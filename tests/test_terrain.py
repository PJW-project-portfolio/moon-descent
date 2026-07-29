import random
import unittest

from lunar_lander.terrain import Terrain


class TerrainTests(unittest.TestCase):
    def test_generation_creates_three_flat_landing_pads(self) -> None:
        terrain = Terrain.generate(1280, 720, stage=1, rng=random.Random(3))
        self.assertEqual(len(terrain.pads), 3)
        self.assertEqual([pad.multiplier for pad in terrain.pads], [1, 2, 3])
        for pad in terrain.pads:
            self.assertAlmostEqual(terrain.height_at(pad.center_x), pad.y)
            self.assertIs(terrain.pad_at(pad.center_x), pad)

    def test_landing_pads_shrink_at_higher_stages(self) -> None:
        early = Terrain.generate(1280, 720, stage=1, rng=random.Random(8))
        later = Terrain.generate(1280, 720, stage=8, rng=random.Random(8))
        for early_pad, later_pad in zip(early.pads, later.pads):
            self.assertLess(later_pad.width, early_pad.width)

    def test_height_interpolation_stays_inside_world(self) -> None:
        terrain = Terrain.generate(1280, 720, stage=1, rng=random.Random(5))
        for x in (0.0, 100.0, 640.0, 1279.0, 1300.0):
            y = terrain.height_at(x)
            self.assertGreaterEqual(y, 0.0)
            self.assertLessEqual(y, 720.0)


if __name__ == "__main__":
    unittest.main()
