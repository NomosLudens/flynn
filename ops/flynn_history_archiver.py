#!/usr/bin/env python3
"""Bounded-memory T2 history exporter and checkpoint-gated SQLite rotator.

Closed, checkpoint-confirmed rows are exported in short rowid pages. Local
compaction is allowed only after the remote catalog is verified, a compact
candidate restores in the installed T2, and the resident and viewer are
quiescent. This oneshot remains the sole maintenance writer, not a neural
runtime or a second resident SQLite writer.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import http.client
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

BUCKET_PREFIX = "gs://kaline-totalidade-backup-1079084506908/FLYNN/HISTORICO"
BATCH_ROWS = 16
ARCHIVE_THRESHOLD = 0.75 * 1_073_741_824
ARCHIVE_PRESSURE_INTERVAL_SECONDS = 30 * 60
MANIFEST_INTERVAL_SECONDS = 8 * 60 * 60
ARCHIVE_SERVICE_ACCOUNT = "flynn-history-archiver@kaline-totalidade.iam.gserviceaccount.com"
MAX_RESIDENT_DATA_BYTES = 1_073_741_824
_ACCESS_TOKEN: str | None = None
_METADATA_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as f:
        f.write(canonical(value))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def connect_readonly(path: Path) -> sqlite3.Connection:
    c = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True,
                         isolation_level=None, timeout=5)
    c.execute("PRAGMA query_only=ON")
    c.execute("PRAGMA busy_timeout=5000")
    return c


def capture(root: Path, db: Path) -> dict[str, Any]:
    c = connect_readonly(db)
    try:
        # Capture only small cursor/schema metadata in one short read snapshot.
        c.execute("BEGIN")
        control = c.execute(
            "SELECT episode_id,active_generation_id,checkpoint_state_id,checkpoint_sha256,"
            "checkpoint_tick,revision,updated_at_utc FROM causal_generation_control WHERE singleton=1"
        ).fetchone()
        if not control:
            raise RuntimeError("no active causal checkpoint cursor")
        checkpoint_row = c.execute(
            "SELECT state_json FROM component_states WHERE state_id=? AND component='integrated_world_neural_checkpoint'",
            (control[2],),
        ).fetchone()
        if not checkpoint_row:
            raise RuntimeError("active cursor checkpoint state is missing")
        checkpoint = json.loads(checkpoint_row[0])
        if (checkpoint.get("episode_id") != control[0]
                or checkpoint.get("causal_generation_id") != control[1]
                or int(checkpoint.get("neural_tick", -1)) != int(control[4])
                or checkpoint.get("checkpoint_sha256") != control[3]):
            raise RuntimeError("active checkpoint cursor and paired state disagree")
        cp_path = Path(checkpoint["checkpoint_file"]).resolve()
        if not cp_path.is_relative_to(root.resolve()) or not cp_path.is_file():
            raise RuntimeError("checkpoint file is absent or outside the resident root")
        if sha256_file(cp_path) != control[3]:
            raise RuntimeError("checkpoint file SHA-256 does not match SQLite cursor")
        highwater: dict[str, int] = {}
        for table in ("events", "component_states", "stimuli", "neuron_mapping", "causal_generations", "metadata"):
            highwater[table] = int(c.execute(f'SELECT COALESCE(MAX(rowid),0) FROM "{table}"').fetchone()[0])
        schemas = c.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master "
            "WHERE sql IS NOT NULL AND type IN ('table','index','trigger') "
            "AND name NOT LIKE 'sqlite_%' ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 ELSE 2 END,name"
        ).fetchall()
        columns = {}
        integer_primary_keys = {}
        table_names = [r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()]
        for name in table_names:
            info = c.execute(f'PRAGMA table_info("{name}")').fetchall()
            columns[name] = [r[1] for r in info]
            integer_primary_keys[name] = [r[1] for r in info if r[5] == 1 and r[2].upper() == "INTEGER"]
        generations = c.execute("SELECT * FROM causal_generations ORDER BY rowid").fetchall()
        coordinator = c.execute("SELECT * FROM coordinator_control WHERE singleton=1").fetchall()
        metadata = c.execute("SELECT * FROM metadata ORDER BY key").fetchall()
        c.execute("COMMIT")
        episode_marker = json.loads((root / "episode.json").read_text(encoding="utf-8"))
        if episode_marker.get("episode_id") != control[0] or episode_marker.get("execution_kind") != "RESIDENT":
            raise RuntimeError("episode marker differs from the active SQLite cursor")
        return {
            "episode_id": control[0], "generation_id": control[1],
            "checkpoint_state_id": control[2], "checkpoint_sha256": control[3],
            "checkpoint_tick": int(control[4]), "checkpoint_neural_time_ms": float(checkpoint["neural_time_ms"]),
            "checkpoint_file": str(cp_path), "checkpoint_bytes": cp_path.stat().st_size,
            "checkpoint_state": checkpoint, "control_rows": [[1, *list(control)]],
            "coordinator_control": coordinator, "metadata_rows": metadata,
            "generations": generations, "watermarks": highwater,
            "schema_rows": schemas, "columns": columns,
            "integer_primary_keys": integer_primary_keys,
            "episode_marker": episode_marker,
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        c.close()


def add_bytes(tf: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o600
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    tf.addfile(info, io.BytesIO(data))


def table_pages(c: sqlite3.Connection, table: str, columns: list[str],
                after: int, high: int) -> Iterator[list[tuple[Any, ...]]]:
    quoted_cols = ",".join('"' + x.replace('"', '""') + '"' for x in columns)
    cursor = after
    while cursor < high:
        rows = c.execute(
            f'SELECT rowid,{quoted_cols} FROM "{table}" WHERE rowid>? AND rowid<=? ORDER BY rowid LIMIT ?',
            (cursor, high, BATCH_ROWS),
        ).fetchall()
        if not rows:
            break
        cursor = int(rows[-1][0])
        yield rows


def write_table(tf: tarfile.TarFile, c: sqlite3.Connection, table: str,
                columns: list[str], high: int, lower_rowid: int,
                boundary_ms: float | None, *, time_column: str | None = None,
                export_all: bool = False) -> dict[str, Any]:
    digest = hashlib.sha256()
    count = excluded = 0
    last_rowid = lower_rowid
    chunk_number = 0
    batch: list[bytes] = []
    column_index = columns.index(time_column) if time_column else None

    def flush() -> None:
        nonlocal chunk_number
        if not batch:
            return
        chunk_number += 1
        add_bytes(tf, f"tables/{table}/{chunk_number:06d}.jsonl", b"".join(batch))
        batch.clear()

    for page in table_pages(c, table, columns, lower_rowid, high):
        for row in page:
            rowid, values = int(row[0]), row[1:]
            if not export_all and column_index is not None:
                neural_time = values[column_index]
                if neural_time is None or float(neural_time) > float(boundary_ms):
                    excluded += 1
                    continue
            entry = canonical({"rowid": rowid, "values": values})
            batch.append(entry)
            digest.update(entry)
            count += 1
            last_rowid = max(last_rowid, rowid)
            if len(batch) >= BATCH_ROWS:
                flush()
    flush()
    return {"rows": count, "last_rowid": last_rowid, "sha256": digest.hexdigest(),
            "excluded_after_checkpoint": excluded}


def build_archive(root: Path, db: Path, state_dir: Path, stage_dir: Path,
                  bucket_prefix: str) -> dict[str, Any] | None:
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    stage_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = (state_dir / "archive.lock").open("a+")
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise RuntimeError("another history archive task is active") from exc
    catalog_path = state_dir / "catalog.json"
    catalog = json.loads(catalog_path.read_text()) if catalog_path.exists() else {
        "schema": "flynn.history_catalog.v1", "last_checkpoint_tick": -1,
        "rowids": {}, "segments": [], "untimed_rowids": {},
    }
    snap = capture(root, db)
    previous_tick = int(catalog["last_checkpoint_tick"])
    current_tick = snap["checkpoint_tick"]
    resident_bytes = sum(
        p.stat().st_blocks * 512 if p.stat().st_blocks else p.stat().st_size
        for p in root.rglob("*") if p.is_file() and not p.is_symlink()
    )
    last_archive = catalog.get("last_archive_at_utc")
    elapsed = float("inf")
    if last_archive:
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last_archive.replace("Z", "+00:00"))).total_seconds()
    manifest_due = not last_archive or elapsed >= MANIFEST_INTERVAL_SECONDS
    pressure_due = resident_bytes >= ARCHIVE_THRESHOLD and elapsed >= ARCHIVE_PRESSURE_INTERVAL_SECONDS
    if not manifest_due and not pressure_due:
        return None
    if current_tick <= previous_tick:
        return None

    db_size = db.stat().st_size
    free = shutil.disk_usage(stage_dir).free
    # Reserve a bounded staging margin before reading/exporting the large DB.
    if free < (2 * db_size + snap["checkpoint_bytes"] + 256 * 1024 * 1024):
        raise RuntimeError("insufficient free disk for archive staging plus reserve")

    segment_key = (f"segments/{snap['episode_id']}/{snap['generation_id']}/"
                   f"{previous_tick + 1:012d}-{current_tick:012d}.tar.zst")
    archive_path = stage_dir / f"segment-{previous_tick + 1}-{current_tick}.tar.zst"
    partial = archive_path.with_suffix(archive_path.suffix + ".partial")
    internal: dict[str, Any] = {
        "schema": "flynn.history_segment.v1", "episode_id": snap["episode_id"],
        "generation_id": snap["generation_id"], "from_tick_exclusive": previous_tick,
        "to_tick_inclusive": current_tick, "checkpoint_state_id": snap["checkpoint_state_id"],
        "checkpoint_sha256": snap["checkpoint_sha256"],
        "checkpoint_neural_time_ms": snap["checkpoint_neural_time_ms"],
        "checkpoint_bytes": snap["checkpoint_bytes"],
        "checkpoint_state": snap["checkpoint_state"],
        "previous_segment_uri": catalog["segments"][-1]["object_uri"] if catalog["segments"] else None,
        "database_basename": db.name, "tables": {}, "created_by": "flynn_history_archiver_v1",
    }
    c = connect_readonly(db)
    try:
        proc_out = partial.open("wb")
        proc = subprocess.Popen(["zstd", "-q", "-3", "-T1", "-c"], stdin=subprocess.PIPE,
                                stdout=proc_out, stderr=subprocess.PIPE)
        try:
            assert proc.stdin is not None
            with tarfile.open(fileobj=proc.stdin, mode="w|") as tf:
                schema = {"rows": snap["schema_rows"], "columns": snap["columns"],
                          "integer_primary_keys": snap["integer_primary_keys"],
                          "episode_marker": snap["episode_marker"]}
                add_bytes(tf, "schema.json", canonical(schema))
                add_bytes(tf, "header.json", canonical({k: v for k, v in internal.items() if k != "tables"}))
                previous_rowids = catalog.get("rowids", {})
                previous_untimed = catalog.get("untimed_rowids", {})
                # Append-only timed tables are paged with short autocommit reads.
                for table, time_col in (("events", "neural_time_ms"),
                                        ("component_states", "neural_time_ms")):
                    res = write_table(tf, c, table, snap["columns"][table],
                                      snap["watermarks"][table],
                                      int(previous_rowids.get(table, 0)),
                                      snap["checkpoint_neural_time_ms"],
                                      time_column=time_col)
                    internal["tables"][table] = res
                    # Untimed records are an archival side channel, not a neural boundary.
                    query = (f'SELECT rowid,{",".join(chr(34)+x+chr(34) for x in snap["columns"][table])} '
                             f'FROM "{table}" WHERE rowid>? AND rowid<=? AND neural_time_ms IS NULL ORDER BY rowid LIMIT ?')
                    cursor = int(previous_untimed.get(table, 0))
                    digest = hashlib.sha256(); n = 0; last = cursor; buf = [] ; chunk = 0
                    while cursor < snap["watermarks"][table]:
                        page = c.execute(query, (cursor, snap["watermarks"][table], BATCH_ROWS)).fetchall()
                        if not page: break
                        cursor = int(page[-1][0])
                        for row in page:
                            entry = canonical({"rowid": int(row[0]), "values": row[1:]})
                            buf.append(entry); digest.update(entry); n += 1; last = int(row[0])
                        if buf:
                            chunk += 1; add_bytes(tf, f"untimed/{table}/{chunk:06d}.jsonl", b"".join(buf)); buf.clear()
                    internal["tables"][table + "_untimed"] = {"rows": n, "last_rowid": last, "sha256": digest.hexdigest()}
                    previous_untimed[table] = last
                # Static mapping/schema facts are included once; generation lineage is always explicit.
                if not catalog["segments"]:
                    for table in ("metadata", "neuron_mapping"):
                        res = write_table(tf, c, table, snap["columns"][table],
                                          int(c.execute(f'SELECT COALESCE(MAX(rowid),0) FROM "{table}"').fetchone()[0]),
                                          0, None, export_all=True)
                        internal["tables"][table] = res
                generation_after = int(catalog.get("rowids", {}).get("causal_generations", 0))
                res = write_table(tf, c, "causal_generations", snap["columns"]["causal_generations"],
                                  snap["watermarks"]["causal_generations"], generation_after, None, export_all=True)
                internal["tables"]["causal_generations"] = res
                # Snapshot mutable singletons in header for a recoverable cursor without rewriting SQLite.
                internal["cursor_snapshot"] = {
                    "causal_generation_control": snap["control_rows"],
                    "coordinator_control": snap["coordinator_control"],
                    "metadata": snap["metadata_rows"],
                }
                # Include stimuli for this segment using only the current bounded event page.
                # Do not retain a set proportional to the entire historical interval.
                stim_digest = hashlib.sha256(); stim_count=0; stim_buf=[]; stim_chunk=0
                event_pages = table_pages(
                    c, "events", snap["columns"]["events"],
                    int(previous_rowids.get("events", 0)), snap["watermarks"]["events"],
                )
                for page in event_pages:
                    ids = [rec[1] for rec in page
                           if rec[4] is None or float(rec[4]) <= snap["checkpoint_neural_time_ms"]]
                    if not ids:
                        continue
                    placeholders = ",".join("?" for _ in ids)
                    rows = c.execute(f'SELECT rowid,{",".join(chr(34)+x+chr(34) for x in snap["columns"]["stimuli"])} FROM stimuli WHERE event_id IN ({placeholders}) ORDER BY rowid', ids).fetchall()
                    for row in rows:
                        entry=canonical({"rowid":int(row[0]),"values":row[1:]}); stim_buf.append(entry); stim_digest.update(entry); stim_count+=1
                        if len(stim_buf) >= BATCH_ROWS:
                            stim_chunk+=1; add_bytes(tf,f"tables/stimuli/{stim_chunk:06d}.jsonl",b"".join(stim_buf)); stim_buf.clear()
                if stim_buf:
                    stim_chunk+=1; add_bytes(tf,f"tables/stimuli/{stim_chunk:06d}.jsonl",b"".join(stim_buf)); stim_buf.clear()
                internal["tables"]["stimuli"] = {"rows":stim_count,"sha256":stim_digest.hexdigest()}
                # Paired physical checkpoint artifact is copied into the immutable segment.
                cp = Path(snap["checkpoint_file"])
                info = tarfile.TarInfo("checkpoint/integrated.npz")
                info.size = cp.stat().st_size; info.mode=0o600; info.mtime=0; info.uid=info.gid=0; info.uname=info.gname=""
                with cp.open("rb") as source: tf.addfile(info, source)
                add_bytes(tf, "manifest.json", canonical(internal))
            proc.stdin.close()
            err = proc.stderr.read() if proc.stderr else b""
            code = proc.wait()
            proc_out.close()
            if code:
                raise RuntimeError(f"zstd failed ({code}): {err.decode(errors='replace')[-1000:]}")
            with partial.open("rb") as f:
                os.fsync(f.fileno())
            os.replace(partial, archive_path)
            dir_fd = os.open(stage_dir, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except Exception:
            if proc.poll() is None:
                proc.kill(); proc.wait()
            proc_out.close()
            partial.unlink(missing_ok=True)
            raise
    finally:
        c.close()

    archive_sha = sha256_file(archive_path)
    object_uri = bucket_prefix.rstrip("/") + "/" + segment_key
    remote_manifest = {
        "schema": "flynn.remote_archive_manifest.v1", "object_uri": object_uri,
        "archive_sha256": archive_sha, "archive_bytes": archive_path.stat().st_size,
        "episode_id": snap["episode_id"], "generation_id": snap["generation_id"],
        "from_tick_exclusive": previous_tick, "to_tick_inclusive": current_tick,
        "checkpoint_state_id": snap["checkpoint_state_id"],
        "checkpoint_sha256": snap["checkpoint_sha256"],
        "table_summary": internal["tables"],
        "captured_at_utc": snap["checkpoint_state"].get("saved_at_utc"),
    }
    sidecar = stage_dir / f"{archive_path.stem}.manifest.json"
    atomic_json(sidecar, remote_manifest)
    # Create-only uploads fit the VM identity. On an idempotent retry, read the exact object.
    created = upload_create_only(archive_path, object_uri)
    readback = stage_dir / f"{archive_path.stem}.readback.tar.zst"
    download_exact(object_uri, readback)
    manifest_uri = object_uri + ".manifest.json"
    manifest_readback = stage_dir / f"{archive_path.stem}.manifest.readback.json"
    if created:
        if sha256_file(readback) != archive_sha:
            raise RuntimeError("remote archive readback SHA-256 mismatch")
        remote_manifest["manifest_uri"] = manifest_uri
        upload_create_only(sidecar, manifest_uri)
        download_exact(manifest_uri, manifest_readback)
        if sha256_file(manifest_readback) != sha256_file(sidecar):
            raise RuntimeError("remote manifest readback SHA-256 mismatch")
    else:
        # A previous immutable object may use different deterministic tar chunking.
        # Accept it only when its own SHA is valid and every logical row/checkpoint
        # digest exactly matches this export; never overwrite or silently trust it.
        download_exact(manifest_uri, manifest_readback)
        existing_manifest = json.loads(manifest_readback.read_text(encoding="utf-8"))
        if sha256_file(readback) != existing_manifest.get("archive_sha256"):
            raise RuntimeError("existing remote archive does not match its manifest SHA-256")
        identity_fields = (
            "object_uri", "episode_id", "generation_id", "from_tick_exclusive",
            "to_tick_inclusive", "checkpoint_state_id", "checkpoint_sha256", "table_summary",
        )
        if any(existing_manifest.get(key) != remote_manifest.get(key) for key in identity_fields):
            raise RuntimeError("existing immutable archive differs from the current logical segment")
        remote_manifest = existing_manifest

    segment = {**remote_manifest, "manifest_uri": manifest_uri}
    catalog["episode_id"] = snap["episode_id"]
    catalog["generation_id"] = snap["generation_id"]
    catalog["last_checkpoint_tick"] = current_tick
    catalog["last_checkpoint_state_id"] = snap["checkpoint_state_id"]
    catalog["last_archive_at_utc"] = datetime.now(timezone.utc).isoformat()
    catalog["rowids"].update({
        "events": max(int(catalog["rowids"].get("events", 0)), int(internal["tables"]["events"]["last_rowid"])),
        "component_states": max(int(catalog["rowids"].get("component_states", 0)), int(internal["tables"]["component_states"]["last_rowid"])),
        "causal_generations": max(int(catalog["rowids"].get("causal_generations", 0)), int(internal["tables"]["causal_generations"]["last_rowid"])),
    })
    catalog["untimed_rowids"].update({t:int(internal["tables"][t+"_untimed"]["last_rowid"]) for t in ("events","component_states")})
    if not catalog["segments"]:
        catalog["rowids"]["metadata"] = snap["watermarks"]["metadata"]
        catalog["rowids"]["neuron_mapping"] = snap["watermarks"]["neuron_mapping"]
    catalog["segments"].append(segment)
    catalog["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    # A consolidated remote catalog is immutable/versioned; no object-list permission is needed.
    catalog_bytes = canonical(catalog)
    catalog_sha = hashlib.sha256(catalog_bytes).hexdigest()
    catalog_obj = (bucket_prefix.rstrip("/") + f"/catalog/{snap['episode_id']}/"
                   f"catalog-{current_tick:012d}-{catalog_sha[:16]}.json")
    catalog_file = stage_dir / f"catalog-{current_tick}-{catalog_sha[:16]}.json"
    catalog_file.write_bytes(catalog_bytes)
    upload_create_only(catalog_file, catalog_obj)
    cat_readback = stage_dir / f"catalog-{current_tick}.readback.json"
    download_exact(catalog_obj, cat_readback)
    if sha256_file(cat_readback) != catalog_sha:
        raise RuntimeError("consolidated catalog readback SHA-256 mismatch")
    catalog["latest_remote_catalog_uri"] = catalog_obj
    # Commit the local cursor only after the remote catalog is readable and verified.
    # Otherwise a crash here would make the next run skip this checkpoint forever.
    atomic_json(catalog_path, catalog)
    staged_bytes_removed = 0
    for path in (archive_path, readback, sidecar, manifest_readback, catalog_file, cat_readback):
        try:
            staged_bytes_removed += path.stat().st_size
            path.unlink()
        except FileNotFoundError:
            pass
    return {"segment": segment, "catalog_uri": catalog_obj,
            "sha256": archive_sha, "verified_staging_bytes_removed": staged_bytes_removed}


def upload_create_only(source: Path, uri: str) -> bool:
    bucket, object_name = _gcs_target(uri)
    token = _metadata_access_token()
    query = urllib.parse.urlencode({
        "uploadType": "media", "name": object_name, "ifGenerationMatch": "0",
    }, quote_via=urllib.parse.quote)
    path = f"/upload/storage/v1/b/{urllib.parse.quote(bucket, safe='')}/o?{query}"
    conn = http.client.HTTPSConnection("storage.googleapis.com", timeout=120)
    try:
        conn.putrequest("POST", path, skip_accept_encoding=True)
        conn.putheader("Authorization", f"Bearer {token}")
        conn.putheader("Content-Type", "application/octet-stream")
        conn.putheader("Content-Length", str(source.stat().st_size))
        conn.putheader("Connection", "close")
        conn.endheaders()
        with source.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                conn.send(block)
        response = conn.getresponse()
        response.read(8192)
        if response.status in (200, 201):
            return True
        if response.status == 412:
            return False
        raise RuntimeError(f"Cloud Storage create failed: HTTP {response.status}")
    finally:
        conn.close()


def download_exact(uri: str, destination: Path) -> None:
    destination.unlink(missing_ok=True)
    bucket, object_name = _gcs_target(uri)
    token = _metadata_access_token()
    path = (f"/storage/v1/b/{urllib.parse.quote(bucket, safe='')}/o/"
            f"{urllib.parse.quote(object_name, safe='')}?alt=media")
    conn = http.client.HTTPSConnection("storage.googleapis.com", timeout=120)
    try:
        conn.request("GET", path, headers={"Authorization": f"Bearer {token}",
                                            "Connection": "close"})
        response = conn.getresponse()
        if response.status != 200:
            response.read(8192)
            raise RuntimeError(f"Cloud Storage readback failed: HTTP {response.status}")
        with destination.open("wb") as output:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                output.write(block)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        conn.close()


def _gcs_target(uri: str) -> tuple[str, str]:
    parsed = urllib.parse.urlsplit(uri)
    if parsed.scheme != "gs" or not parsed.netloc or not parsed.path.lstrip("/"):
        raise ValueError("archive destination must be a gs://bucket/object URI")
    return parsed.netloc, urllib.parse.unquote(parsed.path.lstrip("/"))


def _metadata_access_token() -> str:
    """Use only the VM's attached archiver identity; never persist or log its token."""
    global _ACCESS_TOKEN
    if _ACCESS_TOKEN is not None:
        return _ACCESS_TOKEN
    headers = {"Metadata-Flavor": "Google"}
    email_request = urllib.request.Request(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email",
        headers=headers,
    )
    with _METADATA_OPENER.open(email_request, timeout=5) as response:
        email = response.read(512).decode("ascii").strip()
    if email != ARCHIVE_SERVICE_ACCOUNT:
        raise RuntimeError("VM metadata identity does not match the authorized history archiver")
    token_request = urllib.request.Request(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
        headers=headers,
    )
    with _METADATA_OPENER.open(token_request, timeout=5) as response:
        payload = json.loads(response.read(4096))
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("VM metadata server did not return an access token")
    _ACCESS_TOKEN = token
    return token


