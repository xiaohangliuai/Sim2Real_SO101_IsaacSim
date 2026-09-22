# SO-101 grasp-and-lift validation

Run after closing the Isaac Sim GUI:

```bash
./scripts/isaac-sim.sh python /workspace/so101/scripts/validate_so101_grasp.py
```

The controller executes the deterministic state sequence
`RESET → APPROACH → DESCEND → ALIGN → CLOSE → VERIFY_GRASP → LIFT → HOLD`.
It descends beside the cube before moving horizontally into the open jaw, which
prevents the fixed finger from colliding with the cube's top face.

The imported robot contains visual collision scopes but no active collision
shapes. The task scene therefore supplies lightweight box collision proxies for
the fixed and moving fingers. Both fingers and the cube use an explicit contact
material with static and dynamic friction set to 2.0 and zero restitution.

Grasping uses `configs/so101_lula_grasp_robot_description.yaml`. It keeps
`wrist_roll` fixed at zero while the first four arm joints solve position IK.
This prevents a position-only solve from rotating the jaw plane during the
low-level alignment move. The general reach validator continues to use the
five-axis Lula configuration.

## Acceptance criteria

- At least 18 of 20 trials succeed.
- Cube lift is at least 60 mm.
- Cube-to-end-effector distance after lift is at most 60 mm.
- Cube drift during the 120-step hold is at most 15 mm.

## Measured result

The 20-trial validation passed with the following worst-case measurements:

| Metric | Result | Limit |
|---|---:|---:|
| Successful trials | 20/20 | at least 18/20 |
| Minimum lift height | 136.823 mm | at least 60 mm |
| Maximum cube-to-end-effector distance | 31.621 mm | at most 60 mm |
| Maximum hold drift | 0.079 mm | at most 15 mm |

The full per-trial measurements are written to
`logs/so101_grasp_validation.json` and are intentionally excluded from Git.
