# Persistence, episodes and checkpoints

## SQLite schema

The installed schema version is `1`. Its tables are `metadata`, `neuron_mapping`, `events`, `stimuli`, `component_states`, `coordinator_control`, `causal_generations`, and `causal_generation_control`. Event payloads and component snapshots are JSON text; event/state IDs include episode, generation or sequence information. Mapping, event and state tables have update/delete guards. The resident SQLite file was in `DELETE` journal mode at inspection.

The viewer opens the same episode database read-only. In `DELETE` mode, a long reader may hold a shared lock while the resident writer needs an exclusive lock. The resident store's writer connection uses the Python SQLite default connection timeout; the service log records `database is locked` failures. This archive does not change the schema or database.

## Identity rule

An episode is not identified by a numeric tick interval alone. Use `(episode_id, generation_id, checkpoint_state_id, checkpoint_sha256, checkpoint_tick)`. `episode.json` stores episode identity but may not contain a generation; the causal control row in SQLite is authoritative for the active generation and checkpoint cursor.

## Main resident records

| Store | Episode | Generation / cursor | Evidence |
|---|---|---|---|
| `resident-episode-5` | `resident-v2:flynn-1gb:19bc839e52474f3f9a3ec12eefaf1647` | `ffc7f14f56c149268e695faaf40a0451`, checkpoint tick 87,800, revision 440 | Last cursor at 15:40:31 UTC; checkpoint SHA-256 `0b7c0316993dc03bdee9d49e4cc2c323f015dc31f49c462815de1d47621c0cd8`. Persisted component states continue to tick 88,000, but the cycle lacks the atomic confirmed-cycle record required for restoration. |
| `resident-episode-3` | `resident-v2:flynn-1gb:successor-0474efa32ea5408a87f89b567c5dab7b` | Latest local generation `generation-be731e6d86374508818c4f8f685850c3`, tick 4,468,400 | This exceeds the Cloud Storage catalog's last archived tick 3,786,800. The later local database/checkpoint have no completed remote-archive proof. |
| `resident-episode-4` | `resident-v2:flynn-1gb:174591ea2f3c4217947d017416beafa7` | generation `b1a298a898a147079fb851a909c1e469`, tick 0, no checkpoint hash | Separate episode; not a continuation of episode 5. |
| `resident-episode-2` | `resident-v2:flynn-1gb:7909dda987994c308ec928794a1f4e20` | older schema/cursor form | Its copies appear in maintenance and forensic staging. Matching bytes or ticks do not make these independent executions. |

The current episode-5 database contained 5,169 events, 3,393 component states, 139,255 neuron mappings and no rows in `stimuli`. At tick 88,000 there are world-coordinator, PicoClaw-receipt and body state records, but the durable cursor remained tick 87,800. The next starts failed with `resident checkpoint lacks its atomic confirmed-cycle record`. The unit reached the systemd start limit and was not restarted by this archive mission.

## Checkpoint contents and hashes

The three episode-5 NPZ files are unchanged and remain on the VM:

| Tick | Size | SHA-256 | Interpretation |
|---:|---:|---|---|
| 87,600 | 888,763 B | `01d04242cc70d9bcf02902c3772d41d739f971a787402342127ed28f697fb336` | Earlier saved checkpoint |
| 87,800 | 869,473 B | `0b7c0316993dc03bdee9d49e4cc2c323f015dc31f49c462815de1d47621c0cd8` | Last causal-control checkpoint |
| 88,000 | 869,285 B | `3315e284a47b0ce254e261b3a96f67fadea4e2a5be0df5623095877a434743f9` | File exists, but no confirmed-cycle cursor proves it is a restorable boundary |

The NPZ schema includes LIF arrays, neural tick/sequence, world snapshot JSON and observability snapshot JSON. A filename alone is not a restoration proof. No restore was attempted for this final archive.

## Previously archived history

The existing archive catalog reports seven Cloud Storage segments for episode 3 through tick 3,786,800, with generation changes recorded in the manifests. The catalog, segment manifests and earlier readback/restore verification are on the VM. The object for ticks 2,153,401–3,414,000 is 9,256,436 bytes and was readable with existing VM credentials; its recorded archive SHA-256 is `e2910d8cab0b5c7b5d48e6a8a9389454f2af2a85b746c20c2df07e5e3586afb9`. The catalog itself was last updated 2026-10-24. These historical remote segments do not contain episode 5.

## Preservation boundary

The SHA-256 manifest in [`archive/runtime-installed/2026-10-26/data-preservation/data.sha256`](../archive/runtime-installed/2026-10-26/data-preservation/data.sha256) inventories episode JSON, SQLite files, NPZ checkpoints and archive metadata on the VM. It does not copy those datasets to GitHub. Current episode 5 and episode-3 data after tick 3,786,800 remain unpreserved outside the VM at capture. They must not be deleted with the VM until a separately authorized preservation decision is complete.