def verify_and_reconstruct(archive_path: Path, expected_sha256: str, destination: Path) -> dict[str, Any]:
    """Rebuild a disposable SQLite copy from a downloaded segment and verify every row stream."""
    actual = sha256_file(archive_path)
    if actual != expected_sha256:
        raise RuntimeError(f"archive SHA-256 mismatch: expected {expected_sha256}, got {actual}")
    destination.unlink(missing_ok=True)
    proc = subprocess.Popen(["zstd", "-q", "-d", "-c", str(archive_path)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.stdout is None:
        raise RuntimeError("zstd decompressor did not provide a stream")
    target: sqlite3.Connection | None = None
    schema: dict[str, Any] | None = None
    manifest: dict[str, Any] | None = None
    hashes: dict[str, Any] = defaultdict(lambda: {"rows": 0, "sha256": hashlib.sha256()})
    checkpoint_hash: str | None = None
    try:
        with tarfile.open(fileobj=proc.stdout, mode="r|") as tf:
            for member in tf:
                stream = tf.extractfile(member)
                if stream is None:
                    continue
                if member.name == "schema.json":
                    schema = json.load(stream)
                    target = sqlite3.connect(destination)
                    target.execute("PRAGMA foreign_keys=OFF")
                    target.execute("PRAGMA journal_mode=OFF")
                    target.execute("PRAGMA synchronous=OFF")
                    for typ, _name, _tbl, sql in schema["rows"]:
                        if typ == "table":
                            target.execute(sql)
                    continue
                if member.name == "manifest.json":
                    manifest = json.load(stream)
                    continue
                if member.name == "checkpoint/integrated.npz":
                    h = hashlib.sha256()
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        h.update(block)
                    checkpoint_hash = h.hexdigest()
                    continue
                if member.name.startswith("tables/") or member.name.startswith("untimed/"):
                    if target is None or schema is None:
                        raise RuntimeError("archive row data preceded the schema")
                    parts = member.name.split("/")
                    table = parts[1]
                    bucket = ("untimed/" if parts[0] == "untimed" else "") + table
                    columns = schema["columns"][table]
                    pk_aliases = schema.get("integer_primary_keys", {}).get(table, [])
                    for raw in stream:
                        entry = json.loads(raw)
                        rowid, values = int(entry["rowid"]), entry["values"]
                        hashes[bucket]["sha256"].update(raw)
                        hashes[bucket]["rows"] += 1
                        if pk_aliases:
                            pk_index = columns.index(pk_aliases[0])
                            if int(values[pk_index]) != rowid:
                                raise RuntimeError(f"INTEGER PRIMARY KEY/rowid mismatch in {table}")
                            names = columns
                            vals = values
                        else:
                            names = ["rowid", *columns]
                            vals = [rowid, *values]
                        escaped = ",".join('"' + name.replace('"', '""') + '"' for name in names)
                        marks = ",".join("?" for _ in vals)
                        target.execute(f'INSERT INTO "{table}" ({escaped}) VALUES ({marks})', vals)
                        if hashes[bucket]["rows"] % 1000 == 0:
                            target.commit()
                    target.commit()
                    continue
                # Other members are bounded metadata JSON.
                if member.name == "header.json":
                    json.load(stream)
        stderr = proc.stderr.read() if proc.stderr else b""
        code = proc.wait()
        if code:
            raise RuntimeError(f"zstd verification decompression failed: {stderr.decode(errors='replace')[-1000:]}")
        if target is None or schema is None or manifest is None:
            raise RuntimeError("archive is missing schema or manifest")
        if checkpoint_hash != manifest["checkpoint_sha256"]:
            raise RuntimeError("archived paired checkpoint file hash differs from its manifest")
        for table, stats in manifest["tables"].items():
            bucket = ("untimed/" if table.endswith("_untimed") else "") + table.removesuffix("_untimed")
            observed = hashes[bucket]
            if observed["rows"] != stats["rows"] or observed["sha256"].hexdigest() != stats["sha256"]:
                raise RuntimeError(f"row-stream verification failed for {table}")
        # The active cursors are mutable singletons captured in the segment header.
        for table, rows in (("causal_generation_control", manifest["cursor_snapshot"]["causal_generation_control"]),
                            ("coordinator_control", manifest["cursor_snapshot"]["coordinator_control"])):
            if rows:
                columns = schema["columns"][table]
                row = list(rows[0])
                if len(row) == len(columns) - 1 and columns[0] == "singleton":
                    row.insert(0, 1)
                if len(row) != len(columns):
                    raise RuntimeError(f"captured control row shape differs from schema for {table}")
                escaped = ",".join('"' + name.replace('"', '""') + '"' for name in columns)
                marks = ",".join("?" for _ in columns)
                target.execute(f'INSERT INTO "{table}" ({escaped}) VALUES ({marks})', row)
        for typ, _name, _tbl, sql in schema["rows"]:
            if typ in ("index", "trigger"):
                target.execute(sql)
        target.commit()
        target.execute("PRAGMA foreign_keys=ON")
        fk_errors = target.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            raise RuntimeError(f"reconstructed segment has foreign-key violations: {fk_errors[:5]}")
        target.commit()
        # Re-read the causal pointer from the reconstructed database.
        cursor = target.execute("SELECT episode_id,active_generation_id,checkpoint_state_id,checkpoint_sha256,checkpoint_tick FROM causal_generation_control WHERE singleton=1").fetchone()
        if not cursor or cursor[0] != manifest["episode_id"] or cursor[1] != manifest["generation_id"] or cursor[2] != manifest["checkpoint_state_id"] or cursor[3] != manifest["checkpoint_sha256"] or int(cursor[4]) != int(manifest["to_tick_inclusive"]):
            raise RuntimeError("reconstructed active causal cursor differs from archived checkpoint")
        checkpoint_row = target.execute(
            "SELECT event_id,component,state_json FROM component_states WHERE state_id=?",
            (manifest["checkpoint_state_id"],),
        ).fetchone()
        if not checkpoint_row or json.loads(checkpoint_row[2]) != manifest["checkpoint_state"]:
            raise RuntimeError("reconstructed checkpoint state differs from archived cursor metadata")
        state_refs = {r[0]: (r[1], r[2]) for r in target.execute(
            "SELECT state_id,event_id,component FROM component_states"
        ).fetchall()}
        unresolved = []
        for event_id, event_type, payload_json in target.execute(
            "SELECT event_id,event_type,payload_json FROM events"
        ):
            payload = json.loads(payload_json)
            ref = payload.get("_component_state_ref") if isinstance(payload, dict) else None
            if ref is not None:
                resolved = state_refs.get(ref.get("state_id"))
                if (event_type != "COMPONENT_STATE_RECORDED" or resolved is None
                        or resolved != (event_id, ref.get("component"))):
                    unresolved.append(event_id)
                    if len(unresolved) >= 5:
                        break
        if unresolved:
            raise RuntimeError(f"deduplicated event payload references unresolved: {unresolved}")
        return {"archive_sha256": actual, "checkpoint_sha256": checkpoint_hash,
                "foreign_key_violations": 0, "tables_reconstructed": len(schema["columns"]),
                "deduplicated_payload_references": len(state_refs),
                "reconstructed_db_bytes": destination.stat().st_size,
                "episode_id": cursor[0], "generation_id": cursor[1], "checkpoint_tick": cursor[4]}
    except Exception:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        destination.unlink(missing_ok=True)
        raise
    finally:
        if target is not None:
            target.close()



def _resident_bytes(root: Path) -> int:
    # Match the resident guard exactly: DBs, WAL/SHM sidecars, and neural/world checkpoints.
    total = 0
    for path in (root / "episode-v2.sqlite3", root / "world.sqlite3"):
        if path.exists():
            total += path.stat().st_size
    for path in (root / "episode-v2.sqlite3-wal", root / "episode-v2.sqlite3-shm",
                 root / "world.sqlite3-wal", root / "world.sqlite3-shm"):
        if path.exists():
            total += path.stat().st_size
    checkpoints = root / "checkpoints"
    if checkpoints.exists():
        total += sum(p.stat().st_size for p in checkpoints.glob("flynn-world-lif-*.npz") if p.is_file())
    return total


def _unit_active(unit: str) -> bool:
    result = subprocess.run(["systemctl", "is-active", "--quiet", unit], check=False)
    return result.returncode == 0


def _rotation_due(root: Path, state_dir: Path) -> bool:
    catalog_path = state_dir / "catalog.json"
    if not catalog_path.is_file():
        return False
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    allocated = sum(p.stat().st_blocks * 512 if p.stat().st_blocks else p.stat().st_size
                    for p in root.rglob("*") if p.is_file() and not p.is_symlink())
    last = catalog.get("last_archive_at_utc")
    elapsed = float("inf") if not last else (
        datetime.now(timezone.utc) - datetime.fromisoformat(last.replace("Z", "+00:00"))
    ).total_seconds()
    return allocated >= ARCHIVE_THRESHOLD and elapsed >= ARCHIVE_PRESSURE_INTERVAL_SECONDS


def _verify_catalog_coverage(catalog: dict[str, Any]) -> None:
    segments = catalog.get("segments")
    if not isinstance(segments, list) or not segments:
        raise RuntimeError("rotation requires verified remote archive segments")
    previous_tick = -1
    for segment in segments:
        if (len(str(segment.get("archive_sha256", ""))) != 64
                or not segment.get("object_uri") or not segment.get("manifest_uri")):
            raise RuntimeError("catalog contains a segment without verified object identity")
        if int(segment.get("from_tick_exclusive", -2)) != previous_tick:
            raise RuntimeError("remote segment tick intervals have a gap or overlap")
        if int(segment.get("to_tick_inclusive", -1)) <= previous_tick:
            raise RuntimeError("remote segment tick interval is not increasing")
        previous_tick = int(segment["to_tick_inclusive"])
    for table in ("events", "component_states", "causal_generations"):
        cursor = total = 0
        for segment in segments:
            summary = segment.get("table_summary", {}).get(table)
            if not isinstance(summary, dict) or len(str(summary.get("sha256", ""))) != 64:
                raise RuntimeError(f"remote archive lacks a row-stream digest for {table}")
            last = int(summary.get("last_rowid", -1))
            rows = int(summary.get("rows", -1))
            if rows < 0 or last - cursor != rows:
                raise RuntimeError(f"remote archive rowid coverage has a gap or overlap in {table}")
            cursor, total = last, total + rows
        if cursor != int(catalog.get("rowids", {}).get(table, -1)) or total != cursor:
            raise RuntimeError(f"remote archive rowid coverage does not reach the {table} watermark")
    for segment in segments:
        summary = segment.get("table_summary", {}).get("stimuli")
        if not isinstance(summary, dict) or int(summary.get("rows", -1)) < 0 or len(str(summary.get("sha256", ""))) != 64:
            raise RuntimeError("remote archive lacks a valid stimuli row-stream digest")
    first = segments[0].get("table_summary", {})
    for table in ("metadata", "neuron_mapping"):
        summary = first.get(table)
        if not isinstance(summary, dict) or int(summary.get("rows", -1)) != int(catalog.get("rowids", {}).get(table, -2)):
            raise RuntimeError(f"remote archive does not contain the complete immutable {table} table")


def _build_compact_candidate(source_db: Path, root: Path, state_dir: Path,
                             catalog: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    source = sqlite3.connect(source_db)
    source.row_factory = sqlite3.Row
    target_path = work_dir / "candidate.sqlite3"
    target = None
    try:
        source.execute("PRAGMA query_only=ON")
        control = source.execute(
            "SELECT episode_id,active_generation_id,checkpoint_state_id,checkpoint_sha256,checkpoint_tick "
            "FROM causal_generation_control WHERE singleton=1"
        ).fetchone()
        if control is None:
            raise RuntimeError("compact candidate source has no active causal cursor")
        if (catalog.get("episode_id"), catalog.get("generation_id"),
                catalog.get("last_checkpoint_state_id"), catalog.get("last_checkpoint_tick")) != (
                control[0], control[1], control[2], int(control[4])):
            raise RuntimeError("remote catalog does not cover the exact active causal checkpoint")
        _verify_catalog_coverage(catalog)
        cp_row = source.execute(
            "SELECT state_json FROM component_states WHERE state_id=? AND component='integrated_world_neural_checkpoint'",
            (control[2],),
        ).fetchone()
        if cp_row is None:
            raise RuntimeError("compact candidate source is missing the active checkpoint state")
        checkpoint = json.loads(cp_row[0])
        if (checkpoint.get("episode_id") != control[0]
                or checkpoint.get("causal_generation_id") != control[1]
                or checkpoint.get("checkpoint_sha256") != control[3]
                or int(checkpoint.get("neural_tick", -1)) != int(control[4])):
            raise RuntimeError("compact candidate checkpoint differs from its causal cursor")
        checkpoint_path = Path(checkpoint["checkpoint_file"]).resolve()
        if (not checkpoint_path.is_file() or sha256_file(checkpoint_path) != control[3]
                or not checkpoint_path.is_relative_to(root.resolve())):
            raise RuntimeError("compact candidate paired checkpoint artifact failed identity/hash validation")
        body_ref = checkpoint.get("body_checkpoint")
        if not isinstance(body_ref, dict):
            raise RuntimeError("compact candidate checkpoint has no Pinocchio pair")
        body = source.execute(
            "SELECT state_json FROM component_states WHERE state_id=? AND component='pinocchio_body_checkpoint'",
            (body_ref.get("component_state_id"),),
        ).fetchone()
        if body is None:
            raise RuntimeError("compact candidate is missing its checkpoint-paired Pinocchio state")
        body_state = json.loads(body[0])
        body_json = json.dumps(body_state.get("body_state"), sort_keys=True, separators=(",", ":"), allow_nan=False)
        if (body_state.get("episode_id") != control[0]
                or abs(float(body_state.get("physical_time_ms", -1)) - float(checkpoint.get("world_time_ms", -2))) > 1e-8
                or hashlib.sha256(body_json.encode("utf-8")).hexdigest() != body_ref.get("body_state_sha256")):
            raise RuntimeError("compact candidate body state does not match the paired checkpoint hash/time")
        generation, boundary = control[1], float(checkpoint["neural_time_ms"])
        latest: dict[str, int] = {}
        for row in source.execute(
            "SELECT rowid,component FROM component_states "
            "WHERE json_extract(state_json,'$.causal_generation_id')=? AND neural_time_ms<=? "
            "ORDER BY component,neural_time_ms DESC,rowid DESC", (generation, boundary),
        ):
            latest.setdefault(str(row[1]), int(row[0]))
        required = {"continuous_world", "neural_activity_aggregator", "neuro_world_coordinator",
                    "picoclaw_cerebellar_coordinator", "integrated_world_neural_checkpoint",
                    "pinocchio_body_checkpoint", "pinocchio_motor_actuation", "synthetic_proprioceptive_readout"}
        if not required.issubset(latest):
            raise RuntimeError(f"compact candidate lacks required current readouts: {sorted(required-set(latest))}")
        active_cycle = source.execute(
            "SELECT state_json FROM component_states WHERE rowid=?", (latest["neuro_world_coordinator"],)
        ).fetchone()
        if active_cycle is None or json.loads(active_cycle[0]).get("cycle_status") != "CYCLE_CONFIRMED":
            raise RuntimeError("compact candidate current causal cycle is not confirmed")
        selected_states = set(latest.values())
        state_watermark = int(catalog["rowids"]["component_states"])
        event_watermark = int(catalog["rowids"]["events"])
        selected_states.update(int(r[0]) for r in source.execute(
            "SELECT rowid FROM component_states WHERE rowid>?", (state_watermark,)))
        state_rows: dict[int, sqlite3.Row] = {}
        for rowid in selected_states:
            row = source.execute("SELECT rowid AS __rid,* FROM component_states WHERE rowid=?", (rowid,)).fetchone()
            if row is None:
                raise RuntimeError("compact candidate selected a missing component state")
            state_rows[int(row["__rid"])] = row
        event_ids = {str(row["event_id"]) for row in state_rows.values()}
        event_ids.update(str(r[0]) for r in source.execute("SELECT recovery_event_id FROM causal_generations"))
        # Preserve every event/state tail newer than the remotely archived high-water marks.
        event_ids.update(str(r[0]) for r in source.execute("SELECT event_id FROM events WHERE rowid>?", (event_watermark,)))
        event_ids.update(str(r[0]) for r in source.execute("SELECT event_id FROM stimuli"))
        max_event = source.execute("SELECT event_id FROM events ORDER BY rowid DESC LIMIT 1").fetchone()
        if max_event:
            event_ids.add(str(max_event[0]))
        while True:
            added = []
            for event_id in list(event_ids):
                row = source.execute("SELECT payload_json FROM events WHERE event_id=?", (event_id,)).fetchone()
                if row is None:
                    raise RuntimeError(f"compact candidate event reference is missing: {event_id}")
                payload = json.loads(row[0])
                ref = payload.get("_component_state_ref") if isinstance(payload, dict) else None
                if isinstance(ref, dict):
                    state_id = str(ref.get("state_id", ""))
                    if state_id not in {str(r["state_id"]) for r in state_rows.values()}:
                        state = source.execute(
                            "SELECT rowid AS __rid,* FROM component_states WHERE state_id=?", (state_id,)
                        ).fetchone()
                        if state is None:
                            raise RuntimeError(f"deduplicated payload reference is unresolved: {event_id}")
                        added.append(state)
            if not added:
                break
            for state in added:
                state_rows[int(state["__rid"])] = state
                event_ids.add(str(state["event_id"]))
        schema = source.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL "
            "AND type IN ('table','index','trigger') AND name NOT LIKE 'sqlite_%' "
            "ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 ELSE 2 END,name"
        ).fetchall()
        target = sqlite3.connect(target_path)
        target.execute("PRAGMA foreign_keys=OFF")
        for typ, _name, _tbl, sql in schema:
            if typ == "table":
                target.execute(sql)
        def copy_rows(table: str, rows: list[sqlite3.Row]) -> None:
            columns = [r[1] for r in source.execute(f'PRAGMA table_info("{table}")')]
            for row in rows:
                names = ["rowid", *columns]
                target.execute(
                    f'INSERT INTO "{table}" (' + ",".join('"'+n+'"' for n in names) + ") VALUES (" +
                    ",".join("?" for _ in names) + ")",
                    [row["__rid"], *[row[c] for c in columns]],
                )
        for table in ("causal_generations", "metadata", "neuron_mapping", "causal_generation_control", "coordinator_control"):
            copy_rows(table, source.execute(f'SELECT rowid AS __rid,* FROM "{table}" ORDER BY rowid').fetchall())
        ids = list(event_ids)
        if ids:
            marks = ",".join("?" for _ in ids)
            copy_rows("events", source.execute(
                f"SELECT rowid AS __rid,* FROM events WHERE event_id IN ({marks}) ORDER BY rowid", ids
            ).fetchall())
        source_stimuli = source.execute("SELECT COUNT(*) FROM stimuli").fetchone()[0]
        archived_stimuli = sum(int(seg["table_summary"]["stimuli"]["rows"]) for seg in catalog["segments"])
        if int(source_stimuli) != archived_stimuli:
            raise RuntimeError("remote archive stimuli row count differs from the source database")
        copy_rows("stimuli", source.execute("SELECT rowid AS __rid,* FROM stimuli ORDER BY rowid").fetchall())
        copy_rows("component_states", source.execute(
            "SELECT rowid AS __rid,* FROM component_states WHERE rowid IN (" +
            ",".join("?" for _ in state_rows) + ") ORDER BY rowid", list(state_rows)
        ).fetchall())
        for typ, _name, _tbl, sql in schema:
            if typ in ("index", "trigger"):
                target.execute(sql)
        target.commit()
        target.execute("PRAGMA foreign_keys=ON")
        if target.execute("PRAGMA quick_check(1)").fetchone()[0] != "ok":
            raise RuntimeError("compact candidate failed SQLite quick_check")
        fk = target.execute("PRAGMA foreign_key_check").fetchall()
        if fk:
            raise RuntimeError(f"compact candidate has foreign-key violations: {fk[:5]}")
        candidate_cursor = target.execute(
            "SELECT episode_id,active_generation_id,checkpoint_state_id,checkpoint_sha256,checkpoint_tick "
            "FROM causal_generation_control WHERE singleton=1"
        ).fetchone()
        if tuple(candidate_cursor) != tuple(control):
            raise RuntimeError("compact candidate cursor changed during construction")
        for table in ("events", "component_states", "causal_generations", "metadata", "neuron_mapping"):
            high = int(catalog.get("rowids", {}).get(table, 0))
            source_high = int(source.execute(f'SELECT COALESCE(MAX(rowid),0) FROM "{table}"').fetchone()[0])
            candidate_high = int(target.execute(f'SELECT COALESCE(MAX(rowid),0) FROM "{table}"').fetchone()[0])
            if candidate_high != source_high or source_high < high:
                raise RuntimeError(f"compact candidate did not preserve monotonic {table} rowid anchors")
        for event_id, payload in target.execute("SELECT event_id,payload_json FROM events"):
            value = json.loads(payload)
            ref = value.get("_component_state_ref") if isinstance(value, dict) else None
            if ref:
                resolved = target.execute(
                    "SELECT event_id,component FROM component_states WHERE state_id=?", (ref["state_id"],)
                ).fetchone()
                if resolved is None or tuple(resolved) != (event_id, ref["component"]):
                    raise RuntimeError(f"compact candidate has unresolved deduplicated payload: {event_id}")
        target.commit()
        report = {
            "schema": "flynn.sqlite_rotation_candidate.v1", "source_sha256": sha256_file(source_db),
            "candidate_sha256": sha256_file(target_path), "candidate_bytes": target_path.stat().st_size,
            "episode_id": control[0], "generation_id": control[1], "checkpoint_state_id": control[2],
            "checkpoint_sha256": control[3], "checkpoint_tick": int(control[4]),
            "mapping_rows": int(target.execute("SELECT COUNT(*) FROM neuron_mapping").fetchone()[0]),
            "retained_states": len(state_rows), "retained_events": len(event_ids),
            "retained_components": sorted(latest), "remote_archive_segments": len(catalog["segments"]),
            "remote_events_covered": sum(int(x["table_summary"]["events"]["rows"]) for x in catalog["segments"]),
            "remote_states_covered": sum(int(x["table_summary"]["component_states"]["rows"]) for x in catalog["segments"]),
            "integrity_check": "ok", "foreign_key_violations": 0,
            "id_and_rowid_preservation": "PASS", "deduplicated_references": "PASS",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        atomic_json(work_dir / "candidate-manifest.json", report)
        os.chmod(target_path, 0o640)
        return report
    finally:
        if target is not None:
            target.close()
        source.close()


def _backup_sqlite(source_path: Path, destination: Path) -> dict[str, Any]:
    source = connect_readonly(source_path)
    target = sqlite3.connect(destination)
    try:
        source.backup(target, pages=128, sleep=0.02)
        target.commit()
    finally:
        target.close()
        source.close()
    check = sqlite3.connect(f"file:{destination.resolve().as_posix()}?mode=ro", uri=True)
    try:
        quick = check.execute("PRAGMA quick_check(1)").fetchone()[0]
        fk = check.execute("PRAGMA foreign_key_check").fetchall()
        if quick != "ok" or fk:
            raise RuntimeError("pre-rotation SQLite backup failed integrity/foreign-key verification")
        cursor = check.execute(
            "SELECT episode_id,active_generation_id,checkpoint_state_id,checkpoint_sha256,checkpoint_tick "
            "FROM causal_generation_control WHERE singleton=1"
        ).fetchone()
        if cursor is None:
            raise RuntimeError("pre-rotation SQLite backup has no causal cursor")
        return {"quick_check": quick, "foreign_key_violations": len(fk), "cursor": list(cursor),
                "bytes": destination.stat().st_size, "sha256": sha256_file(destination)}
    finally:
        check.close()


def _wait_checkpoint(root: Path, origin_tick: int, timeout_seconds: int = 240) -> dict[str, Any]:
    db = root / "episode-v2.sqlite3"
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _unit_active("flynn-v2-resident.service"):
            raise RuntimeError("T2 became inactive before a new post-rotation checkpoint was confirmed")
        try:
            state = capture(root, db)
            if state["checkpoint_tick"] > origin_tick:
                return state
        except (sqlite3.Error, RuntimeError, OSError):
            pass
        time.sleep(5)
    raise RuntimeError("T2 stayed active but did not confirm a new checkpoint within the bounded observation")


def _rotate_existing(root: Path, state_dir: Path, catalog: dict[str, Any],
                     *, candidate_dir: Path | None = None,
                     start_before: bool | None = None, viewer_before: bool | None = None,
                     safe_stop_recovery: bool | None = None,
                     resident_bytes_before: int | None = None) -> dict[str, Any]:
    if resident_bytes_before is None:
        resident_bytes_before = _resident_bytes(root)
    rotation_root = state_dir / "rotation"
    rotation_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    work = rotation_root / f"run-{stamp}"
    work.mkdir(mode=0o700)
    db = root / "episode-v2.sqlite3"
    if start_before is None:
        start_before = _unit_active("flynn-v2-resident.service")
    if viewer_before is None:
        viewer_before = _unit_active("flynn-lethe-viewer.service")
    marker_path = root / "episode.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if safe_stop_recovery is None:
        safe_stop_recovery = marker.get("last_stop_reason") == "SAFE_STORAGE_LIMIT"
    for unit, active in (("flynn-lethe-viewer.service", viewer_before),
                         ("flynn-v2-resident.service", start_before)):
        if active:
            subprocess.run(["systemctl", "stop", unit], check=True, timeout=240)
    if _unit_active("flynn-v2-resident.service") or _unit_active("flynn-lethe-viewer.service"):
        raise RuntimeError("resident/viewer connection remained open after controlled stop")
    origin = capture(root, db)
    _verify_catalog_coverage(catalog)
    if (catalog.get("episode_id"), catalog.get("generation_id"), catalog.get("last_checkpoint_state_id"),
            catalog.get("last_checkpoint_tick")) != (origin["episode_id"], origin["generation_id"],
            origin["checkpoint_state_id"], origin["checkpoint_tick"]):
        raise RuntimeError("remote archive cursor differs from the stopped resident checkpoint")
    if candidate_dir is None:
        snapshot = work / "source-backup.sqlite3"
        backup = _backup_sqlite(db, snapshot)
        report = _build_compact_candidate(snapshot, root, state_dir, catalog, work)
        report["source_backup"] = backup
        atomic_json(work / "candidate-manifest.json", report)
        candidate_path = work / "candidate.sqlite3"
    else:
        candidate_dir = candidate_dir.resolve()
        candidate_path = candidate_dir / "episode-v2.sqlite3"
        report = json.loads((candidate_dir / "candidate-manifest.json").read_text(encoding="utf-8"))
        if (sha256_file(candidate_path) != report.get("candidate_sha256")
                or report.get("episode_id") != origin["episode_id"]
                or report.get("generation_id") != origin["generation_id"]
                or report.get("checkpoint_state_id") != origin["checkpoint_state_id"]
                or report.get("checkpoint_sha256") != origin["checkpoint_sha256"]
                or int(report.get("checkpoint_tick", -1)) != origin["checkpoint_tick"]):
            raise RuntimeError("prebuilt compact candidate differs from the exact stopped checkpoint")
    candidate_sha = sha256_file(candidate_path)
    # systemd exposes history-archive and resident-episode-3 as separate writable
    # bind mounts. Stage both sides of the SQLite rename inside the resident mount
    # so every os.replace is atomic and cannot fail with EXDEV.
    install_dir = root / ".rotation-install" / f"run-{stamp}"
    install_dir.mkdir(mode=0o700, parents=True)
    staged_candidate = install_dir / "episode-v2.sqlite3"
    required_copy_bytes = candidate_path.stat().st_size
    if shutil.disk_usage(root).free < required_copy_bytes + 536_870_912:
        raise RuntimeError("insufficient free disk for candidate staging plus the measured 512 MiB resident reserve")
    shutil.copyfile(candidate_path, staged_candidate)
    with staged_candidate.open("rb") as staged_file:
        os.fsync(staged_file.fileno())
    if sha256_file(staged_candidate) != candidate_sha:
        raise RuntimeError("same-filesystem candidate staging SHA-256 mismatch")
    stage_fd = os.open(install_dir, os.O_RDONLY)
    try:
        os.fsync(stage_fd)
    finally:
        os.close(stage_fd)
    old_paths = [db, Path(str(db)+"-wal"), Path(str(db)+"-shm")]
    old_sizes = {p.name: p.stat().st_size for p in old_paths if p.exists()}
    old_hashes = {p.name: sha256_file(p) for p in old_paths if p.is_file() and p.stat().st_size}
    rollback = root / ".rotation-rollback" / f"run-{stamp}"
    rollback.mkdir(mode=0o700, parents=True)
    transaction_path = rotation_root / f"transaction-{stamp}.json"
    transaction = {"schema": "flynn.sqlite_rotation_transaction.v1", "status": "PREPARED",
                   "episode_id": origin["episode_id"], "generation_id": origin["generation_id"],
                   "origin_tick": origin["checkpoint_tick"], "origin_checkpoint_sha256": origin["checkpoint_sha256"],
                   "candidate_sha256": candidate_sha, "old_files": old_hashes,
                   "started_at_utc": datetime.now(timezone.utc).isoformat(),
                   "rollback_dir": str(rollback), "candidate_dir": str(candidate_path.parent)}
    atomic_json(transaction_path, transaction)
    switched = False
    try:
        # Merge the stopped writer's WAL into the original main DB first. The
        # consistent SQLite backup and compact candidate already protect this
        # logical state. With no T2/viewer handles, this removes only the now
        # redundant WAL frames and makes the main-file replacement atomic.
        wal_db = sqlite3.connect(db, timeout=5, isolation_level=None)
        try:
            wal_db.execute("PRAGMA busy_timeout=5000")
            journal_mode = str(wal_db.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            if journal_mode != "wal":
                raise RuntimeError(f"resident SQLite journal mode changed unexpectedly: {journal_mode}")
            wal_result = tuple(int(v) for v in wal_db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone())
            if wal_result != (0, 0, 0):
                raise RuntimeError(f"resident SQLite WAL could not be fully checkpointed: {wal_result}")
        finally:
            wal_db.close()
        post_checkpoint_origin = capture(root, db)
        if any(post_checkpoint_origin[key] != origin[key] for key in (
                "episode_id", "generation_id", "checkpoint_state_id", "checkpoint_sha256", "checkpoint_tick")):
            raise RuntimeError("SQLite WAL checkpoint changed the causal origin")
        wal_path = Path(str(db) + "-wal")
        if wal_path.exists() and wal_path.stat().st_size != 0:
            raise RuntimeError("SQLite WAL remains non-empty after TRUNCATE checkpoint")
        # Keep a same-filesystem hard link to the consistent old DB for rollback;
        # replacing the active pathname is a single atomic operation.
        os.link(db, rollback / db.name)
        for path in old_paths[1:]:
            if path.exists():
                os.replace(path, rollback / path.name)
        import pwd
        owner = pwd.getpwnam("tonyus-dev")
        os.chown(staged_candidate, owner.pw_uid, owner.pw_gid)
        os.chmod(staged_candidate, 0o640)
        os.replace(staged_candidate, db)
        switched = True
        for parent in (root, rollback):
            fd = os.open(parent, os.O_RDONLY)
            try: os.fsync(fd)
            finally: os.close(fd)
        transaction["wal_checkpoint_result"] = list(wal_result)
        transaction["post_checkpoint_origin_verified"] = True
        transaction["status"] = "PUBLISHED"
        transaction["published_at_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_json(transaction_path, transaction)
        should_start = start_before or safe_stop_recovery
        if should_start:
            subprocess.run(["systemctl", "start", "flynn-v2-resident.service"], check=True, timeout=120)
            result = _wait_checkpoint(root, origin["checkpoint_tick"])
            transaction["status"] = "RECOVERED"
            transaction["new_checkpoint_state_id"] = result["checkpoint_state_id"]
            transaction["new_checkpoint_sha256"] = result["checkpoint_sha256"]
            transaction["new_checkpoint_tick"] = result["checkpoint_tick"]
            transaction["recovered_at_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_json(transaction_path, transaction)
            if viewer_before or should_start:
                subprocess.run(["systemctl", "start", "flynn-lethe-viewer.service"], check=True, timeout=120)
                if not _unit_active("flynn-lethe-viewer.service"):
                    raise RuntimeError("LETHE viewer did not become active after T2 recovery")
            # The immutable remote catalog covers the old rows; the candidate was restored by the installed T2.
            # Retire only the moved operational copies after the new causal boundary is confirmed.
            freed_rollback = sum(p.stat().st_blocks * 512 if p.stat().st_blocks else p.stat().st_size
                                 for p in rollback.iterdir() if p.is_file())
            for p in list(rollback.iterdir()):
                if p.is_file(): p.unlink()
            try: rollback.rmdir()
            except OSError: pass
            try:
                rollback.parent.rmdir()
            except OSError:
                pass
            try:
                install_dir.rmdir()
                install_dir.parent.rmdir()
            except OSError:
                pass
            snapshot = work / "source-backup.sqlite3"
            if snapshot.exists(): snapshot.unlink()
            transaction["status"] = "COMMITTED"
            transaction["local_rollback_bytes_retired_after_recovery"] = freed_rollback
            transaction["committed_at_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_json(transaction_path, transaction)
            return {"rotation": transaction, "candidate": report,
                    "resident_bytes_before": resident_bytes_before,
                    "resident_bytes_after": _resident_bytes(root),
                    "filesystem_free_after_bytes": shutil.disk_usage(root).free,
                    "local_rollback_bytes_retired": freed_rollback,
                    "checkpoint": result, "t2_active": _unit_active("flynn-v2-resident.service"),
                    "viewer_active": _unit_active("flynn-lethe-viewer.service")}
        # Preserve a user-stopped resident state; do not turn a maintenance run into a start command.
        if viewer_before and _unit_active("flynn-v2-resident.service"):
            subprocess.run(["systemctl", "start", "flynn-lethe-viewer.service"], check=True, timeout=120)
        transaction["status"] = "PUBLISHED_AWAITING_OPERATOR_START"
        atomic_json(transaction_path, transaction)
        return {"rotation": transaction, "candidate": report,
                "resident_bytes_before": resident_bytes_before, "resident_bytes_after": _resident_bytes(root),
                "filesystem_free_after_bytes": shutil.disk_usage(root).free,
                "t2_active": _unit_active("flynn-v2-resident.service"),
                "viewer_active": _unit_active("flynn-lethe-viewer.service")}
    except Exception:
        if not switched:
            old_link = rollback / db.name
            if old_link.exists():
                old_link.unlink()
            # A successful TRUNCATE leaves no live data in the WAL. Restore a
            # non-empty WAL only if a failed checkpoint left it untouched.
            for path in old_paths[1:]:
                saved = rollback / path.name
                if saved.exists():
                    if path.name.endswith("-wal") and saved.stat().st_size > 0 and not path.exists():
                        os.replace(saved, path)
                    else:
                        saved.unlink()
            try:
                rollback.rmdir()
                rollback.parent.rmdir()
            except OSError:
                pass
            try:
                staged_candidate.unlink(missing_ok=True)
                install_dir.rmdir()
                install_dir.parent.rmdir()
            except OSError:
                pass
            transaction["status"] = "ABORTED_BEFORE_PUBLISH"
            transaction["failed_at_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_json(transaction_path, transaction)
        raise



def _resume_published_rotation(root: Path, state_dir: Path, transaction_path: Path) -> dict[str, Any]:
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    if transaction.get("status") not in {"PUBLISHED", "RECOVERED"}:
        raise RuntimeError("rotation transaction is not awaiting post-publication recovery")
    if not _unit_active("flynn-v2-resident.service"):
        raise RuntimeError("published compact database is not running; rollback is retained")
    origin_tick = int(transaction["origin_tick"])
    result = _wait_checkpoint(root, origin_tick)
    if (result["episode_id"] != transaction["episode_id"]
            or result["generation_id"] != transaction["generation_id"]
            or result["checkpoint_tick"] <= origin_tick):
        raise RuntimeError("post-rotation checkpoint does not continue the same episode and generation")
    checkpoint = result["checkpoint_state"]
    if abs(float(checkpoint.get("neural_time_ms", -1)) - float(checkpoint.get("world_time_ms", -2))) > 1e-8:
        raise RuntimeError("post-rotation checkpoint world and neural times are not paired")
    body_ref = checkpoint.get("body_checkpoint")
    if not isinstance(body_ref, dict):
        raise RuntimeError("post-rotation checkpoint has no paired Pinocchio state")
    c = connect_readonly(root / "episode-v2.sqlite3")
    try:
        body_row = c.execute(
            "SELECT state_json FROM component_states WHERE state_id=? AND component='pinocchio_body_checkpoint'",
            (body_ref.get("component_state_id"),),
        ).fetchone()
        if body_row is None:
            raise RuntimeError("post-rotation paired Pinocchio state is absent")
        body_state = json.loads(body_row[0])
        body_json = json.dumps(body_state.get("body_state"), sort_keys=True, separators=(",", ":"), allow_nan=False)
        if (body_state.get("episode_id") != result["episode_id"]
                or body_state.get("causal_generation_id") != result["generation_id"]
                or abs(float(body_state.get("physical_time_ms", -1)) - float(checkpoint["world_time_ms"])) > 1e-8
                or hashlib.sha256(body_json.encode("utf-8")).hexdigest() != body_ref.get("body_state_sha256")):
            raise RuntimeError("post-rotation Pinocchio checkpoint pair failed identity/hash/time validation")
    finally:
        c.close()
    if not _unit_active("flynn-lethe-viewer.service"):
        subprocess.run(["systemctl", "start", "flynn-lethe-viewer.service"], check=True, timeout=120)
    if not _unit_active("flynn-lethe-viewer.service"):
        raise RuntimeError("LETHE viewer did not become active after compact DB recovery")
    rollback = Path(transaction["rollback_dir"]).resolve()
    if not rollback.is_relative_to(root.resolve()) or not rollback.is_dir():
        raise RuntimeError("same-filesystem rollback directory is missing or outside the resident root")
    allowed = { "episode-v2.sqlite3", "episode-v2.sqlite3-wal", "episode-v2.sqlite3-shm" }
    entries = list(rollback.iterdir())
    if any(p.name not in allowed or not p.is_file() for p in entries):
        raise RuntimeError("rollback directory contains unexpected files; retaining it")
    freed = sum(p.stat().st_blocks * 512 if p.stat().st_blocks else p.stat().st_size for p in entries)
    for p in entries:
        p.unlink()
    rollback.rmdir()
    try:
        rollback.parent.rmdir()
    except OSError:
        pass
    install_parent = root / ".rotation-install"
    if install_parent.exists():
        for child in list(install_parent.iterdir()):
            if child.is_dir() and not any(child.iterdir()):
                child.rmdir()
        try:
            install_parent.rmdir()
        except OSError:
            pass
    for directory in (root, state_dir / "rotation"):
        fd = os.open(directory, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    transaction["status"] = "COMMITTED"
    transaction["new_checkpoint_state_id"] = result["checkpoint_state_id"]
    transaction["new_checkpoint_sha256"] = result["checkpoint_sha256"]
    transaction["new_checkpoint_tick"] = result["checkpoint_tick"]
    transaction["recovered_at_utc"] = datetime.now(timezone.utc).isoformat()
    transaction["local_rollback_bytes_retired_after_recovery"] = freed
    transaction["committed_at_utc"] = datetime.now(timezone.utc).isoformat()
    atomic_json(transaction_path, transaction)
    return {"rotation": transaction, "checkpoint": result,
            "resident_bytes_after": _resident_bytes(root),
            "filesystem_free_after_bytes": shutil.disk_usage(root).free,
            "local_rollback_bytes_retired": freed,
            "t2_active": _unit_active("flynn-v2-resident.service"),
            "viewer_active": _unit_active("flynn-lethe-viewer.service")}


def _pending_published_rotation(state_dir: Path) -> Path | None:
    tx_paths = sorted((state_dir / "rotation").glob("transaction-*.json"),
                      key=lambda p: p.stat().st_mtime_ns, reverse=True)
    for path in tx_paths:
        try:
            status = json.loads(path.read_text(encoding="utf-8")).get("status")
        except (OSError, json.JSONDecodeError):
            continue
        if status in {"PUBLISHED", "RECOVERED"}:
            return path
        if status == "COMMITTED":
            return None
    return None

def _pressure_rotation(root: Path, state_dir: Path, bucket_prefix: str,
                       *, candidate_dir: Path | None = None) -> dict[str, Any]:
    resident_bytes_before = _resident_bytes(root)
    viewer_was_active = _unit_active("flynn-lethe-viewer.service")
    t2_was_active = _unit_active("flynn-v2-resident.service")
    # Capture only after quiescing the sole SQLite writer and LETHE reader.
    try:
        for unit, active in (("flynn-lethe-viewer.service", viewer_was_active),
                             ("flynn-v2-resident.service", t2_was_active)):
            if active:
                subprocess.run(["systemctl", "stop", unit], check=True, timeout=240)
        archive_result = build_archive(root, root / "episode-v2.sqlite3", state_dir,
                                       state_dir / "staging", bucket_prefix)
        catalog = json.loads((state_dir / "catalog.json").read_text(encoding="utf-8"))
        marker = json.loads((root / "episode.json").read_text(encoding="utf-8"))
        result = _rotate_existing(root, state_dir, catalog, candidate_dir=candidate_dir,
                                  start_before=t2_was_active, viewer_before=viewer_was_active,
                                  safe_stop_recovery=marker.get("last_stop_reason") == "SAFE_STORAGE_LIMIT",
                                  resident_bytes_before=resident_bytes_before)
        result["archive"] = archive_result
        return result
    except Exception:
        # Resume only a service that was running before maintenance; an existing SAFE_STORAGE_LIMIT stop
        # remains stopped if archiving or validation cannot complete.
        tx_files = sorted((state_dir / "rotation").glob("transaction-*.json"), key=lambda p: p.stat().st_mtime_ns)
        last_status = json.loads(tx_files[-1].read_text()).get("status") if tx_files else None
        if t2_was_active and last_status not in {"PUBLISHED", "RECOVERED", "COMMITTED"} and not _unit_active("flynn-v2-resident.service"):
            if _resident_bytes(root) <= MAX_RESIDENT_DATA_BYTES:
                subprocess.run(["systemctl", "start", "flynn-v2-resident.service"], check=False, timeout=120)
        if viewer_was_active and not _unit_active("flynn-lethe-viewer.service"):
            subprocess.run(["systemctl", "start", "flynn-lethe-viewer.service"], check=False, timeout=120)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/var/lib/flynn-v2/resident-episode-3"))
    parser.add_argument("--bucket-prefix", default=BUCKET_PREFIX)
    parser.add_argument("--state-dir", type=Path, default=Path("/var/lib/flynn-v2/history-archive"))
    parser.add_argument("--stage-dir", type=Path, default=Path("/var/lib/flynn-v2/history-archive/staging"))
    parser.add_argument("--verify-archive", type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--reconstruction-db", type=Path)
    parser.add_argument("--apply-candidate", type=Path,
                        help="Apply a previously verified rotation candidate after remote coverage checks")
    parser.add_argument("--resume-published-rotation", type=Path,
                        help="Finish a published rotation only after a new paired T2 checkpoint is verified")
    args = parser.parse_args()
    if args.verify_archive:
        if not args.expected_sha256 or not args.reconstruction_db:
            parser.error("--verify-archive requires --expected-sha256 and --reconstruction-db")
        result = verify_and_reconstruct(args.verify_archive, args.expected_sha256, args.reconstruction_db)
        print(json.dumps(result, sort_keys=True))
        return 0
    root = args.root.resolve()
    state_dir = args.state_dir.resolve()
    if args.resume_published_rotation:
        result = _resume_published_rotation(root, state_dir, args.resume_published_rotation.resolve())
        print(json.dumps(result, sort_keys=True))
        return 0
    pending = _pending_published_rotation(state_dir)
    if pending is not None:
        result = _resume_published_rotation(root, state_dir, pending)
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.apply_candidate:
        result = _pressure_rotation(root, state_dir, args.bucket_prefix,
                                    candidate_dir=args.apply_candidate.resolve())
        print(json.dumps(result, sort_keys=True))
        return 0
    if _rotation_due(root, state_dir):
        result = _pressure_rotation(root, state_dir, args.bucket_prefix)
        print(json.dumps(result, sort_keys=True))
        return 0
    result = build_archive(root, root / "episode-v2.sqlite3", state_dir, args.stage_dir.resolve(),
                           args.bucket_prefix)
    if result is None:
        print("ARCHIVE_NOT_DUE_OR_NO_NEW_CONFIRMED_CHECKPOINT")
    else:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"FLYNN_ARCHIVE_BLOCKED={type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
