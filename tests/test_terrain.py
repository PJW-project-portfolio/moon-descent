import random
import unittest

from lunar_lander.settings import GameSettings
from lunar_lander.terrain import Terrain


class TerrainTests(unittest.TestCase):
    def test_generation_creates_four_flat_landing_pads(self) -> None:
        settings = GameSettings()
        terrain = Terrain.generate(
            int(settings.world_width),
            settings.screen_height,
            stage=1,
            rng=random.Random(3),
        )
        self.assertEqual(
            terrain.width,
            settings.screen_width * settings.map_screens,
        )
        self.assertEqual(len(terrain.pads), 4)
        self.assertEqual(
            {pad.multiplier for pad in terrain.pads},
            {2, 3, 4, 5},
        )
        self.assertEqual(
            sorted(terrain.pads, key=lambda pad: pad.width, reverse=True),
            sorted(terrain.pads, key=lambda pad: pad.multiplier),
        )
        for pad in terrain.pads:
            self.assertAlmostEqual(terrain.height_at(pad.center_x), pad.y)
            self.assertIs(terrain.pad_at(pad.center_x), pad)

    def test_landing_pads_shrink_at_higher_stages(self) -> None:
        settings = GameSettings()
        width = int(settings.world_width)
        early = Terrain.generate(width, 720, stage=1, rng=random.Random(8))
        later = Terrain.generate(width, 720, stage=3, rng=random.Random(8))
        for early_pad, later_pad in zip(early.pads, later.pads):
            self.assertLess(later_pad.width, early_pad.width)

    def test_height_interpolation_stays_inside_world(self) -> None:
        settings = GameSettings()
        terrain = Terrain.generate(
            int(settings.world_width),
            720,
            stage=1,
            rng=random.Random(5),
        )
        for x in (0.0, 100.0, 1279.0, 1300.0, 6399.0, 6500.0):
            y = terrain.height_at(x)
            self.assertGreaterEqual(y, 0.0)
            self.assertLessEqual(y, 720.0)

    def test_wrapped_terrain_has_a_continuous_seam(self) -> None:
        settings = GameSettings()
        terrain = Terrain.generate(
            int(settings.world_width),
            720,
            stage=1,
            rng=random.Random(6),
        )
        self.assertEqual(terrain.points[0][1], terrain.points[-1][1])
        self.assertEqual(terrain.height_at(0.0), terrain.height_at(terrain.width))


if __name__ == "__main__":
    unittest.main()
