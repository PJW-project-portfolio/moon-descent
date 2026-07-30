import unittest

from lunar_lander.stages import STAGES


class StageDefinitionTests(unittest.TestCase):
    def test_stage_order_and_surface_gravity(self) -> None:
        self.assertEqual(len(STAGES), 5)
        self.assertEqual(
            [stage.name for stage in STAGES],
            ["MOON", "MARS", "VENUS", "EUROPA", "TITAN"],
        )
        self.assertEqual(
            [stage.gravity_ms2 for stage in STAGES],
            [1.62, 3.71, 8.87, 1.31, 1.35],
        )

        self.assertEqual(
            [stage.par_time_seconds for stage in STAGES],
            [45.0, 50.0, 60.0, 45.0, 45.0],
        )


if __name__ == "__main__":
    unittest.main()
