"""Central game tuning values."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GameSettings:
    screen_width: int = 1280
    screen_height: int = 720
    target_fps: int = 60
    # 표시용 스케일: 물리 계산은 픽셀 단위 그대로, HUD 표기만 미터로 환산한다.
    pixels_per_meter: float = 10.0
    map_screens: int = 5

    # 금성(8.87 m/s²)에서도 TWR≈1.24로 착륙 가능해야 하므로.
    thrust_acceleration: float = 110.0
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
        return float(self.screen_width * self.map_screens)
