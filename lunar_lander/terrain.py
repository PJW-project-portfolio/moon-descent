"""Procedural terrain and landing pads."""

from dataclasses import dataclass
import bisect
import random
from typing import Iterable


@dataclass(frozen=True)
class LandingPad:
    start_x: float
    end_x: float
    y: float
    multiplier: int
    distance_bonus: float = 1.0

    @property
    def center_x(self) -> float:
        return (self.start_x + self.end_x) / 2.0

    @property
    def width(self) -> float:
        return self.end_x - self.start_x

    def contains(self, x: float) -> bool:
        return self.start_x <= x <= self.end_x

    def contains_wrapped(self, x: float, world_width: float) -> bool:
        x %= world_width
        return any(
            self.contains(candidate)
            for candidate in (x - world_width, x, x + world_width)
        )

    def bounds_near(
        self, x: float, world_width: float
    ) -> tuple[float, float]:
        shift = round((x - self.center_x) / world_width) * world_width
        return self.start_x + shift, self.end_x + shift


def signed_wrapped_delta(from_x: float, to_x: float, width: float) -> float:
    """Return the shortest signed offset to ``to_x`` on a wrapped strip."""
    return (to_x - from_x + width / 2.0) % width - width / 2.0


def wrapped_distance(a: float, b: float, width: float) -> float:
    """Return the shortest distance between two points on a wrapped strip."""
    return abs(signed_wrapped_delta(a, b, width))


@dataclass
class Terrain:
    width: int
    height: int
    points: list[tuple[float, float]]
    pads: list[LandingPad]

    @classmethod
    def generate(
        cls,
        width: int,
        height: int,
        stage: int,
        spawn_x: float,
        exclusion_radius: float,
        rng: random.Random | None = None,
    ) -> "Terrain":
        rng = rng or random.Random()
        stage = max(1, stage)

        base_widths = (170.0, 135.0, 105.0, 78.0)
        shrink = min((stage - 1) * 5.0, 34.0)
        allowed_length = width - 2.0 * exclusion_radius
        minimum_separation = max(base_widths)
        if allowed_length < minimum_separation * len(base_widths):
            raise ValueError("pad exclusion radius leaves too little placement space")

        arc_start = (spawn_x + exclusion_radius) % width
        jitter = width * 0.015
        arc_offsets: list[float] = []
        for index, fraction in enumerate((0.125, 0.375, 0.625, 0.875)):
            offset = allowed_length * fraction + rng.uniform(-jitter, jitter)
            minimum_offset = (
                minimum_separation / 2.0 + index * minimum_separation
            )
            maximum_offset = (
                allowed_length
                - minimum_separation / 2.0
                - (len(base_widths) - index - 1) * minimum_separation
            )
            offset = min(maximum_offset, max(minimum_offset, offset))
            if arc_offsets:
                offset = max(offset, arc_offsets[-1] + minimum_separation)
            arc_offsets.append(offset)

        centers = [
            (arc_start + offset) % width for offset in arc_offsets
        ]
        centers_by_distance = sorted(
            centers,
            key=lambda center: wrapped_distance(center, spawn_x, width),
        )
        multiplier_by_center = {
            center: multiplier
            for multiplier, center in enumerate(centers_by_distance, start=2)
        }

        pads: list[LandingPad] = []
        for center in centers:
            multiplier = multiplier_by_center[center]
            base_width = base_widths[multiplier - 2]
            pad_width = max(54.0, base_width - shrink)
            pad_y = rng.uniform(height * 0.76, height * 0.89)
            distance = wrapped_distance(center, spawn_x, width)
            pads.append(
                LandingPad(
                    center - pad_width / 2.0,
                    center + pad_width / 2.0,
                    pad_y,
                    multiplier,
                    1.0 + 0.5 * distance / (width / 2.0),
                )
            )

        x_values = {0.0, float(width)}
        x_values.update(float(x) for x in range(40, width, 40))
        for pad in pads:
            x_values.update(
                (pad.start_x % width, pad.end_x % width)
            )

        points: list[tuple[float, float]] = []
        current_y = rng.uniform(height * 0.78, height * 0.86)
        for x in sorted(x_values):
            pad = next(
                (
                    candidate
                    for candidate in pads
                    if candidate.contains_wrapped(x, width)
                ),
                None,
            )
            if pad is not None:
                y = pad.y
            else:
                current_y += rng.uniform(-46.0, 46.0)
                current_y = min(height * 0.92, max(height * 0.68, current_y))
                y = current_y
            points.append((x, y))

        # The strip is a loop, so its two endpoints must meet without a seam.
        points[-1] = (float(width), points[0][1])
        return cls(width=width, height=height, points=points, pads=pads)

    @property
    def x_coordinates(self) -> list[float]:
        return [point[0] for point in self.points]

    def height_at(self, x: float) -> float:
        """Linearly interpolate terrain height at a wrapped x coordinate."""
        x %= self.width
        xs = self.x_coordinates
        right_index = bisect.bisect_right(xs, x)
        if right_index == 0:
            return self.points[0][1]
        if right_index >= len(self.points):
            return self.points[-1][1]

        x1, y1 = self.points[right_index - 1]
        x2, y2 = self.points[right_index]
        if x2 == x1:
            return y1
        ratio = (x - x1) / (x2 - x1)
        return y1 + (y2 - y1) * ratio

    def pad_at(self, x: float) -> LandingPad | None:
        x %= self.width
        return next(
            (
                pad
                for pad in self.pads
                if pad.contains_wrapped(x, self.width)
            ),
            None,
        )

    def polygon(self) -> Iterable[tuple[float, float]]:
        yield from self.points
        yield (float(self.width), float(self.height))
        yield (0.0, float(self.height))
