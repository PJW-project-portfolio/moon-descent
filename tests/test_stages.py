import unittest

from lunar_lander.stages import STAGES


class StageDefinitionTests(unittest.TestCase):
    def test_stage_order_and_surface_gravity(self) -> None:
        self.assertEqual(len(STAGES), 3)
        self.assertEqual(
            [stage.name for stage in STAGES],
            ["MOON", "MARS", "VENUS"],
        )
        self.assertEqual(
            [stage.gravity_ms2 for stage in STAGES],
            [1.62, 3.71, 8.87],
        )

        self.assertEqual(
            [stage.entry_speed_ms for stage in STAGES],
            [5.0, 7.0, 8.0],
        )
        self.assertEqual(
            [stage.par_time_seconds for stage in STAGES],
            [45.0, 50.0, 60.0],
        )

    def test_stage_background_palettes_are_distinct(self) -> None:
        self.assertEqual(len({stage.sky for stage in STAGES}), 3)
        self.assertEqual(STAGES[-1].name, "VENUS")
        self.assertEqual(STAGES[-1].star_count, 0)


if __name__ == "__main__":
    unittest.main()
