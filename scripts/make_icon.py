"""Generate the Moon Descent application icon."""

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


SIZE = 512
PHOSPHOR = (180, 255, 202)
WHITE = (230, 245, 236)
AMBER = (255, 193, 92)
SCALE = 12
CENTER = (256, 208)


def scaled(point: tuple[float, float]) -> tuple[int, int]:
    return (
        round(CENTER[0] + point[0] * SCALE),
        round(CENTER[1] + point[1] * SCALE),
    )


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)
    Path("assets").mkdir(exist_ok=True)

    pygame.init()
    pygame.display.set_mode((1, 1))
    surface = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))

    flame = [scaled((-7, 8)), scaled((7, 8)), scaled((0, 17.5))]
    pygame.draw.polygon(surface, AMBER, flame)

    body = [scaled((-10, -10)), scaled((10, -10)), scaled((13, 8)), scaled((-13, 8))]
    window = [scaled((-5, -7)), scaled((5, -7)), scaled((6, 0)), scaled((-6, 0))]
    pygame.draw.lines(surface, WHITE, True, body, 22)
    pygame.draw.lines(surface, PHOSPHOR, True, window, 16)
    pygame.draw.line(surface, WHITE, scaled((-9, 7)), scaled((-16, 18)), 22)
    pygame.draw.line(surface, WHITE, scaled((9, 7)), scaled((16, 18)), 22)
    pygame.draw.line(surface, WHITE, scaled((-20, 18)), scaled((-12, 18)), 22)
    pygame.draw.line(surface, WHITE, scaled((12, 18)), scaled((20, 18)), 22)

    output_path = Path("assets/icon.png")
    pygame.image.save(surface, str(output_path))
    print(f"Saved {project_root / output_path} ({surface.get_size()})")
    pygame.quit()


if __name__ == "__main__":
    main()
