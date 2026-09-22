"""Validate position-only IK at SO-101 pick-and-place task waypoints."""

import json
import sys
from pathlib import Path

import numpy as np
from isaacsim import SimulationApp


simulation_app = SimulationApp({"headless": True})

from isaacsim.core.api import World
from isaacsim.core.utils.stage import open_stage
from isaacsim.core.utils.types import ArticulationAction


PROJECT_ROOT = Path("/workspace/so101")
sys.path.insert(0, str(PROJECT_ROOT / "source"))

from so101_tasks import SO101PickPlaceTask, SO101PositionController


SCENE_PATH = str(PROJECT_ROOT / "scenes/so101_pick_place_task.usda")
ROBOT_DESCRIPTION_PATH = str(PROJECT_ROOT / "configs/so101_lula_robot_description.yaml")
URDF_PATH = str(PROJECT_ROOT / "assets/robots/so101/so101_new_calib.urdf")


def quaternion_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(min(np.linalg.norm(a - b), np.linalg.norm(a + b)))


def main() -> None:
    assert open_stage(SCENE_PATH), f"Unable to open {SCENE_PATH}"
    world = World(stage_units_in_meters=1.0, backend="numpy", device="cpu")
    task = SO101PickPlaceTask(world)
    task.initialize()
    reset_state = task.reset(settle=True)

    controller = SO101PositionController(
        task,
        robot_description_path=ROBOT_DESCRIPTION_PATH,
        urdf_path=URDF_PATH,
    )
    cube = reset_state["cube_position"]
    target = reset_state["target_position"]
    waypoints = [
        ("pre_grasp", cube + np.array([0.0, 0.0, 0.10])),
        ("grasp", cube + np.array([0.0, 0.0, 0.045])),
        ("lift", cube + np.array([0.0, 0.0, 0.12])),
        ("pre_place", target + np.array([0.0, 0.0, 0.12])),
        ("place", target + np.array([0.0, 0.0, 0.045])),
        ("retreat", target + np.array([0.0, 0.0, 0.14])),
    ]

    initial_base_position, initial_base_orientation = task.robot.get_world_pose()
    results = []
    for name, position in waypoints:
        reached = controller.move_to(name, position)
        results.append(
            {
                "name": reached.name,
                "target_position_m": reached.target_position.tolist(),
                "achieved_position_m": reached.achieved_position.tolist(),
                "position_error_m": reached.position_error,
                "ik_success": reached.ik_success,
                "joint_positions_rad": reached.joint_positions.tolist(),
            }
        )

    task.robot.apply_action(
        ArticulationAction(joint_positions=task.config.home_joint_positions.copy())
    )
    task.step(240)
    final_base_position, final_base_orientation = task.robot.get_world_pose()
    base_position_error = float(np.linalg.norm(final_base_position - initial_base_position))
    base_orientation_error = quaternion_distance(
        final_base_orientation, initial_base_orientation
    )
    assert base_position_error <= 1.0e-5
    assert base_orientation_error <= 1.0e-5

    result = {
        "scene": SCENE_PATH,
        "status": "pass",
        "end_effector_frame": controller.end_effector_frame,
        "lula_joint_names": controller.solver.get_joint_names(),
        "max_position_error_m": max(item["position_error_m"] for item in results),
        "base_position_error_m": base_position_error,
        "base_orientation_error": base_orientation_error,
        "waypoints": results,
    }
    output = PROJECT_ROOT / "logs/so101_reach_validation.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("SO101_REACH_VALIDATION_PASS " + json.dumps(result), flush=True)


try:
    main()
finally:
    simulation_app.close()
