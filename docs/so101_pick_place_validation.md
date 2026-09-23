# SO-101 full pick-and-place validation

Run after closing the Isaac Sim GUI:

```bash
./scripts/isaac-sim.sh python /workspace/so101/scripts/validate_so101_pick_place.py
```

The controller executes the deterministic sequence
`RESET → APPROACH → DESCEND → ALIGN → CLOSE → VERIFY_GRASP →`
`LIFT → TRANSIT → PLACE_APPROACH → PLACE → OPEN → EXIT →`
`RETREAT → HOME → SUCCESS`.

Arm motion explicitly maintains the intended gripper target. This prevents a
contact-limited jaw position from being reused as the next motion target and
gradually weakening the grasp during transfer.

Transfer uses measured cube and end-effector positions for three correction
iterations at the pre-place and approach heights. The final placement motion is
vertical. A calibrated release offset compensates for the small horizontal
displacement caused when the high-friction moving jaw opens. After release, the
end effector exits horizontally, retreats upward, and then returns home.

The target disk has a 55 mm radius. The cube horizontal circumradius is about
28.3 mm, so the 25 mm center-error limit keeps the complete cube footprint
inside the target disk.

## Acceptance criteria

- At least 18 of 20 full cycles succeed.
- Final cube center error in the target plane is at most 25 mm.
- Final cube height error is at most 8 mm.
- Final cube linear speed is at most 10 mm/s.
- Maximum robot home-position error is at most 0.03 rad.

## Measured result

The 20-trial validation passed with the following worst-case measurements:

| Metric | Result | Limit |
|---|---:|---:|
| Successful trials | 20/20 | at least 18/20 |
| Maximum target-plane center error | 4.704 mm | at most 25 mm |
| Maximum cube height error | 0.003 mm | at most 8 mm |
| Maximum final cube speed | 0.848 mm/s | at most 10 mm/s |
| Maximum home-position error | 0.018850 rad | at most 0.03 rad |

The full per-trial measurements are written to
`logs/so101_pick_place_validation.json` and are intentionally excluded from Git.
