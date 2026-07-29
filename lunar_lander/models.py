"""Physics model and landing evaluation."""

from dataclasses import dataclass
from enum import Enum, auto
import math

from .settings import GameSettings


class LandingResult(Enum):
    FLYING = auto()
    LANDED = auto()
    CRASHED = auto()


def normalized_angle(angle_degrees: float) -> float:
    """Return an angle in the [-180, 180) range."""
    return (angle_degrees + 180.0) % 360.0 - 180.0


@dataclass
class Lander:
    x: float
    y: float
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    angle: float = 0.0
    fuel: float = 100.0
    thrusting: bool = False

    def update(
        self,
        dt: float,
        rotation_direction: float,
        thrust_requested: bool,
        gravity: float,
        settings: GameSettings,
    ) -> None:
        """Advance the lander with stable substeps and exact fuel-limited thrust."""
        remaining = max(0.0, dt)
        fired_thruster = False

        while remaining > 1e-9:
            step = min(remaining, 0.01)
            self.angle = normalized_angle(
                self.angle + rotation_direction * settings.rotation_speed * step
            )

            self.velocity_y += gravity * step
            thrust_duration = 0.0
            if thrust_requested and self.fuel > 0.0:
                if settings.fuel_burn_per_second > 0.0:
                    thrust_duration = min(
                        step, self.fuel / settings.fuel_burn_per_second
                    )
                    self.fuel = max(
                        0.0,
                        self.fuel
                        - settings.fuel_burn_per_second * thrust_duration,
                    )
                else:
                    thrust_duration = step

            if thrust_duration > 0.0:
                radians = math.radians(self.angle)
                thrust_delta_v = settings.thrust_acceleration * thrust_duration
                self.velocity_x += math.sin(radians) * thrust_delta_v
                self.velocity_y -= math.cos(radians) * thrust_delta_v
                fired_thruster = True

            self.x = (self.x + self.velocity_x * step) % settings.world_width
            self.y += self.velocity_y * step
            remaining -= step

        self.thrusting = fired_thruster

    def _world_point(
        self, local_x: float, local_y: float
    ) -> tuple[float, float]:
        radians = math.radians(self.angle)
        world_x = (
            self.x
            + local_x * math.cos(radians)
            - local_y * math.sin(radians)
        )
        world_y = (
            self.y
            + local_x * math.sin(radians)
            + local_y * math.cos(radians)
        )
        return world_x, world_y

    def landing_gear_points(self) -> tuple[tuple[float, float], ...]:
        """Return the rendered landing-foot endpoints in world coordinates."""
        return tuple(
            self._world_point(local_x, 18.0)
            for local_x in (-20.0, -12.0, 12.0, 20.0)
        )

    def collision_points(self) -> tuple[tuple[float, float], ...]:
        """Return body and landing-gear points used for terrain collision."""
        local_points = (
            (-10.0, -10.0),
            (10.0, -10.0),
            (13.0, 8.0),
            (-13.0, 8.0),
            (-20.0, 18.0),
            (-12.0, 18.0),
            (12.0, 18.0),
            (20.0, 18.0),
        )
        return tuple(self._world_point(x, y) for x, y in local_points)

    def evaluate_landing(
        self,
        pad_start: float | None,
        pad_end: float | None,
        settings: GameSettings,
    ) -> LandingResult:
        """Evaluate touchdown using pad clearance, speed and orientation."""
        if pad_start is None or pad_end is None:
            return LandingResult.CRASHED

        gear_x_positions = [point[0] for point in self.landing_gear_points()]
        fits_on_pad = (
            min(gear_x_positions) >= pad_start
            and max(gear_x_positions) <= pad_end
        )
        safe_speed = (
            abs(self.velocity_x) <= settings.safe_horizontal_speed
            and 0.0 <= self.velocity_y <= settings.safe_vertical_speed
        )
        safe_angle = (
            abs(normalized_angle(self.angle)) <= settings.safe_angle_degrees
        )

        if fits_on_pad and safe_speed and safe_angle:
            return LandingResult.LANDED
        return LandingResult.CRASHED
