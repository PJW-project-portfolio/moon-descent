import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from lunar_lander.app import AMBER, WHITE, sky_color_at
from lunar_lander.settings import GameSettings
from lunar_lander.stages import STAGES


def relative_luminance(color: tuple[int, int, int]) -> float:
    def linear(channel: int) -> float:
        value = channel / 255.0
        if value <= 0.04045:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(channel) for channel in color)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    brighter, darker = sorted(
        (relative_luminance(a), relative_luminance(b)), reverse=True
    )
    return (brighter + 0.05) / (darker + 0.05)


class SkyTests(unittest.TestCase):
    def test_flat_sky_is_the_same_on_every_row(self) -> None:
        moon = STAGES[0]
        for y in (0, 360, 719):
            self.assertEqual(sky_color_at(moon, y, 720), moon.sky)

    def test_gradient_runs_from_zenith_to_horizon(self) -> None:
        mars = STAGES[1]
        self.assertEqual(sky_color_at(mars, 0, 720), mars.sky)
        self.assertEqual(sky_color_at(mars, 719, 720), mars.sky_horizon)
        rows = [sum(sky_color_at(mars, y, 720)) for y in range(720)]
        self.assertEqual(rows, sorted(rows))

    def test_hud_stays_readable_on_every_sky(self) -> None:
        height = GameSettings().screen_height
        for stage in STAGES:
            with self.subTest(stage=stage.name):
                # HUD 글자(흰색 y<160, 호박색 패드 방향 표시 y<280): WCAG AA 4.5:1
                for y in range(280):
                    sky = sky_color_at(stage, y, height)
                    self.assertGreaterEqual(contrast_ratio(AMBER, sky), 4.5)
                    if y < 160:
                        self.assertGreaterEqual(contrast_ratio(WHITE, sky), 4.5)
                # 착륙선 흰 선은 화면 어디서든: 그래픽 요소 기준 3:1
                for y in range(height):
                    sky = sky_color_at(stage, y, height)
                    self.assertGreaterEqual(contrast_ratio(WHITE, sky), 3.0)


if __name__ == "__main__":
    unittest.main()
