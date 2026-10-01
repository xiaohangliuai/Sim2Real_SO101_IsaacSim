"""Exercise the SO-101 fixed-target Isaac Lab environment."""

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--num_envs", type=int, choices=(1, 8), default=8)
parser.add_argument("--steps", type=int, default=120)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import gymnasium as gym
import torch

PROJECT_ROOT = Path("/workspace/so101")
sys.path.insert(0, str(PROJECT_ROOT / "source"))

import so101_lab  # noqa: F401
from so101_lab.reach_env import SO101ReachEnvCfg


def main() -> None:
    assert args_cli.steps >= 2
    cfg = SO101ReachEnvCfg()
    cfg.scene.num_envs = args_cli.num_envs
    cfg.sim.device = args_cli.device
    cfg.seed = 42
    env = gym.make("SO101-Reach-Direct-v0", cfg=cfg)
    observations, _ = env.reset(seed=42)
    policy = observations["policy"]
    assert policy.shape == (args_cli.num_envs, 24), policy.shape
    assert bool(torch.isfinite(policy).all().item())

    minimum_distance = float("inf")
    maximum_commanded_increment = 0.0
    reset_count = 0
    for step_index in range(args_cli.steps):
        previous_joint_pos = env.unwrapped.robot.data.joint_pos.clone()
        actions = torch.zeros((args_cli.num_envs, 6), device=env.unwrapped.device)
        actions[:, 0] = 2.0 if step_index % 2 == 0 else -2.0
        actions[:, 5] = 2.0
        with torch.inference_mode():
            observations, rewards, terminated, truncated, _ = env.step(actions)
        policy = observations["policy"]
        assert policy.shape == (args_cli.num_envs, 24)
        assert rewards.shape == (args_cli.num_envs,)
        assert bool(torch.isfinite(policy).all().item())
        assert bool(torch.isfinite(rewards).all().item())
        assert bool(torch.all(torch.abs(env.unwrapped.actions) <= 1.0).item())
        commanded_increment = torch.abs(
            env.unwrapped.joint_targets - previous_joint_pos
        )
        assert bool(
            torch.all(commanded_increment <= env.unwrapped.action_scale + 1.0e-5).item()
        )
        maximum_commanded_increment = max(
            maximum_commanded_increment,
            float(torch.max(commanded_increment).item()),
        )
        distance = torch.linalg.vector_norm(policy[:, 12:15] - policy[:, 15:18], dim=1)
        minimum_distance = min(minimum_distance, float(torch.min(distance).item()))
        reset_count += int(torch.count_nonzero(terminated | truncated).item())

    with torch.inference_mode():
        observations, _ = env.reset(seed=43)
    assert observations["policy"].shape == (args_cli.num_envs, 24)
    assert bool(torch.isfinite(observations["policy"]).all().item())
    result = {
        "status": "pass",
        "task": "SO101-Reach-Direct-v0",
        "num_envs": args_cli.num_envs,
        "steps": args_cli.steps,
        "observation_shape": list(observations["policy"].shape),
        "action_shape": list(env.action_space.shape),
        "minimum_target_distance_m": minimum_distance,
        "maximum_commanded_increment_rad": maximum_commanded_increment,
        "automatic_resets": reset_count,
        "manual_resets": 1,
    }
    output = PROJECT_ROOT / f"logs/so101_reach_env_{args_cli.num_envs}env.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("SO101_REACH_ENV_VALIDATION_PASS " + json.dumps(result), flush=True)


try:
    main()
except Exception:
    traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1)
else:
    # The disposable validation container releases Kit resources on process exit.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
