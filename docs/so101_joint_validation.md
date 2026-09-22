# SO-101 articulation validation

Validated in Isaac Sim 5.1 using:

```bash
./scripts/isaac-sim.sh python /workspace/so101/scripts/validate_so101_articulation.py
```

The validation loads `scenes/so101_pick_place_task.usda`, waits for the robot to
settle, moves one DOF at a time, returns it to the initial pose, and checks that
the table mount remains fixed. The machine-readable result is written to
`logs/so101_articulation_validation.json`.

## Stable controller ordering

| Index | Joint | Lower limit (rad) | Upper limit (rad) | Test delta (rad) | Target error (rad) | Return error (rad) |
|---:|---|---:|---:|---:|---:|---:|
| 0 | `shoulder_pan` | -1.919860 | 1.919860 | 0.08 | 0.015080 | 0.015851 |
| 1 | `shoulder_lift` | -1.745330 | 1.745330 | 0.08 | 0.009831 | 0.010783 |
| 2 | `elbow_flex` | -1.690000 | 1.690000 | 0.08 | 0.000744 | 0.009834 |
| 3 | `wrist_flex` | -1.658060 | 1.658060 | 0.08 | 0.000181 | 0.011092 |
| 4 | `wrist_roll` | -2.743850 | 2.841210 | 0.08 | 0.000003 | 0.008323 |
| 5 | `gripper` | -0.174533 | 1.745330 | 0.15 | 0.000728 | 0.010133 |

All values are radians. The controller and task code must retain this ordering.

## Drive properties

| Joint | Stiffness | Damping | Maximum effort | Maximum velocity (rad/s) |
|---|---:|---:|---:|---:|
| `shoulder_pan` | 17.778107 | 0.007111 | 10.0 | 9.999999 |
| `shoulder_lift` | 57.874058 | 0.023150 | 10.0 | 9.999999 |
| `elbow_flex` | 220.222824 | 0.088089 | 10.0 | 9.999999 |
| `wrist_flex` | 256.332031 | 0.102533 | 10.0 | 9.999999 |
| `wrist_roll` | 43.053837 | 0.017222 | 10.0 | 9.999999 |
| `gripper` | 2.166366 | 0.000867 | 10.0 | 9.999999 |

## Validation result

- Six controllable revolute DOFs were detected.
- The USD order matches the URDF and expected task order.
- Every joint moved independently in the positive direction and returned.
- The largest target error was 0.015080 rad on `shoulder_pan`.
- The largest return error was 0.015851 rad after the `shoulder_pan` test.
- Maximum unintended motion in another joint was 0.009905 rad.
- The robot mount position and orientation did not move.
- No joint exceeded its imported limit.

The positive direction is the imported URDF joint-local +Z right-hand-rule
direction and produces an increasing Isaac Sim joint coordinate. Matching this
direction to the physical SO-101 servo convention remains a required hardware
calibration step before sim-to-real deployment.
