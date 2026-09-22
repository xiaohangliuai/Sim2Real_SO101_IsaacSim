"""Validate the composed SO-101 pick-place scene in Isaac Sim.

Run with:
    ./scripts/isaac-sim.sh python /workspace/so101/scripts/validate_pick_place_scene.py
"""

import json
from pathlib import Path

import numpy as np
from isaacsim import SimulationApp


simulation_app = SimulationApp({"headless": True})

from isaacsim.core.api import World
from isaacsim.core.prims import RigidPrim
from isaacsim.core.utils.stage import open_stage
import omni.usd
from pxr import Usd, UsdPhysics


SCENE_PATH = "/workspace/so101/scenes/so101_pick_place_task.usda"
CUBE_PATH = "/World/TaskObjects/PickCube"
TARGET_PATH = "/World/TaskObjects/PlaceTarget"
ROBOT_PATH = "/World/so101_new_calib"
GRIPPER_FRAME_PATH = f"{ROBOT_PATH}/gripper_frame_link"


def main() -> None:
    assert open_stage(SCENE_PATH), f"Unable to open {SCENE_PATH}"
    world = World(stage_units_in_meters=1.0)
    stage = omni.usd.get_context().get_stage()
    assert stage.GetDefaultPrim().GetPath() == "/World"
    assert stage.GetMetadata("metersPerUnit") == 1.0

    cube_prim = stage.GetPrimAtPath(CUBE_PATH)
    target_prim = stage.GetPrimAtPath(TARGET_PATH)
    frame_prim = stage.GetPrimAtPath(GRIPPER_FRAME_PATH)
    assert cube_prim.IsValid()
    assert target_prim.IsValid()
    assert frame_prim.IsValid()
    assert cube_prim.GetAttribute("physics:approximation").Get() == "convexHull"
    assert cube_prim.HasAPI(UsdPhysics.RigidBodyAPI)
    assert not target_prim.HasAPI(UsdPhysics.RigidBodyAPI)
    assert target_prim.GetRelationship("material:binding").GetTargets()

    articulation_paths = [
        str(prim.GetPath())
        for prim in stage.Traverse()
        if prim.HasAPI(UsdPhysics.ArticulationRootAPI)
    ]
    assert articulation_paths == [f"{ROBOT_PATH}/root_joint"], articulation_paths

    cube = world.scene.add(RigidPrim(prim_paths_expr=CUBE_PATH, name="pick_cube"))
    world.reset()
    initial_positions, _ = cube.get_world_poses()
    initial_position = initial_positions[0]

    robot = stage.GetPrimAtPath(ROBOT_PATH)
    robot_initial_translation = robot.GetAttribute("xformOp:translate:tableMount").Get()

    for _ in range(240):
        world.step(render=False)

    final_positions, _ = cube.get_world_poses()
    final_position = final_positions[0]
    linear_velocity = cube.get_linear_velocities()[0]
    angular_velocity = cube.get_angular_velocities()[0]
    robot_final_translation = robot.GetAttribute("xformOp:translate:tableMount").Get()

    assert float(initial_position[2] - final_position[2]) > 0.005
    assert 0.765 <= float(final_position[2]) <= 0.775, final_position
    assert float(np.linalg.norm(linear_velocity)) < 0.02, linear_velocity
    assert float(np.linalg.norm(angular_velocity)) < 0.2, angular_velocity
    assert robot_initial_translation == robot_final_translation

    result = {
        "scene": SCENE_PATH,
        "articulation_paths": articulation_paths,
        "cube_initial_position": initial_position.tolist(),
        "cube_final_position": final_position.tolist(),
        "cube_linear_speed": float(np.linalg.norm(linear_velocity)),
        "cube_angular_speed": float(np.linalg.norm(angular_velocity)),
        "robot_mount_translation": list(robot_final_translation),
        "status": "pass",
    }
    output = Path("/workspace/so101/logs/pick_place_scene_validation.json")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("SO101_PICK_PLACE_SCENE_PASS " + json.dumps(result), flush=True)


try:
    main()
finally:
    simulation_app.close()
