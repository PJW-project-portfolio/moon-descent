import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from lunar_lander.app import STAR_PARALLAX, star_field_width, star_screen_x
from lunar_lander.settings import GameSettings
from lunar_lander.stages import STAGES


def circular_gap(a: float, b: float, width: float) -> float:
    delta = abs(a - b) % width
    return min(delta, width - delta)


class StarParallaxTests(unittest.TestCase):
    def test_stars_do_not_jump_when_camera_wraps_at_seam(self) -> None:
        for stage in STAGES:
            width = float(stage.world_width_px)
            field = star_field_width(width)
            for star_x in (0.0, 17.0, field / 2.0, field - 1.0):
                with self.subTest(stage=stage.name, star_x=star_x):
                    # 착륙선이 x = width - 0.5 에서 0.5 로 넘어가는 순간의 카메라
                    before = star_screen_x(star_x, width - 0.5 - 640.0, width)
                    after = star_screen_x(star_x, 0.5 - 640.0, width)
                    self.assertAlmostEqual(
                        circular_gap(before, after, field),
                        1.0 * STAR_PARALLAX,
                        places=6,
                    )

    def test_stars_keep_the_parallax_rate(self) -> None:
        width = float(STAGES[0].world_width_px)
        self.assertAlmostEqual(
            star_screen_x(500.0, 0.0, width)
            - star_screen_x(500.0, 100.0, width),
            100.0 * STAR_PARALLAX,
        )

    def test_star_strip_covers_the_screen_in_every_stage(self) -> None:
        screen_width = GameSettings().screen_width
        for stage in STAGES:
            with self.subTest(stage=stage.name):
                self.assertGreaterEqual(
                    star_field_width(stage.world_width_px), screen_width
                )


if __name__ == "__main__":
    unittest.main()
