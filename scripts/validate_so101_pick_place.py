"""Run repeated full-cycle validation of the SO-101 pick-and-place task."""

import json
import sys
import traceback
from pathlib import Path

from isaacsim import SimulationApp


simulation_app = SimulationApp({"headless": True})

from isaacsim.core.api import World
from isaacsim.core.utils.stage import open_stage


PROJECT_ROOT = Path("/workspace/so101")
sys.path.insert(0, str(PROJECT_ROOT / "source"))

from so101_tasks import (
    SO101GraspController,
    SO101PickPlaceController,
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
    assert open_stage(SCENE_PATH), f"Unable to open {SCENE_PATH}"
    world = World(stage_units_in_meters=1.0, backend="numpy", device="cpu")
    task = SO101PickPlaceTask(world)
    task.initialize()
    position_controller = SO101PositionController(
        task,
        robot_description_path=ROBOT_DESCRIPTION_PATH,
        urdf_path=URDF_PATH,
    )
    grasp_controller = SO101GraspController(task, position_controller)
    controller = SO101PickPlaceController(
        task, position_controller, grasp_controller
    )

    trials = []
    for trial_index in range(TRIAL_COUNT):
        placed = controller.execute()
        trial = {
            "trial": trial_index + 1,
            "success": placed.success,
            "states": list(placed.state_history),
            "desired_cube_position_m": placed.desired_cube_position.tolist(),
            "placed_cube_position_m": placed.placed_cube_position.tolist(),
            "released_cube_position_m": placed.released_cube_position.tolist(),
            "final_cube_position_m": placed.final_cube_position.tolist(),
            "final_cube_velocity_m_s": placed.final_cube_velocity.tolist(),
            "final_joint_positions_rad": placed.final_joint_positions.tolist(),
            "target_xy_error_m": placed.target_xy_error_m,
            "height_error_m": placed.height_error_m,
            "final_speed_m_s": placed.final_speed_m_s,
            "home_error_rad": placed.home_error_rad,
        }
        trials.append(trial)
        print("SO101_PICK_PLACE_TRIAL " + json.dumps(trial), flush=True)

    successes = sum(trial["success"] for trial in trials)
    success_rate = successes / TRIAL_COUNT
    result = {
        "scene": SCENE_PATH,
        "status": "pass" if success_rate >= MINIMUM_SUCCESS_RATE else "fail",
        "trial_count": TRIAL_COUNT,
        "successful_trials": successes,
        "success_rate": success_rate,
        "minimum_success_rate": MINIMUM_SUCCESS_RATE,
        "maximum_target_xy_error_m": max(
            trial["target_xy_error_m"] for trial in trials
        ),
        "maximum_height_error_m": max(trial["height_error_m"] for trial in trials),
        "maximum_final_speed_m_s": max(
            trial["final_speed_m_s"] for trial in trials
        ),
        "maximum_home_error_rad": max(trial["home_error_rad"] for trial in trials),
        "trials": trials,
    }
    output = PROJECT_ROOT / "logs/so101_pick_place_validation.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    assert success_rate >= MINIMUM_SUCCESS_RATE, json.dumps(result)
    print("SO101_PICK_PLACE_VALIDATION_PASS " + json.dumps(result), flush=True)


try:
    main()
except Exception:
    traceback.print_exc()
    raise
finally:
    simulation_app.close()
