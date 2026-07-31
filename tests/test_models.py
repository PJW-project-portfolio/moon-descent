import unittest

from lunar_lander.models import Lander, LandingResult, normalized_angle
from lunar_lander.settings import GameSettings


class LanderPhysicsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = GameSettings()

    def test_gravity_increases_downward_velocity(self) -> None:
        lander = Lander(100.0, 100.0)
        lander.update(0.1, 0.0, False, 22.0, self.settings)
        self.assertGreater(lander.velocity_y, 0.0)
        self.assertEqual(lander.fuel, 100.0)

    def test_upright_thrust_reduces_downward_velocity_and_burns_fuel(self) -> None:
        lander = Lander(100.0, 100.0, velocity_y=20.0)
        lander.update(0.05, 0.0, True, 22.0, self.settings)
        self.assertLess(lander.velocity_y, 20.0)
        self.assertAlmostEqual(
            lander.fuel, 100.0 - self.settings.fuel_burn_per_second * 0.05
        )
        self.assertTrue(lander.thrusting)

    def test_empty_tank_disables_thrust(self) -> None:
        lander = Lander(100.0, 100.0, fuel=0.0)
        lander.update(0.05, 0.0, True, 22.0, self.settings)
        self.assertFalse(lander.thrusting)
        self.assertGreater(lander.velocity_y, 0.0)

    def test_last_drop_of_fuel_only_provides_proportional_impulse(self) -> None:
        # 연료가 프레임 도중 소진되면 추력은 남은 연료 비율만큼만 적용된다.
        # 그 부분 임펄스가 중력을 정확히 상쇄하도록 초기 연료를 역산한다:
        # thrust * (fuel / burn) == gravity * dt
        gravity, dt = 22.0, 0.05
        fuel = (
            gravity * dt * self.settings.fuel_burn_per_second
            / self.settings.thrust_acceleration
        )
        lander = Lander(100.0, 100.0, fuel=fuel)
        lander.update(dt, 0.0, True, gravity, self.settings)
        self.assertAlmostEqual(lander.fuel, 0.0)
        self.assertAlmostEqual(lander.velocity_y, 0.0, places=7)

    def test_horizontal_position_wraps_at_world_width(self) -> None:
        lander = Lander(
            self.settings.screen_width - 1.0,
            100.0,
            velocity_x=20.0,
        )
        lander.update(0.1, 0.0, False, 0.0, self.settings)
        self.assertGreater(lander.x, self.settings.screen_width)

        lander.x = self.settings.world_width - 1.0
        lander.update(0.1, 0.0, False, 0.0, self.settings)
        self.assertAlmostEqual(lander.x, 1.0)

    def test_large_frame_matches_repeated_small_steps(self) -> None:
        one_frame = Lander(100.0, 100.0, velocity_x=35.0)
        small_steps = Lander(100.0, 100.0, velocity_x=35.0)
        one_frame.update(0.1, -0.5, True, 22.0, self.settings)
        for _ in range(10):
            small_steps.update(0.01, -0.5, True, 22.0, self.settings)
        self.assertAlmostEqual(one_frame.x, small_steps.x, places=7)
        self.assertAlmostEqual(one_frame.y, small_steps.y, places=7)
        self.assertAlmostEqual(
            one_frame.velocity_x, small_steps.velocity_x, places=7
        )
        self.assertAlmostEqual(
            one_frame.velocity_y, small_steps.velocity_y, places=7
        )
        self.assertAlmostEqual(one_frame.fuel, small_steps.fuel, places=7)

    def test_rotation_is_normalized(self) -> None:
        self.assertEqual(normalized_angle(190.0), -170.0)
        self.assertEqual(normalized_angle(-190.0), 170.0)


class LandingEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = GameSettings()

    def test_safe_touchdown_on_pad(self) -> None:
        lander = Lander(
            x=100.0,
            y=500.0,
            velocity_x=10.0,
            velocity_y=25.0,
            angle=5.0,
        )
        result = lander.evaluate_landing(70.0, 130.0, self.settings)
        self.assertEqual(result, LandingResult.LANDED)

    def test_landing_fails_when_rendered_foot_extends_beyond_pad(self) -> None:
        lander = Lander(
            x=115.0,
            y=500.0,
            velocity_y=20.0,
            angle=0.0,
        )
        result = lander.evaluate_landing(70.0, 130.0, self.settings)
        self.assertEqual(result, LandingResult.CRASHED)

    def test_fast_or_tilted_touchdown_crashes(self) -> None:
        fast = Lander(100.0, 500.0, velocity_y=60.0)
        tilted = Lander(100.0, 500.0, velocity_y=20.0, angle=20.0)
        self.assertEqual(
            fast.evaluate_landing(70.0, 130.0, self.settings),
            LandingResult.CRASHED,
        )
        self.assertEqual(
            tilted.evaluate_landing(70.0, 130.0, self.settings),
            LandingResult.CRASHED,
        )

    def test_touchdown_off_pad_crashes(self) -> None:
        lander = Lander(100.0, 500.0, velocity_y=20.0)
        self.assertEqual(
            lander.evaluate_landing(None, None, self.settings),
            LandingResult.CRASHED,
        )

    def test_safe_touchdown_off_pad_on_flat_terrain_is_emergency_landing(
        self,
    ) -> None:
        lander = Lander(
            100.0,
            500.0,
            velocity_x=10.0,
            velocity_y=25.0,
            angle=5.0,
        )
        self.assertEqual(
            lander.evaluate_landing(
                None,
                None,
                self.settings,
                surface_span_px=8.0,
            ),
            LandingResult.EMERGENCY_LANDED,
        )

    def test_safe_touchdown_off_pad_on_steep_terrain_crashes(self) -> None:
        lander = Lander(100.0, 500.0, velocity_y=20.0)
        self.assertEqual(
            lander.evaluate_landing(
                None,
                None,
                self.settings,
                surface_span_px=8.1,
            ),
            LandingResult.CRASHED,
        )

    def test_fast_or_tilted_touchdown_off_pad_crashes(self) -> None:
        fast = Lander(100.0, 500.0, velocity_y=60.0)
        tilted = Lander(100.0, 500.0, velocity_y=20.0, angle=20.0)
        for lander in (fast, tilted):
            with self.subTest(lander=lander):
                self.assertEqual(
                    lander.evaluate_landing(
                        None,
                        None,
                        self.settings,
                        surface_span_px=0.0,
                    ),
                    LandingResult.CRASHED,
                )


if __name__ == "__main__":
    unittest.main()
