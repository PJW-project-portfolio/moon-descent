"""Game progression independent of rendering."""

from dataclasses import dataclass
from enum import Enum, auto
import random

from .models import Lander, LandingResult
from .settings import GameSettings
from .terrain import Terrain


class GameState(Enum):
    TITLE = auto()
    PLAYING = auto()
    PAUSED = auto()
    LANDED = auto()
    CRASHED = auto()
    GAME_OVER = auto()


@dataclass
class GameSession:
    settings: GameSettings
    rng: random.Random
    state: GameState = GameState.TITLE
    score: int = 0
    high_score: int = 0
    final_score: int = 0
    lives: int = 3
    stage: int = 1
    terrain: Terrain | None = None
    lander: Lander | None = None
    stage_start_fuel: float = 100.0
    transition_elapsed: float = 0.0
    last_award: int = 0

    @classmethod
    def create(
        cls,
        settings: GameSettings | None = None,
        seed: int | None = None,
    ) -> "GameSession":
        return cls(settings or GameSettings(), random.Random(seed))

    @property
    def gravity(self) -> float:
        difficulty_scale = 1.0 + min(self.stage - 1, 12) * 0.05
        return self.settings.base_gravity * difficulty_scale

    def new_game(self) -> None:
        self.score = 0
        self.final_score = 0
        self.lives = self.settings.starting_lives
        self.stage = 1
        self.last_award = 0
        self._prepare_round(self.settings.fuel_capacity)

    def _prepare_round(self, fuel: float) -> None:
        self.stage_start_fuel = fuel
        self.terrain = Terrain.generate(
            self.settings.screen_width,
            self.settings.screen_height,
            self.stage,
            self.rng,
        )
        self._spawn_lander(fuel)

    def _spawn_lander(self, fuel: float) -> None:
        self.lander = Lander(
            x=self.settings.screen_width / 2.0,
            y=105.0,
            velocity_x=0.0,
            velocity_y=0.0,
            fuel=fuel,
        )
        self.transition_elapsed = 0.0
        self.state = GameState.PLAYING

    def toggle_pause(self) -> None:
        if self.state == GameState.PLAYING:
            self.state = GameState.PAUSED
        elif self.state == GameState.PAUSED:
            self.state = GameState.PLAYING

    def update(
        self,
        dt: float,
        rotation_direction: float = 0.0,
        thrust_requested: bool = False,
    ) -> None:
        if self.state == GameState.PLAYING:
            remaining = max(0.0, dt)
            while remaining > 1e-9 and self.state == GameState.PLAYING:
                step = min(remaining, 0.01)
                self._update_playing(
                    step, rotation_direction, thrust_requested
                )
                remaining -= step
        elif self.state in (GameState.LANDED, GameState.CRASHED):
            self.transition_elapsed += dt
            if self.transition_elapsed >= self.settings.round_transition_seconds:
                self.advance_after_result()

    def _update_playing(
        self,
        dt: float,
        rotation_direction: float,
        thrust_requested: bool,
    ) -> None:
        assert self.lander is not None
        assert self.terrain is not None
        self.lander.update(
            dt,
            rotation_direction,
            thrust_requested,
            self.gravity,
            self.settings,
        )

        collision_points = self.lander.collision_points()
        has_contact = any(
            point_y >= self.terrain.height_at(point_x)
            for point_x, point_y in collision_points
        )
        if not has_contact:
            return

        pad = self.terrain.pad_at(self.lander.x)
        result = self.lander.evaluate_landing(
            pad.start_x if pad else None,
            pad.end_x if pad else None,
            self.settings,
        )
        if result == LandingResult.LANDED and pad is not None:
            lowest_gear_offset = max(
                point_y - self.lander.y
                for _, point_y in self.lander.landing_gear_points()
            )
            self.lander.y = pad.y - lowest_gear_offset
        self.lander.thrusting = False
        self.transition_elapsed = 0.0

        if result == LandingResult.LANDED and pad is not None:
            softness = max(
                0.0,
                1.0
                - abs(self.lander.velocity_y)
                / self.settings.safe_vertical_speed,
            )
            self.last_award = int((100 + softness * 100) * pad.multiplier)
            self.score += self.last_award
            self.high_score = max(self.high_score, self.score)
            self.lander.fuel = min(
                self.settings.fuel_capacity,
                self.lander.fuel + self.settings.landing_fuel_reward,
            )
            self.state = GameState.LANDED
        else:
            self.last_award = 0
            self.lives = max(0, self.lives - 1)
            if self.lives == 0:
                self.final_score = self.score
                self.high_score = max(self.high_score, self.final_score)
                self.state = GameState.GAME_OVER
            else:
                self.state = GameState.CRASHED

    def advance_after_result(self) -> None:
        if self.lander is None:
            return
        if self.state == GameState.LANDED:
            fuel = self.lander.fuel
            self.stage += 1
            self._prepare_round(fuel)
        elif self.state == GameState.CRASHED:
            retry_fuel = (
                self.settings.fuel_capacity
                if self.stage == 1
                else self.stage_start_fuel
            )
            self._spawn_lander(retry_fuel)

    def restart(self) -> None:
        self.new_game()

    @property
    def altitude(self) -> float:
        if self.lander is None or self.terrain is None:
            return 0.0
        clearances = (
            self.terrain.height_at(point_x) - point_y
            for point_x, point_y in self.lander.landing_gear_points()
        )
        return max(0.0, min(clearances))
