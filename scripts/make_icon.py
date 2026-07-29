"""Generate the Moon Descent application icon."""

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


SIZE = 512
BLACK = (4, 7, 9)
PHOSPHOR = (180, 255, 202)
WHITE = (230, 245, 236)
AMBER = (255, 193, 92)
DIM = (74, 110, 92)
SCALE = 11
CENTER = (256, 240)
STARS = (
    (74, 82, 3),
    (136, 142, 4),
    (207, 70, 3),
    (281, 104, 5),
    (361, 68, 3),
    (437, 128, 4),
    (91, 210, 4),
    (421, 224, 3),
)


def scaled(point: tuple[int, int]) -> tuple[int, int]:
    return CENTER[0] + point[0] * SCALE, CENTER[1] + point[1] * SCALE


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)
    Path("assets").mkdir(exist_ok=True)

    pygame.init()
    pygame.display.set_mode((1, 1))
    surface = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)

    plate = pygame.Rect(16, 16, 480, 480)
    pygame.draw.rect(surface, BLACK, plate, border_radius=90)
    pygame.draw.rect(surface, PHOSPHOR, plate, width=6, border_radius=90)
    for x, y, radius in STARS:
        pygame.draw.circle(surface, DIM, (x, y), radius)

    flame = [(216, 328), (296, 328), (256, 418)]
    pygame.draw.polygon(surface, AMBER, flame)

    body = [scaled((-10, -10)), scaled((10, -10)), scaled((13, 8)), scaled((-13, 8))]
    window = [scaled((-5, -7)), scaled((5, -7)), scaled((6, 0)), scaled((-6, 0))]
    pygame.draw.lines(surface, WHITE, True, body, 16)
    pygame.draw.lines(surface, PHOSPHOR, True, window, 12)
    pygame.draw.line(surface, WHITE, scaled((-9, 7)), scaled((-16, 18)), 16)
    pygame.draw.line(surface, WHITE, scaled((9, 7)), scaled((16, 18)), 16)
    pygame.draw.line(surface, WHITE, scaled((-20, 18)), scaled((-12, 18)), 16)
    pygame.draw.line(surface, WHITE, scaled((12, 18)), scaled((20, 18)), 16)

    output_path = Path("assets/icon.png")
    pygame.image.save(surface, str(output_path))
    print(f"Saved {project_root / output_path} ({surface.get_size()})")
    pygame.quit()


if __name__ == "__main__":
    main()
