"""Validate SO-101 articulation metadata and move each DOF independently.

Run after closing the GUI:
    ./scripts/isaac-sim.sh python /workspace/so101/scripts/validate_so101_articulation.py
"""

import json
from pathlib import Path

import numpy as np
from isaacsim import SimulationApp


simulation_app = SimulationApp({"headless": True})

from isaacsim.core.api import World
from isaacsim.core.prims import SingleArticulation
from isaacsim.core.utils.stage import open_stage
from isaacsim.core.utils.types import ArticulationAction


SCENE_PATH = "/workspace/so101/scenes/so101_pick_place_task.usda"
ROBOT_PATH = "/World/so101_new_calib"
EXPECTED_DOF_NAMES = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]
TEST_DELTAS = {
    "shoulder_pan": 0.08,
    "shoulder_lift": 0.08,
    "elbow_flex": 0.08,
    "wrist_flex": 0.08,
    "wrist_roll": 0.08,
    "gripper": 0.15,
}
SETTLE_STEPS = 120
MOVE_STEPS = 180
POSITION_TOLERANCE = 0.035
RETURN_TOLERANCE = 0.035
BASE_POSITION_TOLERANCE = 1.0e-5


def step_world(world: World, count: int) -> None:
    for _ in range(count):
        world.step(render=False)


def as_list(values) -> list:
    return np.asarray(values).astype(float).tolist()


def main() -> None:
    assert open_stage(SCENE_PATH), f"Unable to open {SCENE_PATH}"
    world = World(stage_units_in_meters=1.0, backend="numpy", device="cpu")
    robot = world.scene.add(
        SingleArticulation(
            prim_path=ROBOT_PATH,
            name="so101",
            reset_xform_properties=False,
        )
    )
    world.reset()
    step_world(world, SETTLE_STEPS)

    assert robot.handles_initialized
    assert robot.num_dof == len(EXPECTED_DOF_NAMES), robot.num_dof
    assert robot.dof_names == EXPECTED_DOF_NAMES, robot.dof_names

    initial_positions = robot.get_joint_positions().copy()
    initial_velocities = robot.get_joint_velocities().copy()
    assert np.isfinite(initial_positions).all()
    assert np.isfinite(initial_velocities).all()

    dof_properties = robot.dof_properties
    lower_limits = dof_properties["lower"].copy()
    upper_limits = dof_properties["upper"].copy()
    stiffness = dof_properties["stiffness"].copy()
    damping = dof_properties["damping"].copy()
    max_effort = dof_properties["maxEffort"].copy()
    max_velocity = dof_properties["maxVelocity"].copy()

    assert np.all(lower_limits < upper_limits)
    assert np.all(initial_positions >= lower_limits - 1.0e-5)
    assert np.all(initial_positions <= upper_limits + 1.0e-5)
    assert np.all(stiffness > 0.0)
    assert np.all(damping >= 0.0)
    assert np.all(max_effort > 0.0)

    base_start_position, base_start_orientation = robot.get_world_pose()
    joint_results = []

    for index, name in enumerate(robot.dof_names):
        target_positions = initial_positions.copy()
        requested = float(initial_positions[index] + TEST_DELTAS[name])
        target_positions[index] = np.clip(
            requested,
            lower_limits[index] + 0.02,
            upper_limits[index] - 0.02,
        )
        commanded_delta = float(target_positions[index] - initial_positions[index])
        assert commanded_delta > 0.0

        robot.apply_action(ArticulationAction(joint_positions=target_positions))
        step_world(world, MOVE_STEPS)
        moved_positions = robot.get_joint_positions().copy()
        moved_velocities = robot.get_joint_velocities().copy()

        target_error = float(abs(moved_positions[index] - target_positions[index]))
        other_indices = [i for i in range(robot.num_dof) if i != index]
        max_other_error = float(
            np.max(np.abs(moved_positions[other_indices] - initial_positions[other_indices]))
        )
        assert np.isfinite(moved_positions).all()
        assert np.isfinite(moved_velocities).all()
        assert target_error <= POSITION_TOLERANCE, (name, target_error)
        assert max_other_error <= POSITION_TOLERANCE, (name, max_other_error)

        robot.apply_action(ArticulationAction(joint_positions=initial_positions.copy()))
        step_world(world, MOVE_STEPS)
        returned_positions = robot.get_joint_positions().copy()
        return_error = float(np.max(np.abs(returned_positions - initial_positions)))
        assert return_error <= RETURN_TOLERANCE, (name, return_error)

        joint_results.append(
            {
                "index": index,
                "name": name,
                "lower_limit_rad": float(lower_limits[index]),
                "upper_limit_rad": float(upper_limits[index]),
                "initial_position_rad": float(initial_positions[index]),
                "commanded_delta_rad": commanded_delta,
                "reached_position_rad": float(moved_positions[index]),
                "target_error_rad": target_error,
                "max_other_joint_error_rad": max_other_error,
                "return_error_rad": return_error,
                "stiffness": float(stiffness[index]),
                "damping": float(damping[index]),
                "max_effort": float(max_effort[index]),
                "max_velocity_rad_s": float(max_velocity[index]),
            }
        )

    final_positions = robot.get_joint_positions().copy()
    final_velocities = robot.get_joint_velocities().copy()
    base_final_position, base_final_orientation = robot.get_world_pose()
    base_position_error = float(np.linalg.norm(base_final_position - base_start_position))
    base_orientation_error = float(
        min(
            np.linalg.norm(base_final_orientation - base_start_orientation),
            np.linalg.norm(base_final_orientation + base_start_orientation),
        )
    )

    assert np.max(np.abs(final_positions - initial_positions)) <= RETURN_TOLERANCE
    assert np.isfinite(final_velocities).all()
    assert base_position_error <= BASE_POSITION_TOLERANCE
    assert base_orientation_error <= BASE_POSITION_TOLERANCE

    result = {
        "scene": SCENE_PATH,
        "robot_prim_path": ROBOT_PATH,
        "status": "pass",
        "num_dof": robot.num_dof,
        "dof_names": robot.dof_names,
        "initial_positions_rad": as_list(initial_positions),
        "initial_velocities_rad_s": as_list(initial_velocities),
        "final_positions_rad": as_list(final_positions),
        "final_velocities_rad_s": as_list(final_velocities),
        "base_position_error_m": base_position_error,
        "base_orientation_error": base_orientation_error,
        "joint_results": joint_results,
    }
    output = Path("/workspace/so101/logs/so101_articulation_validation.json")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("SO101_ARTICULATION_VALIDATION_PASS " + json.dumps(result), flush=True)


try:
    main()
finally:
    simulation_app.close()
