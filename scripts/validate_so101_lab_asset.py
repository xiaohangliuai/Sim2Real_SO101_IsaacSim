"""Validate the SO-101 USD as a replicated Isaac Lab articulation."""

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--num_envs", type=int, choices=(1, 8), default=1)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch

from isaaclab.scene import InteractiveScene, InteractiveSceneCfg
from isaaclab.sim import SimulationCfg, SimulationContext
from isaaclab.utils import configclass

PROJECT_ROOT = Path("/workspace/so101")
sys.path.insert(0, str(PROJECT_ROOT / "source"))

from so101_lab import SO101_CFG, SO101_JOINT_NAMES


@configclass
class SO101SceneCfg(InteractiveSceneCfg):
    """One or more isolated copies of the SO-101 articulation."""

    robot = SO101_CFG


def step(sim: SimulationContext, scene: InteractiveScene, count: int) -> None:
    dt = sim.get_physics_dt()
    for _ in range(count):
        scene.write_data_to_sim()
        sim.step()
        scene.update(dt)


def main() -> None:
    sim = SimulationContext(SimulationCfg(device=args_cli.device, dt=1.0 / 120.0))
    scene = InteractiveScene(SO101SceneCfg(num_envs=args_cli.num_envs, env_spacing=2.0))
    sim.reset()
    robot = scene["robot"]

    names = tuple(robot.joint_names)
    assert names == SO101_JOINT_NAMES, f"Unexpected joint order: {names}"
    assert robot.num_instances == args_cli.num_envs
    assert robot.num_joints == 6

    home_pos = robot.data.default_joint_pos.clone()
    home_vel = robot.data.default_joint_vel.clone()
    assert torch.allclose(home_pos, torch.zeros_like(home_pos), atol=1.0e-6)
    assert torch.allclose(home_vel, torch.zeros_like(home_vel), atol=1.0e-6)

    robot.write_joint_state_to_sim(home_pos, home_vel)
    robot.set_joint_position_target(home_pos)
    scene.reset()
    step(sim, scene, 120)
    settled = robot.data.joint_pos.clone()

    target = home_pos.clone()
    target[:, 0] = 0.08
    target[:, 5] = 0.15
    robot.set_joint_position_target(target)
    step(sim, scene, 180)
    moved = robot.data.joint_pos.clone()
    arm_motion = moved[:, 0] - settled[:, 0]
    gripper_motion = moved[:, 5] - settled[:, 5]
    assert bool(torch.all(arm_motion > 0.04).item()), arm_motion.tolist()
    assert bool(torch.all(gripper_motion > 0.08).item()), gripper_motion.tolist()

    robot.write_joint_state_to_sim(home_pos, home_vel)
    robot.set_joint_position_target(home_pos)
    scene.reset()
    step(sim, scene, 120)
    reset_pos = robot.data.joint_pos.clone()
    reset_error = float(torch.max(torch.abs(reset_pos - settled)).item())
    assert reset_error < 0.03, f"Reset error: {reset_error:.6f} rad"
    assert bool(torch.isfinite(reset_pos).all().item())

    result = {
        "status": "pass",
        "num_envs": args_cli.num_envs,
        "device": str(robot.device),
        "joint_names": names,
        "num_joints": robot.num_joints,
        "minimum_shoulder_pan_motion_rad": float(torch.min(arm_motion).item()),
        "minimum_gripper_motion_rad": float(torch.min(gripper_motion).item()),
        "maximum_reset_repeatability_error_rad": reset_error,
    }
    output = PROJECT_ROOT / f"logs/so101_lab_asset_{args_cli.num_envs}env.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("SO101_LAB_ASSET_VALIDATION_PASS " + json.dumps(result), flush=True)


try:
    main()
except Exception:
    traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1)
else:
    # Kit stop can hang for this imported USD. Docker process exit frees resources.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
