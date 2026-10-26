# Incident history

Dates below are UTC where available. A claim is marked **observed** when supported by a service journal, SQLite state, manifest or content hash. Uncertain causal interpretation is labeled.

## Earlier recovery and version divergence

- **2026-10-19 — resident/recovery branches:** multiple episode directories and recovery successors were created. The archive contains separate episode IDs and generations; matching ticks are not evidence of the same execution. Forensic and restore-test directories contain copies or successors, not additional live runs.
- **2026-10-20 — SQLite maintenance copies:** two maintenance backup sets were retained. Their equal SHA-256 files confirm duplicated bytes in some paths, not separate episodes. No historical files were deleted in this final archive.
- **2026-10-22 — first remote history verification:** the archive contains verification records for segments through tick 821,000, including a successful decompression/readback/reconstruction record for an earlier segment. The evidence does not prove that later generations or the current episode were archived.
- **2026-10-23 to 2026-10-24 — generation transitions and archive coverage:** episode `resident-v2:flynn-1gb:successor-0474efa32ea5408a87f89b567c5dab7b` has multiple generations in its archive catalog. Seven segments extend through tick 3,786,800 as of the catalog's 2026-10-24 update. The 2,153,401–3,414,000 segment is generation `generation-3e89139858f046dbbfe642b55f1809e2`; it is not episode 5. Later local episode-3 data reaches tick 4,468,400 and is not covered by the catalog's last segment.
- **2026-10-24 — archive rotation/readback:** the local archive tree retains a 793,518,080-byte source backup from an archive rotation, plus candidate and restore-test files. Existing manifests record earlier readback and reconstruction results. The current archive timer later reported insufficient disk for staging plus reserve.

## Flynn V2 body, energy and public surface

- **2026-10-19 onward — Pinocchio and proprioception:** body and proprioceptive modules were installed; their presence was not a closed-loop proof. Prior reports distinguish a synthetic planar base and instrumental mappings from validated anatomical mechanics.
- **2026-10-25 — Homeostasis V2:** the installed model introduced a measured CPU budget with a 3,600 CPU-second full-reserve scale. It explicitly disabled assimilation without a verified source/conversion. This is compute accounting, not a biological energy model.
- **2026-10-26 — `set_illumination` bridge:** a restricted path allowed the command into the existing world queue. Historical deployment notes record two startup failures after `_handle_signal` was removed, followed by restoration of the handler and resumption of the same episode. Exact prior attempt timestamps are not retained in this archive's service journal; the source snapshot contains the restored handler. No inference of lost data is made from the restart alone.
- **2026-10-26 — public service:** the viewer was configured on `127.0.0.1:8201` behind the existing Cloudflare path. During this capture the public observer returned HTTP 502 while the viewer service was inactive. A successful earlier HTTP 200 was not treated as proof of fresh resident data.

## 2026-10-26 episode 5 and shutdown failure

The configured resident root is `/var/lib/flynn-v2/resident-episode-5`. Episode `resident-v2:flynn-1gb:19bc839e52474f3f9a3ec12eefaf1647` has active generation `ffc7f14f56c149268e695faaf40a0451`. Its causal cursor points to checkpoint tick 87,800, updated at 15:40:31 UTC. Component records continue through neural time 8,800 ms, but there is no atomic confirmed-cycle record for that later cycle.

| Time | Observed event | Cause classification |
|---|---|---|
| 15:28:07–15:28:15 | The scheduled history archiver stopped the viewer and resident. | **Observed:** pressure rotation behavior in the archiver; archive then failed with `insufficient free disk for archive staging plus reserve` at 15:28:16. The unit's archive root was episode 3 while the resident root was episode 5. |
| 15:28:16 | systemd started resident and viewer again. | **Observed:** automatic recovery after archiver's attempt; this archive mission did not request it. |
| 15:32:10 | Resident PID 176070 exited with `OperationalError: database is locked`; systemd restarted it at 15:32:41. | **Observed:** exact error and restart. A long read-only forensic query was running in the same interval; in SQLite `DELETE` journal mode it could block a writer. The attribution is strongly supported but the sudo journal does not retain that Python script's body. |
| 15:40:31–15:40:52 | Episode 5 persisted confirmed cycle 438 at 8,780 ms, then cycle 439 state at 8,800 ms. Causal control remained at tick 87,800. | **Observed:** SQLite rows. The partial 88,000 state is not a confirmed durable boundary. |
| 15:41:09 | Resident PID 176413 exited with `database is locked`; systemd restarted at 15:41:39. | **Observed:** exact error/restart. A long `PRAGMA integrity_check` was part of the forensic session. This archive's previous report identifies it as strongly aligned with the blocking read; the investigation caused these diagnostic-side interruptions. |
| 15:41:48, 15:42:22, 15:42:55 | Three starts exited with `resident checkpoint lacks its atomic confirmed-cycle record`. | **Observed:** service journal. Startup rejected the latest cursor/record combination; this was not a successful restore. |
| 15:43:26 | systemd hit `Start request repeated too quickly`; resident unit became failed with restart counter 5. Viewer was inactive as a dependent service. | **Observed:** last service status captured for this archive. No manual service restart or database modification was performed during this archive mission. |

The earlier lock errors are not attributed to a software data-corruption event without evidence. The missing confirmed-cycle record and later failed starts are explicit runtime outcomes. The user should treat the exact restored continuity after the crash as unverified. The live GET returned 502 during this unavailable period.

## Last state and resource gate

At capture, the resident and viewer were already failed/inactive, so no stop was issued and neither was started. The active history timer remains configured. The VM's 1-GB memory report was 964 MiB total, no swap; `/` had 1.2 GB free of 9.7 GB. GCP returned permission denied for `compute.instances.get`, `.list`, `compute.disks.list`, and `compute.addresses.list`. Therefore exact instance ID, disks and shared-network dependencies remain unverified; no deletion targets are approved or complete.
