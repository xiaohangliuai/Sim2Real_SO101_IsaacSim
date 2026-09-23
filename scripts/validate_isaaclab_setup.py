"""Validate a small parallel Isaac Lab environment on the local GPU."""

import argparse
import importlib.metadata
import json
import time
import traceback
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", default="Isaac-Cartpole-v0")
parser.add_argument("--num_envs", type=int, default=8)
parser.add_argument("--steps", type=int, default=240)
parser.add_argument("--seed", type=int, default=42)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import gymnasium as gym
import torch

import isaaclab
import isaaclab_tasks  # noqa: F401
import rsl_rl
from isaaclab_tasks.utils import parse_env_cfg


PROJECT_ROOT = Path("/workspace/so101")


def _distribution_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _tensor_shapes(value: Any) -> Any:
    if isinstance(value, torch.Tensor):
        return list(value.shape)
    if isinstance(value, dict):
        return {key: _tensor_shapes(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_tensor_shapes(item) for item in value]
    return type(value).__name__


def _all_finite(value: Any) -> bool:
    if isinstance(value, torch.Tensor):
        return bool(torch.isfinite(value).all().item())
    if isinstance(value, dict):
        return all(_all_finite(item) for item in value.values())
    if isinstance(value, (tuple, list)):
        return all(_all_finite(item) for item in value)
    return True


def main() -> None:
    if args_cli.num_envs not in (8, 16):
        raise ValueError("Use 8 or 16 environments for the setup validation")
    if args_cli.steps < 2:
        raise ValueError("Validation requires at least two simulation steps")

    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=True,
    )
    env = gym.make(args_cli.task, cfg=env_cfg)
    try:
        observations, _ = env.reset(seed=args_cli.seed)
        initial_shapes = _tensor_shapes(observations)
        assert _all_finite(observations), "Initial observations contain NaN or Inf"
        assert env.unwrapped.num_envs == args_cli.num_envs

        automatic_resets = 0
        manual_resets = 0
        reward_shape = None
        action_shape = list(env.action_space.shape)
        free_memory, total_memory = torch.cuda.mem_get_info()
        peak_device_used_bytes = total_memory - free_memory
        for step_index in range(args_cli.steps):
            actions = torch.zeros(
                env.action_space.shape,
                device=env.unwrapped.device,
            )
            with torch.inference_mode():
                observations, rewards, terminated, truncated, _ = env.step(actions)
            assert _all_finite(observations), (
                f"Observations contain NaN or Inf at step {step_index + 1}"
            )
            assert bool(torch.isfinite(rewards).all().item()), (
                f"Rewards contain NaN or Inf at step {step_index + 1}"
            )
            reward_shape = list(rewards.shape)
            free_memory, total_memory = torch.cuda.mem_get_info()
            peak_device_used_bytes = max(
                peak_device_used_bytes,
                total_memory - free_memory,
            )
            automatic_resets += int(torch.count_nonzero(terminated | truncated).item())
            if step_index + 1 == args_cli.steps // 2:
                with torch.inference_mode():
                    observations, _ = env.reset(seed=args_cli.seed + 1)
                assert _all_finite(observations)
                manual_resets += 1

        elapsed = time.perf_counter() - started
        result = {
            "status": "pass",
            "task": args_cli.task,
            "num_envs": args_cli.num_envs,
            "steps": args_cli.steps,
            "seed": args_cli.seed,
            "device": str(env.unwrapped.device),
            "gpu": torch.cuda.get_device_name(0),
            "gpu_total_memory_mib": round(
                torch.cuda.get_device_properties(0).total_memory / 1024**2,
                3,
            ),
            "gpu_peak_allocated_mib": round(
                torch.cuda.max_memory_allocated() / 1024**2,
                3,
            ),
            "gpu_peak_reserved_mib": round(
                torch.cuda.max_memory_reserved() / 1024**2,
                3,
            ),
            "gpu_peak_device_used_mib": round(
                peak_device_used_bytes / 1024**2,
                3,
            ),
            "elapsed_seconds": elapsed,
            "steps_per_second": args_cli.steps * args_cli.num_envs / elapsed,
            "observation_shapes": initial_shapes,
            "action_shape": action_shape,
            "reward_shape": reward_shape,
            "manual_resets": manual_resets,
            "automatic_resets": automatic_resets,
            "versions": {
                "isaac_lab": _distribution_version("isaaclab"),
                "isaac_lab_tasks": _distribution_version("isaaclab_tasks"),
                "torch": torch.__version__,
                "rsl_rl": _distribution_version("rsl-rl-lib"),
            },
            "module_paths": {
                "isaaclab": isaaclab.__file__,
                "rsl_rl": rsl_rl.__file__,
            },
        }
        output = PROJECT_ROOT / "logs/isaaclab_setup_validation.json"
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("SO101_ISAACLAB_VALIDATION_PASS " + json.dumps(result), flush=True)
    finally:
        env.close()


try:
    main()
except Exception:
    traceback.print_exc()
    raise
finally:
    simulation_app.close()
