# SO-101 asset in Isaac Lab

The SO-101 robot can now be spawned as an Isaac Lab `Articulation` from the
existing imported USD. The configuration is in `source/so101_lab/asset_cfg.py`.
It preserves the validated six-joint order and uses the position drives and
limits already stored in the USD.

The robot is intentionally tested without the task table, cube, and target.
This check establishes that Isaac Lab can load, duplicate, command, and reset
the robot asset before those task objects are added.

## Run the checks

Close the Isaac Sim GUI if it is open, then run from the project root:

```bash
./scripts/isaac-lab.sh python /workspace/so101/scripts/validate_so101_lab_asset.py --headless --num_envs 1
./scripts/isaac-lab.sh python /workspace/so101/scripts/validate_so101_lab_asset.py --headless --num_envs 8
```

The script verifies the joint names and count, zero home state, positive
shoulder and gripper motion, finite joint values, and repeatable reset after
the motion. Each command writes a JSON report under `logs/`.

| Measurement | One environment | Eight environments |
|---|---:|---:|
| Joint count | 6 | 6 per environment |
| Minimum shoulder-pan motion | 0.042225 rad | 0.042224 rad |
| Minimum gripper motion | 0.149142 rad | 0.149141 rad |
| Maximum reset repeatability error | 0 rad | 0 rad |
| Validation status | Pass | Pass |

The shoulder target was 0.08 rad and the gripper target was 0.15 rad. This
check requires positive movement, not exact convergence to the shoulder target;
future task control must tune motion timing and action scaling independently.

The validator runs in a disposable Docker container. The imported robot USD
currently makes Kit's normal stop callback hang during this isolated test, so
the validator writes and flushes its report before ending the container process.
This does not affect the Isaac Sim GUI or the project files.
