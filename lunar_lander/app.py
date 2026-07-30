"""Pygame application and vector-style renderer."""

# 웹(pygbag) 런타임은 pygame.init() 전에 pygame.font 속성이 없어, 시그니처의
# pygame.font.Font 힌트가 import 시점에 평가되면 실패한다. 지연 평가로 전환.
from __future__ import annotations

from dataclasses import dataclass
import asyncio
import math
import random

import pygame

from .game_state import GameSession, GameState
from .settings import GameSettings
from .resources import resource_path


BLACK = (4, 7, 9)
PHOSPHOR = (180, 255, 202)
WHITE = (230, 245, 236)
AMBER = (255, 193, 92)
RED = (255, 92, 92)
DIM = (74, 110, 92)
GROUND_FILL = (8, 18, 16)


@dataclass
class Particle:
    x: float
    y: float
    velocity_x: float
    velocity_y: float
    life: float
    color: tuple[int, int, int]


class LunarLanderApp:
    def __init__(self, seed: int | None = None) -> None:
        pygame.init()
        pygame.display.set_caption("MOON DESCENT")
        self.settings = GameSettings()
        self.screen = pygame.display.set_mode(
            (self.settings.screen_width, self.settings.screen_height)
        )
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.Font(resource_path("assets/fonts/DejaVuSansMono.ttf"), 18)
        self.font_medium = pygame.font.Font(resource_path("assets/fonts/DejaVuSansMono-Bold.ttf"), 28)
        self.font_large = pygame.font.Font(resource_path("assets/fonts/DejaVuSansMono-Bold.ttf"), 64)
        self.session = GameSession.create(self.settings, seed)
        self.running = True
        self.particles: list[Particle] = []
        self.effect_rng = random.Random(seed)
        self.previous_state = self.session.state
        self.stars = [
            (
                self.effect_rng.randrange(self.settings.screen_width),
                self.effect_rng.randrange(int(self.settings.screen_height * 0.65)),
                self.effect_rng.choice((1, 1, 1, 2)),
            )
            for _ in range(115)
        ]

    def run(self) -> None:
        asyncio.run(self.run_async())

    async def run_async(self) -> None:
        while self.running:
            dt = self.clock.tick(self.settings.target_fps) / 1000.0
            self._handle_events()
            rotation, thrust = self._read_controls()
            self.session.update(dt, rotation, thrust)
            self._emit_effects(dt)
            self._update_particles(dt)
            self._draw()
            await asyncio.sleep(0)
        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif self.session.state == GameState.TITLE and event.key in (
                    pygame.K_RETURN,
                    pygame.K_SPACE,
                ):
                    self.session.new_game()
                elif event.key == pygame.K_p:
                    self.session.toggle_pause()
                elif event.key == pygame.K_r:
                    self.particles.clear()
                    self.session.restart()
                elif self.session.state in (
                    GameState.LANDED,
                    GameState.CRASHED,
                ) and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.session.advance_after_result()
                elif self.session.state == GameState.GAME_OVER and event.key in (
                    pygame.K_RETURN,
                    pygame.K_SPACE,
                ):
                    self.particles.clear()
                    self.session.new_game()

    def _read_controls(self) -> tuple[float, bool]:
        if self.session.state != GameState.PLAYING:
            return 0.0, False
        keys = pygame.key.get_pressed()
        rotation = float(keys[pygame.K_RIGHT]) - float(keys[pygame.K_LEFT])
        thrust = bool(keys[pygame.K_UP] or keys[pygame.K_SPACE])
        return rotation, thrust

    def _emit_effects(self, dt: float) -> None:
        lander = self.session.lander
        if lander is not None and lander.thrusting:
            radians = math.radians(lander.angle)
            origin_x = lander.x - math.sin(radians) * 15.0
            origin_y = lander.y + math.cos(radians) * 15.0
            for _ in range(2):
                speed = self.effect_rng.uniform(45.0, 90.0)
                spread = self.effect_rng.uniform(-0.22, 0.22)
                self.particles.append(
                    Particle(
                        origin_x,
                        origin_y,
                        -math.sin(radians + spread) * speed,
                        math.cos(radians + spread) * speed,
                        self.effect_rng.uniform(0.18, 0.38),
                        self.effect_rng.choice((AMBER, WHITE)),
                    )
                )

        if (
            self.previous_state == GameState.PLAYING
            and self.session.state in (GameState.CRASHED, GameState.GAME_OVER)
            and lander is not None
        ):
            for _ in range(45):
                angle = self.effect_rng.uniform(0.0, math.tau)
                speed = self.effect_rng.uniform(35.0, 155.0)
                self.particles.append(
                    Particle(
                        lander.x,
                        lander.y,
                        math.cos(angle) * speed,
                        math.sin(angle) * speed,
                        self.effect_rng.uniform(0.5, 1.25),
                        self.effect_rng.choice((RED, AMBER, WHITE)),
                    )
                )
        self.previous_state = self.session.state

    def _update_particles(self, dt: float) -> None:
        alive: list[Particle] = []
        for particle in self.particles:
            particle.life -= dt
            if particle.life <= 0.0:
                continue
            particle.x += particle.velocity_x * dt
            particle.y += particle.velocity_y * dt
            particle.velocity_y += 20.0 * dt
            alive.append(particle)
        self.particles = alive

    def _draw(self) -> None:
        self.screen.fill(BLACK)
        self._draw_stars()
        if self.session.state == GameState.TITLE:
            self._draw_title()
        else:
            self._draw_world()
            self._draw_hud()
            self._draw_overlay()
        pygame.display.flip()

    def _draw_stars(self) -> None:
        for x, y, radius in self.stars:
            pygame.draw.circle(self.screen, DIM, (x, y), radius)

    def _draw_title(self) -> None:
        self._center_text("MOON DESCENT", 150, self.font_large, PHOSPHOR)
        self._center_text(
            "VECTOR FLIGHT SIMULATION", 232, self.font_small, AMBER
        )
        controls = (
            "LEFT / RIGHT   ROTATE",
            "UP / SPACE     MAIN THRUSTER",
            "P              PAUSE",
            "R              RESTART",
            "ESC            QUIT",
        )
        for index, line in enumerate(controls):
            self._center_text(line, 320 + index * 32, self.font_small, WHITE)
        self._center_text(
            "PRESS ENTER OR SPACE TO LAUNCH",
            550,
            self.font_medium,
            PHOSPHOR,
        )
        self._center_text(
            "LAND UPRIGHT. LAND SLOW. CONSERVE FUEL.",
            610,
            self.font_small,
            DIM,
        )

    def _draw_world(self) -> None:
        terrain = self.session.terrain
        lander = self.session.lander
        if terrain is None or lander is None:
            return

        pygame.draw.polygon(self.screen, GROUND_FILL, list(terrain.polygon()))
        pygame.draw.lines(self.screen, PHOSPHOR, False, terrain.points, 2)
        for pad in terrain.pads:
            pygame.draw.line(
                self.screen,
                AMBER,
                (pad.start_x, pad.y),
                (pad.end_x, pad.y),
                5,
            )
            label = self.font_small.render(f"x{pad.multiplier}", True, AMBER)
            self.screen.blit(
                label,
                (pad.center_x - label.get_width() / 2, pad.y + 10),
            )

        if self.session.state not in (GameState.CRASHED, GameState.GAME_OVER):
            self._draw_lander(lander.x, lander.y, lander.angle)

        for particle in self.particles:
            radius = 2 if particle.life > 0.3 else 1
            pygame.draw.circle(
                self.screen,
                particle.color,
                (int(particle.x), int(particle.y)),
                radius,
            )

    def _draw_lander(self, x: float, y: float, angle: float) -> None:
        def rotate(point_x: float, point_y: float) -> tuple[int, int]:
            radians = math.radians(angle)
            rotated_x = point_x * math.cos(radians) - point_y * math.sin(radians)
            rotated_y = point_x * math.sin(radians) + point_y * math.cos(radians)
            return int(x + rotated_x), int(y + rotated_y)

        body = [rotate(-10, -10), rotate(10, -10), rotate(13, 8), rotate(-13, 8)]
        window = [rotate(-5, -7), rotate(5, -7), rotate(6, 0), rotate(-6, 0)]
        pygame.draw.lines(self.screen, WHITE, True, body, 2)
        pygame.draw.lines(self.screen, PHOSPHOR, True, window, 2)
        pygame.draw.line(self.screen, WHITE, rotate(-9, 7), rotate(-16, 18), 2)
        pygame.draw.line(self.screen, WHITE, rotate(9, 7), rotate(16, 18), 2)
        pygame.draw.line(self.screen, WHITE, rotate(-20, 18), rotate(-12, 18), 2)
        pygame.draw.line(self.screen, WHITE, rotate(12, 18), rotate(20, 18), 2)

    def _draw_hud(self) -> None:
        lander = self.session.lander
        if lander is None:
            return

        left_lines = (
            f"SCORE {self.session.score:06d}",
            f"HIGH  {self.session.high_score:06d}",
            f"STAGE {self.session.stage:02d}",
            f"LIVES {self.session.lives}",
        )
        ppm = self.settings.pixels_per_meter
        right_lines = (
            f"ALT  {self.session.altitude:06.1f}",
            f"H-S  {lander.velocity_x / ppm:+05.1f} M/S",
            f"V-S  {lander.velocity_y / ppm:+05.1f} M/S",
            f"FUEL {lander.fuel:06.1f}",
        )
        for index, text in enumerate(left_lines):
            self._text(text, 28, 24 + index * 25, self.font_small, WHITE)
        for index, text in enumerate(right_lines):
            surface = self.font_small.render(text, True, WHITE)
            self.screen.blit(
                surface,
                (
                    self.settings.screen_width - surface.get_width() - 28,
                    24 + index * 25,
                ),
            )

        warning_color = RED if lander.fuel < 20.0 else AMBER
        bar_x, bar_y, bar_width, bar_height = 28, 130, 210, 9
        pygame.draw.rect(
            self.screen, DIM, (bar_x, bar_y, bar_width, bar_height), 1
        )
        fill_width = int(bar_width * lander.fuel / self.settings.fuel_capacity)
        pygame.draw.rect(
            self.screen,
            warning_color,
            (bar_x, bar_y, fill_width, bar_height),
        )

    def _draw_overlay(self) -> None:
        state = self.session.state
        if state == GameState.PAUSED:
            self._panel_message("PAUSED", "PRESS P TO RESUME", PHOSPHOR)
        elif state == GameState.LANDED:
            self._panel_message(
                "TOUCHDOWN",
                f"+{self.session.last_award} POINTS",
                PHOSPHOR,
            )
        elif state == GameState.CRASHED:
            self._panel_message("MODULE DESTROYED", "RETRYING...", RED)
        elif state == GameState.GAME_OVER:
            self._panel_message(
                "MISSION ENDED",
                f"FINAL {self.session.final_score:06d} - ENTER TO RETRY",
                RED,
            )

    def _panel_message(
        self,
        title: str,
        subtitle: str,
        color: tuple[int, int, int],
    ) -> None:
        panel = pygame.Surface((600, 150), pygame.SRCALPHA)
        panel.fill((0, 8, 6, 220))
        pygame.draw.rect(panel, color, panel.get_rect(), 2)
        self.screen.blit(
            panel,
            (
                self.settings.screen_width / 2 - panel.get_width() / 2,
                self.settings.screen_height / 2 - panel.get_height() / 2,
            ),
        )
        self._center_text(
            title,
            self.settings.screen_height / 2 - 48,
            self.font_medium,
            color,
        )
        self._center_text(
            subtitle,
            self.settings.screen_height / 2 + 15,
            self.font_small,
            WHITE,
        )

    def _text(
        self,
        text: str,
        x: float,
        y: float,
        font: pygame.font.Font,
        color: tuple[int, int, int],
    ) -> None:
        self.screen.blit(font.render(text, True, color), (x, y))

    def _center_text(
        self,
        text: str,
        y: float,
        font: pygame.font.Font,
        color: tuple[int, int, int],
    ) -> None:
        surface = font.render(text, True, color)
        self.screen.blit(
            surface,
            (self.settings.screen_width / 2 - surface.get_width() / 2, y),
        )
