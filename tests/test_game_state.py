from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from lunar_lander.game_state import (
    GameSession,
    GameState,
    calculate_time_bonus,
)
from lunar_lander.models import Lander
from lunar_lander.stages import STAGES
from lunar_lander.terrain import Terrain


class GameSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        path_patch = patch(
            "lunar_lander.leaderboard.LEADERBOARD_PATH",
            Path(temporary_directory.name) / "leaderboard.json",
        )
        path_patch.start()
        self.addCleanup(path_patch.stop)

    def test_new_game_and_pause_flow(self) -> None:
        session = GameSession.create(seed=1)
        session.new_game()
        self.assertEqual(session.state, GameState.PLAYING)
        self.assertEqual(session.stage, 1)
        self.assertEqual(session.lives, 3)
        self.assertEqual(session.final_score, 0)
        self.assertIsNotNone(session.terrain)
        self.assertIsNotNone(session.lander)
        self.assertEqual(session.current_stage, STAGES[0])
        self.assertEqual(session.terrain.width, session.settings.world_width)
        session.toggle_pause()
        self.assertEqual(session.state, GameState.PAUSED)
        session.toggle_pause()
        self.assertEqual(session.state, GameState.PLAYING)

    def test_safe_landing_awards_score_and_advances_stage(self) -> None:
        session = GameSession.create(seed=2)
        session.new_game()
        assert session.terrain is not None
        assert session.lander is not None
        pad = session.terrain.pads[1]
        session.lander.x = pad.center_x
        session.lander.y = pad.y - session.settings.lander_bottom_offset - 0.1
        session.lander.velocity_x = 0.0
        session.lander.velocity_y = 10.0
        session.lander.angle = 0.0
        session.update(0.01)
        self.assertEqual(session.state, GameState.STAGE_CLEAR)
        self.assertEqual(session.lives, 3)
        gear_heights = [
            point_y for _, point_y in session.lander.landing_gear_points()
        ]
        self.assertTrue(all(abs(y - pad.y) < 1e-7 for y in gear_heights))
        self.assertGreater(session.score, 0)
        expected_fuel = session.settings.fuel_capacity + session.last_fuel_bonus
        session.advance_after_result()
        self.assertEqual(session.state, GameState.PLAYING)
        self.assertEqual(session.stage, 2)
        assert session.lander is not None
        self.assertEqual(session.stage_start_fuel, expected_fuel)
        self.assertEqual(session.lander.fuel, expected_fuel)
        self.assertEqual(session.lander.velocity_x, 0.0)
        self.assertEqual(session.lander.velocity_y, 0.0)

    def test_retry_keeps_stage_and_terrain_and_refills_fuel(self) -> None:
        session = GameSession.create(seed=4)
        session.new_game()
        assert session.terrain is not None
        assert session.lander is not None
        original_terrain = session.terrain
        pad = session.terrain.pads[0]
        session.lander.x = pad.center_x
        session.lander.y = (
            pad.y
            - session.settings.lander_bottom_offset
            - 0.1
        )
        session.lander.velocity_y = 70.0
        session.lander.fuel = 0.0
        session.update(0.01)
        self.assertEqual(session.state, GameState.CRASHED)
        self.assertEqual(session.lives, 2)
        self.assertGreater(session.stage_elapsed, 0.0)
        session.advance_after_result()
        self.assertEqual(session.state, GameState.PLAYING)
        self.assertEqual(session.stage_elapsed, 0.0)
        self.assertEqual(session.stage, 1)
        self.assertIs(session.terrain, original_terrain)
        assert session.lander is not None
        self.assertEqual(session.lander.fuel, session.settings.fuel_capacity)
        self.assertEqual(session.lander.velocity_x, 0.0)
        self.assertEqual(session.lander.velocity_y, 0.0)

    def test_every_round_starts_stationary(self) -> None:
        for seed in range(20):
            session = GameSession.create(seed=seed)
            session.new_game()
            assert session.lander is not None
            self.assertEqual(session.lander.velocity_x, 0.0)
            self.assertEqual(session.lander.velocity_y, 0.0)

    def test_later_stage_retry_restores_that_stages_starting_fuel(self) -> None:
        session = GameSession.create(seed=12)
        session.new_game()
        assert session.terrain is not None
        assert session.lander is not None
        pad = session.terrain.pads[1]
        session.lander.x = pad.center_x
        session.lander.y = pad.y - session.settings.lander_bottom_offset - 0.1
        session.lander.velocity_x = 0.0
        session.lander.velocity_y = 10.0
        session.lander.angle = 0.0
        session.lander.fuel = 40.0
        session.update(0.01)
        session.advance_after_result()

        self.assertEqual(session.stage, 2)
        expected_start_fuel = session.settings.fuel_capacity + session.last_fuel_bonus
        self.assertEqual(session.stage_start_fuel, expected_start_fuel)
        assert session.lander is not None
        session.lander.fuel = 3.0
        session.state = GameState.CRASHED
        session.advance_after_result()
        self.assertEqual(session.lander.fuel, expected_start_fuel)
        self.assertEqual(session.lander.velocity_x, 0.0)
        self.assertEqual(session.lander.velocity_y, 0.0)

    def test_third_crash_records_final_score_and_ends_game(self) -> None:
        session = GameSession.create(seed=15)
        session.new_game()
        session.score = 321

        def crash_current_lander() -> None:
            assert session.terrain is not None
            assert session.lander is not None
            pad = session.terrain.pads[0]
            session.lander.x = pad.center_x
            session.lander.y = (
                pad.y - session.settings.lander_bottom_offset - 0.1
            )
            session.lander.velocity_x = 0.0
            session.lander.velocity_y = 80.0
            session.lander.angle = 0.0
            session.update(0.01)

        crash_current_lander()
        self.assertEqual(session.state, GameState.CRASHED)
        self.assertEqual(session.lives, 2)
        session.advance_after_result()
        crash_current_lander()
        self.assertEqual(session.state, GameState.CRASHED)
        self.assertEqual(session.lives, 1)
        session.advance_after_result()
        crash_current_lander()

        self.assertEqual(session.state, GameState.GAME_OVER)
        self.assertEqual(session.lives, 0)
        self.assertEqual(session.final_score, 321)
        self.assertEqual(session.high_score, 321)
        self.assertEqual(len(session.leaderboard.entries), 1)
        self.assertEqual(session.leaderboard.entries[0]["score"], 321)
        self.assertEqual(
            session.leaderboard.entries[0]["body"], "MOON"
        )
        session.new_game()
        self.assertEqual(session.lives, 3)
        self.assertEqual(session.score, 0)
        self.assertEqual(session.final_score, 0)
        self.assertEqual(session.high_score, 321)

    def test_collision_is_detected_inside_a_long_frame(self) -> None:
        session = GameSession.create(seed=9)
        session.new_game()
        session.terrain = Terrain(
            width=1280,
            height=720,
            points=[
                (0.0, 600.0),
                (130.0, 600.0),
                (145.0, 400.0),
                (155.0, 400.0),
                (170.0, 600.0),
                (1280.0, 600.0),
            ],
            pads=[],
        )
        session.lander = Lander(
            x=100.0,
            y=383.0,
            velocity_x=1000.0,
            velocity_y=0.0,
            fuel=session.settings.fuel_capacity,
        )
        session.update(0.1)
        self.assertEqual(session.state, GameState.CRASHED)
        self.assertLess(session.lander.x, 200.0)

    def test_moon_and_venus_gravity_drive_physics_in_pixels(self) -> None:
        session = GameSession.create(seed=7)
        session.new_game()
        assert session.lander is not None
        ppm = session.settings.pixels_per_meter

        self.assertEqual(session.gravity, STAGES[0].gravity_ms2 * ppm)
        session.update(0.1)
        self.assertAlmostEqual(
            session.lander.velocity_y,
            STAGES[0].gravity_ms2 * ppm * 0.1,
        )

        session.stage = 3
        session._spawn_lander(session.settings.fuel_capacity)
        self.assertEqual(session.gravity, STAGES[2].gravity_ms2 * ppm)
        session.update(0.1)
        self.assertAlmostEqual(
            session.lander.velocity_y,
            STAGES[2].gravity_ms2 * ppm * 0.1,
        )

    def test_stage_fuel_burn_rate_overrides_settings_fallback(self) -> None:
        session = GameSession.create(seed=10)
        session.new_game()
        session.stage = 2
        session._spawn_lander(session.settings.fuel_capacity)
        assert session.lander is not None
        session.update(0.1, thrust_requested=True)
        self.assertAlmostEqual(
            session.lander.fuel,
            session.settings.fuel_capacity
            - STAGES[1].fuel_burn_per_second * 0.1,
        )

    def test_stage_clear_can_save_score_and_end(self) -> None:
        session = GameSession.create(seed=14)
        session.new_game()
        session.stage = 3
        session.state = GameState.STAGE_CLEAR
        session.score = 512
        session.save_score_and_end()

        self.assertEqual(session.state, GameState.LEADERBOARD)
        self.assertEqual(len(session.leaderboard.entries), 1)
        self.assertEqual(session.leaderboard.entries[0]["score"], 512)
        self.assertEqual(session.leaderboard.entries[0]["body"], "VENUS")

    def test_venus_landing_enters_victory_and_records_score(self) -> None:
        session = GameSession.create(seed=11)
        session.new_game()
        session.stage = len(STAGES)
        session._prepare_round(session.settings.fuel_capacity)
        assert session.terrain is not None
        assert session.lander is not None
        pad = session.terrain.pads[1]
        session.score = 700
        session.lander.x = pad.center_x
        session.lander.y = (
            pad.y - session.settings.lander_bottom_offset - 0.1
        )
        session.lander.velocity_x = 0.0
        session.lander.velocity_y = 10.0
        session.lander.angle = 0.0
        session.update(0.01)

        self.assertEqual(session.stage, len(STAGES))
        self.assertEqual(session.current_stage, STAGES[-1])
        self.assertEqual(session.state, GameState.VICTORY)
        self.assertEqual(session.final_score, session.score)
        self.assertEqual(len(session.leaderboard.entries), 1)
        self.assertEqual(
            session.leaderboard.entries[0]["body"], "VENUS"
        )

    def test_time_bonus_under_par(self) -> None:
        self.assertAlmostEqual(calculate_time_bonus(45.0, 30.0), 9.0)

    def test_time_bonus_over_par_is_zero(self) -> None:
        self.assertEqual(calculate_time_bonus(45.0, 50.0), 0.0)

    def test_time_bonus_is_capped(self) -> None:
        self.assertEqual(calculate_time_bonus(100.0, 0.0), 30.0)

    def test_stage_intro_uses_transition_duration_on_stage_entry(self) -> None:
        session = GameSession.create(seed=13)
        session.new_game()
        self.assertTrue(session.stage_intro_active)

        session.stage_intro_elapsed = session.settings.round_transition_seconds
        self.assertFalse(session.stage_intro_active)

        assert session.lander is not None
        session.state = GameState.STAGE_CLEAR
        session.advance_after_result()
        self.assertTrue(session.stage_intro_active)


if __name__ == "__main__":
    unittest.main()
