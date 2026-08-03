import random
import unittest

from lunar_lander.settings import GameSettings
from lunar_lander.terrain import Terrain, signed_wrapped_delta


def wrapped_distance(a: float, b: float, width: float) -> float:
    delta = abs((a % width) - (b % width))
    return min(delta, width - delta)


def generate_terrain(
    settings: GameSettings,
    seed: int,
    stage: int = 1,
    spawn_x: float | None = None,
) -> Terrain:
    return Terrain.generate(
        int(settings.world_width),
        settings.screen_height,
        stage=stage,
        spawn_x=(settings.screen_width / 2.0 if spawn_x is None else spawn_x),
        exclusion_radius=settings.pad_exclusion_radius,
        rng=random.Random(seed),
    )


class SignedWrappedDeltaTests(unittest.TestCase):
    def test_same_point_has_zero_delta(self) -> None:
        self.assertEqual(signed_wrapped_delta(123.0, 123.0, 6400.0), 0.0)

    def test_simple_left_and_right_deltas(self) -> None:
        self.assertEqual(signed_wrapped_delta(100.0, 350.0, 6400.0), 250.0)
        self.assertEqual(signed_wrapped_delta(350.0, 100.0, 6400.0), -250.0)

    def test_seam_uses_shortest_direction(self) -> None:
        self.assertEqual(signed_wrapped_delta(6300.0, 100.0, 6400.0), 200.0)
        self.assertEqual(signed_wrapped_delta(100.0, 6300.0, 6400.0), -200.0)

    def test_result_stays_in_half_open_width_range(self) -> None:
        width = 6400.0
        for from_x in (-12800.0, -1.0, 0.0, 3199.0, 6400.0, 13000.0):
            for to_x in (-9600.0, 0.0, 100.0, 3200.0, 6399.0, 19200.0):
                with self.subTest(from_x=from_x, to_x=to_x):
                    delta = signed_wrapped_delta(from_x, to_x, width)
                    self.assertGreaterEqual(delta, -width / 2.0)
                    self.assertLess(delta, width / 2.0)


class TerrainTests(unittest.TestCase):
    def test_generation_creates_four_flat_landing_pads(self) -> None:
        settings = GameSettings()
        terrain = generate_terrain(settings, seed=3)
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
        early = generate_terrain(settings, seed=8, stage=1)
        later = generate_terrain(settings, seed=8, stage=3)
        for early_pad, later_pad in zip(early.pads, later.pads):
            self.assertLess(later_pad.width, early_pad.width)

    def test_height_interpolation_stays_inside_world(self) -> None:
        settings = GameSettings()
        terrain = generate_terrain(settings, seed=5)
        for x in (0.0, 100.0, 1279.0, 1300.0, 6399.0, 6500.0):
            y = terrain.height_at(x)
            self.assertGreaterEqual(y, 0.0)
            self.assertLessEqual(y, 720.0)

    def test_wrapped_terrain_has_a_continuous_seam(self) -> None:
        settings = GameSettings()
        terrain = generate_terrain(settings, seed=6)
        self.assertEqual(terrain.points[0][1], terrain.points[-1][1])
        self.assertEqual(terrain.height_at(0.0), terrain.height_at(terrain.width))

    def test_all_pads_respect_spawn_exclusion_across_seeds_and_seams(self) -> None:
        settings = GameSettings()
        width = settings.world_width
        seam_spawns = (0.0, 50.0, width - 50.0, 1760.0)

        for spawn_x in seam_spawns:
            for seed in range(20):
                with self.subTest(spawn_x=spawn_x, seed=seed):
                    terrain = generate_terrain(
                        settings,
                        seed=seed,
                        spawn_x=spawn_x,
                    )
                    for pad in terrain.pads:
                        distance = wrapped_distance(
                            pad.center_x,
                            spawn_x,
                            width,
                        )
                        self.assertGreaterEqual(
                            distance,
                            settings.pad_exclusion_radius,
                        )
                        self.assertIs(terrain.pad_at(pad.center_x), pad)

    def test_multipliers_increase_with_wrapped_spawn_distance(self) -> None:
        settings = GameSettings()
        spawn_x = settings.screen_width / 2.0

        for seed in range(25):
            terrain = generate_terrain(settings, seed=seed)
            pads_by_multiplier = sorted(
                terrain.pads,
                key=lambda pad: pad.multiplier,
            )
            distances = [
                wrapped_distance(
                    pad.center_x,
                    spawn_x,
                    terrain.width,
                )
                for pad in pads_by_multiplier
            ]
            self.assertEqual(distances, sorted(distances))

    def test_distance_bonus_is_bounded_and_monotonic(self) -> None:
        settings = GameSettings()
        spawn_x = settings.screen_width / 2.0

        for seed in range(25):
            terrain = generate_terrain(settings, seed=seed)
            pads_by_distance = sorted(
                terrain.pads,
                key=lambda pad: wrapped_distance(
                    pad.center_x,
                    spawn_x,
                    terrain.width,
                ),
            )
            bonuses = [pad.distance_bonus for pad in pads_by_distance]
            self.assertEqual(bonuses, sorted(bonuses))
            for pad in pads_by_distance:
                distance = wrapped_distance(
                    pad.center_x,
                    spawn_x,
                    terrain.width,
                )
                self.assertGreaterEqual(pad.distance_bonus, 1.0)
                self.assertLessEqual(pad.distance_bonus, 1.5)
                self.assertAlmostEqual(
                    pad.distance_bonus,
                    1.0 + 0.5 * distance / (terrain.width / 2.0),
                )

    def test_pads_remain_ordered_and_separated_along_allowed_arc(self) -> None:
        settings = GameSettings()
        spawn_x = settings.screen_width / 2.0
        terrain = generate_terrain(settings, seed=19)
        arc_start = (spawn_x + settings.pad_exclusion_radius) % terrain.width
        offsets = [
            (pad.center_x - arc_start) % terrain.width
            for pad in terrain.pads
        ]
        self.assertEqual(offsets, sorted(offsets))
        for index in range(len(terrain.pads) - 1):
            required_gap = (
                terrain.pads[index].width
                + terrain.pads[index + 1].width
            ) / 2.0
            self.assertGreaterEqual(
                offsets[index + 1] - offsets[index],
                required_gap,
            )


if __name__ == "__main__":
    unittest.main()
