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

    @property
    def center_x(self) -> float:
        return (self.start_x + self.end_x) / 2.0

    @property
    def width(self) -> float:
        return self.end_x - self.start_x

    def contains(self, x: float) -> bool:
        return self.start_x <= x <= self.end_x


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
        rng: random.Random | None = None,
    ) -> "Terrain":
        rng = rng or random.Random()
        stage = max(1, stage)

        base_widths = (170.0, 135.0, 105.0, 78.0)
        shrink = min((stage - 1) * 5.0, 34.0)
        centers = tuple(
            width * fraction + rng.uniform(-width * 0.015, width * 0.015)
            for fraction in (0.125, 0.375, 0.625, 0.875)
        )
        pads: list[LandingPad] = []
        for multiplier, center, base_width in zip(
            range(2, 6), centers, base_widths
        ):
            pad_width = max(54.0, base_width - shrink)
            pad_y = rng.uniform(height * 0.76, height * 0.89)
            pads.append(
                LandingPad(
                    center - pad_width / 2.0,
                    center + pad_width / 2.0,
                    pad_y,
                    multiplier,
                )
            )

        x_values = {0.0, float(width)}
        x_values.update(float(x) for x in range(40, width, 40))
        for pad in pads:
            x_values.update((pad.start_x, pad.end_x))

        points: list[tuple[float, float]] = []
        current_y = rng.uniform(height * 0.78, height * 0.86)
        for x in sorted(x_values):
            pad = next((candidate for candidate in pads if candidate.contains(x)), None)
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
        return next((pad for pad in self.pads if pad.contains(x)), None)

    def polygon(self) -> Iterable[tuple[float, float]]:
        yield from self.points
        yield (float(self.width), float(self.height))
        yield (0.0, float(self.height))
