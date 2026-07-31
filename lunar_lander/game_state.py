"""Game progression independent of rendering."""

from dataclasses import dataclass, field
from enum import Enum, auto
import random

from .leaderboard import Leaderboard, LeaderboardEntry, apply_name_key
from .models import Lander, LandingResult
from .settings import (
    GameSettings,
    MAX_TIME_BONUS_FUEL,
    TIME_BONUS_FUEL_PER_SECOND,
)
from .stages import STAGES, StageConfig
from .terrain import Terrain


class GameState(Enum):
    TITLE = auto()
    PLAYING = auto()
    PAUSED = auto()
    STAGE_CLEAR = auto()
    CRASHED = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    NAME_ENTRY = auto()
    LEADERBOARD = auto()


def calculate_time_bonus(
    par_time_seconds: float,
    elapsed_seconds: float,
    fuel_per_second: float = TIME_BONUS_FUEL_PER_SECOND,
    maximum_bonus: float = MAX_TIME_BONUS_FUEL,
) -> float:
    """Return the clamped fuel reward for finishing ahead of par."""
    return min(
        maximum_bonus,
        max(0.0, (par_time_seconds - elapsed_seconds) * fuel_per_second),
    )


@dataclass
class GameSession:
    settings: GameSettings
    rng: random.Random
    leaderboard: Leaderboard = field(default_factory=Leaderboard)
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
    stage_intro_elapsed: float = 0.0
    stage_elapsed: float = 0.0
    clear_elapsed: float = 0.0
    last_fuel_bonus: float = 0.0
    last_award: int = 0
    fresh_leaderboard_entry: LeaderboardEntry | None = None
    run_recorded: bool = False
    name_input: str = ""

    @classmethod
    def create(
        cls,
        settings: GameSettings | None = None,
        seed: int | None = None,
        leaderboard: Leaderboard | None = None,
    ) -> "GameSession":
        return cls(
            settings or GameSettings(),
            random.Random(seed),
            leaderboard if leaderboard is not None else Leaderboard(),
        )

    @property
    def current_stage(self) -> StageConfig:
        stage_index = min(max(self.stage - 1, 0), len(STAGES) - 1)
        return STAGES[stage_index]

    @property
    def gravity(self) -> float:
        return self.current_stage.gravity_ms2 * self.settings.pixels_per_meter

    @property
    def next_stage(self) -> StageConfig | None:
        if self.stage >= len(STAGES):
            return None
        return STAGES[self.stage]

    @property
    def stage_intro_active(self) -> bool:
        return (
            self.state == GameState.PLAYING
            and self.stage_intro_elapsed
            < self.settings.round_transition_seconds
        )

    def new_game(self) -> None:
        self.score = 0
        self.final_score = 0
        self.lives = self.settings.starting_lives
        self.stage = 1
        self.last_award = 0
        self.clear_elapsed = 0.0
        self.last_fuel_bonus = 0.0
        self.fresh_leaderboard_entry = None
        self.run_recorded = False
        self.name_input = ""
        self._prepare_round(self.settings.fuel_capacity)

    def _prepare_round(self, fuel: float) -> None:
        self.stage_start_fuel = fuel
        self.terrain = Terrain.generate(
            int(self.settings.world_width),
            self.settings.screen_height,
            self.stage,
            self.settings.screen_width / 2.0,
            self.settings.pad_exclusion_radius,
            self.rng,
        )
        self._spawn_lander(fuel)
        self.stage_intro_elapsed = 0.0

    def _spawn_lander(self, fuel: float) -> None:
        self.lander = Lander(
            x=self.settings.screen_width / 2.0,
            y=105.0,
            velocity_x=(
                self.current_stage.entry_speed_ms
                * self.settings.pixels_per_meter
            ),
            velocity_y=0.0,
            fuel=fuel,
        )
        self.transition_elapsed = 0.0
        self.stage_elapsed = 0.0
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
            self.stage_intro_elapsed = min(
                self.settings.round_transition_seconds,
                self.stage_intro_elapsed + max(0.0, dt),
            )
            remaining = max(0.0, dt)
            while remaining > 1e-9 and self.state == GameState.PLAYING:
                step = min(remaining, 0.01)
                self.stage_elapsed += step
                self._update_playing(
                    step, rotation_direction, thrust_requested
                )
                remaining -= step
        elif self.state == GameState.CRASHED:
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
            self.current_stage.fuel_burn_per_second,
        )

        collision_points = self.lander.collision_points()
        has_contact = any(
            point_y >= self.terrain.height_at(point_x)
            for point_x, point_y in collision_points
        )
        if not has_contact:
            return

        pad = self.terrain.pad_at(self.lander.x)
        pad_bounds = (
            pad.bounds_near(self.lander.x, self.terrain.width)
            if pad is not None
            else (None, None)
        )
        result = self.lander.evaluate_landing(
            pad_bounds[0],
            pad_bounds[1],
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
            base_award = 100 + softness * 100
            self.last_award = round(
                base_award * pad.multiplier * pad.distance_bonus
            )
            self.score += self.last_award
            self.high_score = max(self.high_score, self.score)
            self.clear_elapsed = self.stage_elapsed
            self.last_fuel_bonus = calculate_time_bonus(
                self.current_stage.par_time_seconds,
                self.clear_elapsed,
                self.settings.time_bonus_fuel_per_second,
                self.settings.max_time_bonus_fuel,
            )
            if self.stage == len(STAGES):
                self.final_score = self.score
                self.state = GameState.VICTORY
            else:
                self.state = GameState.STAGE_CLEAR
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
        if self.state == GameState.STAGE_CLEAR:
            if self.stage >= len(STAGES):
                return
            fuel = self.settings.fuel_capacity + self.last_fuel_bonus
            self.stage += 1
            self._prepare_round(fuel)
        elif self.state == GameState.CRASHED:
            retry_fuel = (
                self.settings.fuel_capacity
                if self.stage == 1
                else self.stage_start_fuel
            )
            self._spawn_lander(retry_fuel)

    def record_run(self, name: str) -> LeaderboardEntry:
        """Record this run at most once and expose it for UI highlighting."""
        if self.run_recorded and self.fresh_leaderboard_entry is not None:
            return self.fresh_leaderboard_entry
        self.final_score = self.score
        self.high_score = max(self.high_score, self.final_score)
        self.fresh_leaderboard_entry = self.leaderboard.add_entry(
            self.final_score,
            self.current_stage.name,
            name=name,
        )
        self.run_recorded = True
        return self.fresh_leaderboard_entry

    def begin_name_entry(self) -> None:
        if self.state not in (
            GameState.STAGE_CLEAR,
            GameState.VICTORY,
            GameState.GAME_OVER,
        ):
            return
        self.name_input = ""
        for char in self.leaderboard.last_name:
            self.name_input = apply_name_key(self.name_input, char)
        self.state = GameState.NAME_ENTRY

    def edit_name(self, char: str) -> None:
        if self.state == GameState.NAME_ENTRY:
            self.name_input = apply_name_key(self.name_input, char)

    def confirm_name_entry(self) -> LeaderboardEntry | None:
        if self.state != GameState.NAME_ENTRY:
            return None
        entry = self.record_run(self.name_input or "PILOT")
        self.state = GameState.LEADERBOARD
        return entry

    def skip_name_entry(self) -> None:
        if self.state == GameState.NAME_ENTRY:
            self.state = GameState.LEADERBOARD

    def save_score_and_end(self) -> None:
        if self.state != GameState.STAGE_CLEAR:
            return
        self.begin_name_entry()

    def show_leaderboard(self) -> None:
        self.state = GameState.LEADERBOARD

    def return_to_title(self) -> None:
        self.state = GameState.TITLE
        self.fresh_leaderboard_entry = None

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
