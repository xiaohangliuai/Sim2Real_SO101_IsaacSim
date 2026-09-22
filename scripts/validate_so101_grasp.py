"""Run repeated physics validation of the SO-101 grasp-and-lift sequence."""

import json
import sys
import traceback
from pathlib import Path

import numpy as np

from isaacsim import SimulationApp


simulation_app = SimulationApp({"headless": True})

from isaacsim.core.api import World
from isaacsim.core.utils.stage import open_stage


PROJECT_ROOT = Path("/workspace/so101")
sys.path.insert(0, str(PROJECT_ROOT / "source"))

from so101_tasks import (
    SO101GraspController,
    SO101PickPlaceTask,
    SO101PositionController,
)


SCENE_PATH = str(PROJECT_ROOT / "scenes/so101_pick_place_task.usda")
ROBOT_DESCRIPTION_PATH = str(
    PROJECT_ROOT / "configs/so101_lula_grasp_robot_description.yaml"
)
URDF_PATH = str(PROJECT_ROOT / "assets/robots/so101/so101_new_calib.urdf")
TRIAL_COUNT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 20
MINIMUM_SUCCESS_RATE = 0.90


def main() -> None:
    print("SO101_GRASP_STAGE opening_scene", flush=True)
    assert open_stage(SCENE_PATH), f"Unable to open {SCENE_PATH}"
    world = World(stage_units_in_meters=1.0, backend="numpy", device="cpu")
    task = SO101PickPlaceTask(world)
    task.initialize()
    print("SO101_GRASP_STAGE task_initialized", flush=True)
    position_controller = SO101PositionController(
        task,
        robot_description_path=ROBOT_DESCRIPTION_PATH,
        urdf_path=URDF_PATH,
    )
    grasp_controller = SO101GraspController(task, position_controller)
    print("SO101_GRASP_STAGE controller_initialized", flush=True)

    trials = []
    for trial_index in range(TRIAL_COUNT):
        grasp = grasp_controller.execute()
        trial = {
            "trial": trial_index + 1,
            "success": grasp.success,
            "states": list(grasp.state_history),
            "cube_start_position_m": grasp.cube_start_position.tolist(),
            "cube_lift_position_m": grasp.cube_lift_position.tolist(),
            "cube_after_close_position_m": grasp.cube_after_close_position.tolist(),
            "grasp_end_effector_position_m": grasp.grasp_end_effector_position.tolist(),
            "grasp_end_effector_rotation": grasp.grasp_end_effector_rotation.tolist(),
            "grasp_joint_positions_rad": grasp.grasp_joint_positions.tolist(),
            "cube_hold_position_m": grasp.cube_hold_position.tolist(),
            "end_effector_position_m": grasp.end_effector_position.tolist(),
            "lift_height_m": grasp.lift_height_m,
            "grasp_distance_m": grasp.grasp_distance_m,
            "hold_drift_m": grasp.hold_drift_m,
            "gripper_position_rad": grasp.gripper_position_rad,
        }
        trials.append(trial)
        print("SO101_GRASP_TRIAL " + json.dumps(trial), flush=True)

    successes = sum(trial["success"] for trial in trials)
    success_rate = successes / TRIAL_COUNT
    result = {
        "scene": SCENE_PATH,
        "status": "pass" if success_rate >= MINIMUM_SUCCESS_RATE else "fail",
        "trial_count": TRIAL_COUNT,
        "successful_trials": successes,
        "success_rate": success_rate,
        "minimum_success_rate": MINIMUM_SUCCESS_RATE,
        "minimum_lift_height_m": min(trial["lift_height_m"] for trial in trials),
        "maximum_grasp_distance_m": max(
            trial["grasp_distance_m"] for trial in trials
        ),
        "maximum_hold_drift_m": max(trial["hold_drift_m"] for trial in trials),
        "trials": trials,
    }
    output = PROJECT_ROOT / "logs/so101_grasp_validation.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    assert success_rate >= MINIMUM_SUCCESS_RATE, json.dumps(result)
    print("SO101_GRASP_VALIDATION_PASS " + json.dumps(result), flush=True)


try:
    main()
except Exception:
    traceback.print_exc()
    raise
finally:
    simulation_app.close()
