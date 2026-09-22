"""Stress-test deterministic reset for the SO-101 pick-place task."""

import json
import sys
from pathlib import Path

import numpy as np
from isaacsim import SimulationApp


simulation_app = SimulationApp({"headless": True})

from isaacsim.core.api import World
from isaacsim.core.utils.stage import open_stage


PROJECT_ROOT = Path("/workspace/so101")
sys.path.insert(0, str(PROJECT_ROOT / "source"))

from so101_tasks import SO101PickPlaceTask


SCENE_PATH = str(PROJECT_ROOT / "scenes/so101_pick_place_task.usda")
RESET_COUNT = 20
POSITION_REPEATABILITY = 1.0e-4
ORIENTATION_REPEATABILITY = 1.0e-4
JOINT_REPEATABILITY = 2.0e-4


def quaternion_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(min(np.linalg.norm(a - b), np.linalg.norm(a + b)))


def perturb(task: SO101PickPlaceTask, iteration: int) -> None:
    direction = -1.0 if iteration % 2 else 1.0
    joint_offset = direction * np.array(
        [0.015, -0.012, 0.01, -0.008, 0.006, 0.03], dtype=np.float32
    )
    task.robot.set_joint_positions(task.config.home_joint_positions + joint_offset)
    task.robot.set_joint_velocities(
        direction * np.array([0.05, -0.04, 0.03, -0.02, 0.01, 0.06], dtype=np.float32)
    )

    cube_offset = direction * np.array([0.025, -0.015, 0.04], dtype=np.float32)
    task.cube.set_world_poses(
        positions=(task.config.cube_position + cube_offset)[None, :],
        orientations=np.array([[0.9961947, 0.0, 0.0, direction * 0.0871557]], dtype=np.float32),
    )
    task.cube.set_linear_velocities(
        np.array([[direction * 0.2, -direction * 0.1, 0.15]], dtype=np.float32)
    )
    task.cube.set_angular_velocities(
        np.array([[0.0, direction * 0.5, -direction * 0.25]], dtype=np.float32)
    )

    target_offset = direction * np.array([0.02, 0.01, 0.0], dtype=np.float32)
    task.target.set_world_poses(
        positions=(task.config.target_position + target_offset)[None, :],
        orientations=task.config.target_orientation[None, :].copy(),
    )
    task.step(2)


def main() -> None:
    assert open_stage(SCENE_PATH), f"Unable to open {SCENE_PATH}"
    world = World(stage_units_in_meters=1.0, backend="numpy", device="cpu")
    task = SO101PickPlaceTask(world)
    task.initialize()

    base_position, base_orientation = task.robot.get_world_pose()
    baseline = task.reset(settle=True)
    reset_results = []

    for iteration in range(RESET_COUNT):
        perturb(task, iteration)
        state = task.reset(settle=True)

        joint_error = float(
            np.max(np.abs(state["joint_positions"] - baseline["joint_positions"]))
        )
        cube_position_error = float(
            np.linalg.norm(state["cube_position"] - baseline["cube_position"])
        )
        cube_orientation_error = quaternion_distance(
            state["cube_orientation"], baseline["cube_orientation"]
        )
        target_position_error = float(
            np.linalg.norm(state["target_position"] - task.config.target_position)
        )
        target_orientation_error = quaternion_distance(
            state["target_orientation"], task.config.target_orientation
        )
        joint_speed = float(np.max(np.abs(state["joint_velocities"])))
        cube_linear_speed = float(np.linalg.norm(state["cube_linear_velocity"]))
        cube_angular_speed = float(np.linalg.norm(state["cube_angular_velocity"]))

        assert joint_error <= JOINT_REPEATABILITY, (iteration, joint_error)
        assert cube_position_error <= POSITION_REPEATABILITY, (
            iteration,
            cube_position_error,
        )
        assert cube_orientation_error <= ORIENTATION_REPEATABILITY, (
            iteration,
            cube_orientation_error,
        )
        assert target_position_error <= POSITION_REPEATABILITY
        assert target_orientation_error <= ORIENTATION_REPEATABILITY
        assert joint_speed < 0.02, (iteration, joint_speed)
        assert cube_linear_speed < 0.02, (iteration, cube_linear_speed)
        assert cube_angular_speed < 0.2, (iteration, cube_angular_speed)

        reset_results.append(
            {
                "iteration": iteration,
                "joint_repeatability_rad": joint_error,
                "cube_position_repeatability_m": cube_position_error,
                "cube_orientation_repeatability": cube_orientation_error,
                "target_position_error_m": target_position_error,
                "target_orientation_error": target_orientation_error,
                "max_joint_speed_rad_s": joint_speed,
                "cube_linear_speed_m_s": cube_linear_speed,
                "cube_angular_speed_rad_s": cube_angular_speed,
            }
        )

    final_base_position, final_base_orientation = task.robot.get_world_pose()
    base_position_error = float(np.linalg.norm(final_base_position - base_position))
    base_orientation_error = quaternion_distance(final_base_orientation, base_orientation)
    assert base_position_error <= 1.0e-5
    assert base_orientation_error <= 1.0e-5

    result = {
        "scene": SCENE_PATH,
        "status": "pass",
        "reset_count": RESET_COUNT,
        "settle_steps_per_reset": task.config.settle_steps,
        "baseline_joint_positions_rad": baseline["joint_positions"].tolist(),
        "baseline_cube_position_m": baseline["cube_position"].tolist(),
        "target_position_m": task.config.target_position.tolist(),
        "max_joint_repeatability_rad": max(
            item["joint_repeatability_rad"] for item in reset_results
        ),
        "max_cube_position_repeatability_m": max(
            item["cube_position_repeatability_m"] for item in reset_results
        ),
        "max_cube_orientation_repeatability": max(
            item["cube_orientation_repeatability"] for item in reset_results
        ),
        "base_position_error_m": base_position_error,
        "base_orientation_error": base_orientation_error,
        "resets": reset_results,
    }
    output = PROJECT_ROOT / "logs/pick_place_reset_validation.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("SO101_PICK_PLACE_RESET_PASS " + json.dumps(result), flush=True)


try:
    main()
finally:
    simulation_app.close()
