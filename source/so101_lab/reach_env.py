"""First SO-101 Isaac Lab task: reach a fixed end-effector target."""

from collections.abc import Sequence

import torch

from isaaclab.assets import ArticulationCfg
from isaaclab.envs import DirectRLEnv, DirectRLEnvCfg
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sim import SimulationCfg
from isaaclab.utils import configclass

from .asset_cfg import SO101_CFG, SO101_JOINT_NAMES


@configclass
class SO101ReachSceneCfg(InteractiveSceneCfg):
    robot: ArticulationCfg = SO101_CFG


@configclass
class SO101ReachEnvCfg(DirectRLEnvCfg):
    """A small state-only reaching task with bounded joint-position actions."""

    decimation = 2
    episode_length_s = 5.0
    action_space = 6
    observation_space = 24
    state_space = 0

    sim: SimulationCfg = SimulationCfg(dt=1.0 / 120.0, render_interval=decimation)
    scene: SO101ReachSceneCfg = SO101ReachSceneCfg(
        num_envs=8,
        env_spacing=2.0,
        replicate_physics=True,
        clone_in_fabric=False,
    )

    target_position = (0.300, 0.0, 0.100)
    arm_action_scale_rad = 0.02
    gripper_action_scale_rad = 0.04
    success_distance_m = 0.025


class SO101ReachEnv(DirectRLEnv):
    """Observe joint and tool state; command small joint-position increments."""

    cfg: SO101ReachEnvCfg

    def __init__(
        self,
        cfg: SO101ReachEnvCfg,
        render_mode: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(cfg, render_mode, **kwargs)
        self.robot = self.scene["robot"]
        if tuple(self.robot.joint_names) != SO101_JOINT_NAMES:
            raise RuntimeError(f"Unexpected SO-101 joints: {self.robot.joint_names}")
        self.ee_body_index = self.robot.body_names.index("gripper_frame_link")
        self.goal = torch.tensor(
            cfg.target_position,
            dtype=torch.float32,
            device=self.device,
        ).repeat(self.num_envs, 1)
        self.action_scale = torch.tensor(
            [cfg.arm_action_scale_rad] * 5 + [cfg.gripper_action_scale_rad],
            dtype=torch.float32,
            device=self.device,
        )
        self.actions = torch.zeros((self.num_envs, 6), device=self.device)
        self.joint_targets = self.robot.data.default_joint_pos.torch.clone()

    def _tool_position(self) -> torch.Tensor:
        return (
            self.robot.data.body_pos_w.torch[:, self.ee_body_index, :]
            - self.scene.env_origins
        )

    def _pre_physics_step(self, actions: torch.Tensor) -> None:
        self.actions = torch.clamp(actions.clone(), -1.0, 1.0)
        requested = self.robot.data.joint_pos.torch + self.actions * self.action_scale
        limits = self.robot.data.soft_joint_pos_limits.torch
        self.joint_targets = torch.clamp(
            requested,
            min=limits[:, :, 0],
            max=limits[:, :, 1],
        )

    def _apply_action(self) -> None:
        self.robot.actuators.target_command.set_position_index(value=self.joint_targets)

    def _get_observations(self) -> dict:
        policy = torch.cat(
            (
                self.robot.data.joint_pos.torch,
                self.robot.data.joint_vel.torch,
                self._tool_position(),
                self.goal,
                self.actions,
            ),
            dim=-1,
        )
        return {"policy": policy}

    def _get_rewards(self) -> torch.Tensor:
        distance = torch.linalg.vector_norm(
            self._tool_position() - self.goal,
            dim=1,
        )
        proximity = torch.exp(-4.0 * distance)
        action_penalty = 0.001 * torch.sum(self.actions.square(), dim=1)
        success_bonus = (distance < self.cfg.success_distance_m).float()
        return proximity - action_penalty + success_bonus

    def _get_dones(self) -> tuple[torch.Tensor, torch.Tensor]:
        distance = torch.linalg.vector_norm(
            self._tool_position() - self.goal,
            dim=1,
        )
        reached = distance < self.cfg.success_distance_m
        timeout = self.episode_length_buf >= self.max_episode_length - 1
        return reached, timeout

    def _reset_idx(self, env_ids: Sequence[int] | None) -> None:
        if env_ids is None:
            env_ids = self.robot._ALL_INDICES
        super()._reset_idx(env_ids)
        joint_pos = self.robot.data.default_joint_pos.torch[env_ids].clone()
        joint_vel = self.robot.data.default_joint_vel.torch[env_ids].clone()
        self.robot.write_joint_position_to_sim_index(position=joint_pos, env_ids=env_ids)
        self.robot.write_joint_velocity_to_sim_index(velocity=joint_vel, env_ids=env_ids)
        self.robot.actuators.target_command.set_position_index(value=joint_pos, env_ids=env_ids)
        self.joint_targets[env_ids] = joint_pos
        self.actions[env_ids] = 0.0
