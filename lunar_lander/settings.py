"""Central game tuning values."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GameSettings:
    screen_width: int = 1280
    screen_height: int = 720
    target_fps: int = 60

    base_gravity: float = 22.0
    thrust_acceleration: float = 48.0
    rotation_speed: float = 90.0
    fuel_capacity: float = 100.0
    starting_lives: int = 3
    fuel_burn_per_second: float = 15.0
    landing_fuel_reward: float = 18.0

    safe_horizontal_speed: float = 35.0
    safe_vertical_speed: float = 45.0
    safe_angle_degrees: float = 12.0

    lander_half_width: float = 20.0
    lander_bottom_offset: float = 18.0
    round_transition_seconds: float = 2.2

    @property
    def world_width(self) -> float:
        return float(self.screen_width)
