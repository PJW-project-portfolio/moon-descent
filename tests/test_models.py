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
        self.assertAlmostEqual(lander.fuel, 99.25)
        self.assertTrue(lander.thrusting)

    def test_empty_tank_disables_thrust(self) -> None:
        lander = Lander(100.0, 100.0, fuel=0.0)
        lander.update(0.05, 0.0, True, 22.0, self.settings)
        self.assertFalse(lander.thrusting)
        self.assertGreater(lander.velocity_y, 0.0)

    def test_last_drop_of_fuel_only_provides_proportional_impulse(self) -> None:
        lander = Lander(100.0, 100.0, fuel=0.15)
        lander.update(0.05, 0.0, True, 22.0, self.settings)
        self.assertAlmostEqual(lander.fuel, 0.0)
        self.assertAlmostEqual(lander.velocity_y, 0.62, places=7)

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


if __name__ == "__main__":
    unittest.main()
