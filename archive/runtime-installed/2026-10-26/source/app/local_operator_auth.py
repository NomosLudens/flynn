"""Loopback-only operator sessions for local instrumental observation.

The operator credential is configured interactively and only its salted scrypt
verifier is persisted. Browser sessions remain opaque, process-local, and short
lived; this does not replace Flynn's production authentication.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import stat
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit


LOCAL_MODE_ENV = "FLYNN_LOCAL_INSTRUMENTAL"
RESIDENT_MODE_ENV = "FLYNN_LOCAL_RESIDENT"
DB_ENV = "FLYNN_V2_DB"
SESSION_COOKIE = "flynn_local_operator"
SESSION_TTL_SECONDS = 900
LOGIN_WINDOW_SECONDS = 60
LOGIN_MAX_ATTEMPTS = 5
CREDENTIAL_LENGTH = 7
CREDENTIAL_FORMAT_VERSION = 1
SCRYPT_N = 1 << 14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_KEY_LENGTH = 32


def local_mode_enabled() -> bool:
    return os.environ.get(LOCAL_MODE_ENV) == "1" or os.environ.get(RESIDENT_MODE_ENV) == "1"


def local_mode_kind() -> str:
    if os.environ.get(RESIDENT_MODE_ENV) == "1":
        return "RESIDENT"
    if os.environ.get(LOCAL_MODE_ENV) == "1":
        return "INSTRUMENTAL_LOCAL_ONLY"
    return "DISABLED"


def credential_store_path() -> Path:
    """Return the per-user verifier path, always outside the application tree."""
    config_root = os.environ.get("XDG_CONFIG_HOME")
    root = Path(config_root).expanduser() if config_root else Path.home() / ".config"
    destination = root / "flynn" / "lethe" / "operator-credential.json"
    application_root = Path(__file__).resolve().parents[1]
    if destination.resolve().is_relative_to(application_root):
        raise RuntimeError("LETHE operator hash must be stored outside the application checkout")
    return destination


def _validate_credential(credential: str) -> None:
    if (len(credential) != CREDENTIAL_LENGTH
            or any(ord(character) < 0x21 or ord(character) > 0x7E for character in credential)):
        raise ValueError("The operator credential must be exactly 7 printable non-space ASCII characters")


def _derive_digest(credential: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        credential.encode("ascii"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_KEY_LENGTH,
        maxmem=64 * 1024 * 1024,
    )


def _credential_record(credential: str) -> dict[str, object]:
    _validate_credential(credential)
    salt = secrets.token_bytes(16)
    return {
        "version": CREDENTIAL_FORMAT_VERSION,
        "algorithm": "scrypt",
        "n": SCRYPT_N,
        "r": SCRYPT_R,
        "p": SCRYPT_P,
        "salt_hex": salt.hex(),
        "digest_hex": _derive_digest(credential, salt).hex(),
    }


def persist_credential_hash(credential: str, path: Path | None = None) -> Path:
    """Atomically persist only the salted password verifier with private modes."""
    destination = path or credential_store_path()
    record = _credential_record(credential)
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(destination.parent, 0o700)

    descriptor, temporary_name = tempfile.mkstemp(prefix=".operator-credential-", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="ascii") as output:
            json.dump(record, output, sort_keys=True, separators=(",", ":"))
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
        os.chmod(destination, 0o600)
        directory_fd = os.open(destination.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def configure_credential_from_terminal() -> Path:
    """Prompt twice without echo and configure a seven-character credential."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise RuntimeError("Run this command directly in an interactive notebook terminal")
    credential = getpass.getpass("New LETHE operator key (exactly 7 characters): ")
    _validate_credential(credential)
    confirmation = getpass.getpass("Confirm LETHE operator key: ")
    if not hmac.compare_digest(credential, confirmation):
        raise ValueError("The two entries did not match; no credential was saved")
    return persist_credential_hash(credential)


def _configure_cli() -> int:
    parser = argparse.ArgumentParser(description="Configure the local LETHE operator key")
    parser.add_argument("command", choices=("configure",), help="set or change the 7-character key")
    parser.parse_args()
    try:
        path = configure_credential_from_terminal()
    except (OSError, RuntimeError, ValueError) as error:
        print(f"LETHE operator key not changed: {error}", file=sys.stderr)
        return 2
    print(f"LETHE operator key configured; salted scrypt hash saved at {path}")
    print("Restart the local Flynn server to load the updated key.")
    return 0


