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
        self.assertEqual(
            [stage.world_width_px for stage in STAGES],
            [6400, 6000, 5600],
        )

    def test_stage_background_palettes_are_distinct(self) -> None:
        self.assertEqual(len({stage.sky for stage in STAGES}), 3)
        self.assertEqual(STAGES[-1].name, "VENUS")
        self.assertEqual(STAGES[-1].star_count, 0)

    def test_only_the_airless_moon_shows_stars(self) -> None:
        moon, mars, venus = STAGES
        self.assertGreater(moon.star_count, 0)
        # 화성은 낮 하늘(먼지 산란), 금성은 두꺼운 구름층이라 별이 보이지 않는다.
        self.assertEqual(mars.star_count, 0)
        self.assertEqual(venus.star_count, 0)

    def test_sky_effects_are_configured_per_stage(self) -> None:
        moon, mars, venus = STAGES
        self.assertIsNone(moon.sky_horizon)
        self.assertIsNone(moon.haze_color)
        self.assertIsNotNone(mars.sky_horizon)
        self.assertIsNone(mars.haze_color)
        self.assertIsNone(venus.sky_horizon)
        self.assertIsNotNone(venus.haze_color)


if __name__ == "__main__":
    unittest.main()
