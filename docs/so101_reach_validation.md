# SO-101 reach and workspace validation

Run after closing the Isaac Sim GUI:

```bash
./scripts/isaac-sim.sh python /workspace/so101/scripts/validate_so101_reach.py
```

The controller uses Lula with the five arm joints and keeps the gripper joint
outside the kinematic chain. The controlled frame is `gripper_frame_link`.
Targets are position-only because the five-axis arm cannot generally satisfy an
arbitrary 6D pose target.

| Waypoint | Target position (m) | Position error (m) |
|---|---|---:|
| `pre_grasp` | `(0.2000, 0.0500, 0.8700)` | 0.001927 |
| `grasp` | `(0.2000, 0.0500, 0.8150)` | 0.002482 |
| `lift` | `(0.2000, 0.0500, 0.8900)` | 0.001826 |
| `pre_place` | `(-0.1000, 0.0500, 0.8710)` | 0.005336 |
| `place` | `(-0.1000, 0.0500, 0.7960)` | 0.005413 |
| `retreat` | `(-0.1000, 0.0500, 0.8910)` | 0.004946 |

All six IK solves converged, all generated targets remained within the imported
joint limits, and the robot mount did not move. The maximum measured endpoint
error was 5.413 mm at `place`, below the 20 mm acceptance threshold.

The target region is near the outer part of the useful workspace but is
reachable at both the pre-place and place heights. The next grasping stage must
still verify the jaw orientation and contact geometry under physics; position
reachability alone does not prove a stable grasp.
