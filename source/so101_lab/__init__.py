"""Isaac Lab configurations for the SO-101 project."""

import gymnasium as gym

from .asset_cfg import SO101_CFG, SO101_JOINT_NAMES

gym.register(
    id="SO101-Reach-Direct-v0",
    entry_point="so101_lab.reach_env:SO101ReachEnv",
    disable_env_checker=True,
    kwargs={"env_cfg_entry_point": "so101_lab.reach_env:SO101ReachEnvCfg"},
)

__all__ = ["SO101_CFG", "SO101_JOINT_NAMES"]