def _loopback_address(value: str | None) -> bool:
    if not value:
        return False
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def is_loopback_request(request) -> bool:
    client = request.client.host if request.client else None
    server = request.scope.get("server") or (None, None)
    host = request.headers.get("host", "")
    parsed_host = urlsplit(f"//{host}").hostname
    return (
        _loopback_address(client)
        and server[0] == "127.0.0.1"
        and parsed_host == "127.0.0.1"
    )


def same_origin_request(request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return False
    parsed = urlsplit(origin)
    try:
        expected_port = request.url.port or (443 if request.url.scheme == "https" else 80)
        origin_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return False
    return (
        parsed.scheme == request.url.scheme
        and parsed.hostname == "127.0.0.1"
        and origin_port == expected_port
        and request.url.hostname == "127.0.0.1"
    )


class LocalOperatorSessions:
    """Short-lived opaque sessions backed by a persisted salted verifier."""

    def __init__(self, store_path: Path | None = None) -> None:
        self._store_path = store_path or credential_store_path()
        self._credential_salt: bytes | None = None
        self._credential_digest: bytes | None = None
        self._sessions: dict[bytes, float] = {}
        self._attempts: dict[str, list[float]] = {}

    @property
    def credential_file(self) -> Path:
        """Path to the hash-only configuration file (never contains a secret)."""
        return self._store_path

    def start(self) -> Path:
        if not local_mode_enabled():
            raise RuntimeError("local LETHE operator authorization is disabled")
        if self._credential_digest is not None:
            raise RuntimeError("local operator credential is already active")
        try:
            metadata = self._store_path.lstat()
        except FileNotFoundError as error:
            raise RuntimeError(
                "LETHE operator key is not configured; run `python3 -m app.local_operator_auth configure`"
            ) from error
        parent_metadata = self._store_path.parent.stat()
        if (not stat.S_ISDIR(parent_metadata.st_mode)
                or parent_metadata.st_uid != os.getuid()
                or stat.S_IMODE(parent_metadata.st_mode) & 0o077):
            raise RuntimeError("LETHE operator hash directory must be private and owned by this user")
        if (not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) & 0o077):
            raise RuntimeError("LETHE operator hash file must be a private file owned by this user")
        try:
            record = json.loads(self._store_path.read_text(encoding="ascii"))
            if (record.get("version") != CREDENTIAL_FORMAT_VERSION
                    or record.get("algorithm") != "scrypt"
                    or record.get("n") != SCRYPT_N
                    or record.get("r") != SCRYPT_R
                    or record.get("p") != SCRYPT_P):
                raise ValueError("unsupported credential hash format")
            salt = bytes.fromhex(record["salt_hex"])
            digest = bytes.fromhex(record["digest_hex"])
            if len(salt) != 16 or len(digest) != SCRYPT_KEY_LENGTH:
                raise ValueError("invalid credential hash dimensions")
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise RuntimeError("LETHE operator hash file is invalid") from error
        self._credential_salt = salt
        self._credential_digest = digest
        return self._store_path

    def stop(self) -> None:
        self._sessions.clear()
        self._attempts.clear()
        self._credential_salt = None
        self._credential_digest = None

    def login(self, source: str, credential: str) -> str | None:
        now = time.monotonic()
        attempts = [stamp for stamp in self._attempts.get(source, []) if now - stamp < LOGIN_WINDOW_SECONDS]
        if len(attempts) >= LOGIN_MAX_ATTEMPTS:
            self._attempts[source] = attempts
            return None
        attempts.append(now)
        self._attempts[source] = attempts

        salt = self._credential_salt
        expected = self._credential_digest
        if salt is None or expected is None:
            return None
        try:
            _validate_credential(credential)
            supplied = _derive_digest(credential, salt)
        except (UnicodeEncodeError, ValueError):
            return None
        if not hmac.compare_digest(supplied, expected):
            return None
        self._sessions = {digest: expires for digest, expires in self._sessions.items() if now < expires}
        if len(self._sessions) >= 3:
            return None
        token = secrets.token_urlsafe(32)
        self._sessions[hashlib.sha256(token.encode("ascii")).digest()] = now + SESSION_TTL_SECONDS
        return token

    def is_authorized(self, token: str | None) -> bool:
        if not token:
            return False
        now = time.monotonic()
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        expires_at = self._sessions.get(digest)
        if expires_at is None:
            return False
        if now >= expires_at:
            self._sessions.pop(digest, None)
            return False
        return True

    def logout(self, token: str | None) -> None:
        if token:
            self._sessions.pop(hashlib.sha256(token.encode("utf-8")).digest(), None)


local_operator_sessions = LocalOperatorSessions()


if __name__ == "__main__":
    raise SystemExit(_configure_cli())
