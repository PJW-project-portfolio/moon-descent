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
from .models import LandingResult
from .settings import GameSettings
from .resources import resource_path
from .stages import STAGES, StageConfig


PHOSPHOR = (180, 255, 202)
WHITE = (230, 245, 236)
AMBER = (255, 193, 92)
RED = (255, 92, 92)
DIM = (74, 110, 92)


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
        self.star_stage: StageConfig | None = None
        self.stars: list[tuple[int, int, int]] = []
        self._regenerate_stars(STAGES[0])

    def _regenerate_stars(self, stage: StageConfig) -> None:
        self.stars = [
            (
                self.effect_rng.randrange(self.settings.screen_width),
                self.effect_rng.randrange(int(self.settings.screen_height * 0.65)),
                self.effect_rng.choice((1, 1, 1, 2)),
            )
            for _ in range(stage.star_count)
        ]
        self.star_stage = stage

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
                    if self.session.state == GameState.LEADERBOARD:
                        self.session.return_to_title()
                    elif self.session.state == GameState.NAME_ENTRY:
                        self.session.skip_name_entry()
                    else:
                        self.running = False
                elif self.session.state == GameState.NAME_ENTRY:
                    if event.key == pygame.K_RETURN:
                        self.session.confirm_name_entry()
                    elif event.key == pygame.K_BACKSPACE:
                        self.session.edit_name("\b")
                    else:
                        self.session.edit_name(getattr(event, "unicode", ""))
                elif event.key == pygame.K_r:
                    self.particles.clear()
                    self.session.restart()
                elif self.session.state == GameState.TITLE and event.key in (
                    pygame.K_RETURN,
                    pygame.K_SPACE,
                ):
                    self.session.new_game()
                elif (
                    self.session.state == GameState.TITLE
                    and event.key == pygame.K_l
                ):
                    self.session.show_leaderboard()
                elif (
                    self.session.state == GameState.LEADERBOARD
                    and event.key == pygame.K_RETURN
                ):
                    self.session.return_to_title()
                elif (
                    self.session.state == GameState.STAGE_CLEAR
                    and event.key == pygame.K_RETURN
                ):
                    self.session.advance_after_result()
                elif (
                    self.session.state == GameState.STAGE_CLEAR
                    and event.key == pygame.K_l
                ):
                    self.particles.clear()
                    self.session.save_score_and_end()
                elif (
                    self.session.state == GameState.VICTORY
                    and event.key == pygame.K_RETURN
                ):
                    self.particles.clear()
                    self.session.begin_name_entry()
                elif (
                    self.session.state == GameState.GAME_OVER
                    and event.key == pygame.K_RETURN
                ):
                    self.particles.clear()
                    self.session.begin_name_entry()
                elif event.key == pygame.K_p:
                    self.session.toggle_pause()
                elif self.session.state == GameState.CRASHED and event.key in (
                    pygame.K_RETURN,
                    pygame.K_SPACE,
                ):
                    self.session.advance_after_result()

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
            particle.x = (
                particle.x + particle.velocity_x * dt
            ) % self.settings.world_width
            particle.y += particle.velocity_y * dt
            particle.velocity_y += 20.0 * dt
            alive.append(particle)
        self.particles = alive

    @property
    def camera_x(self) -> float:
        lander = self.session.lander
        if lander is None:
            return 0.0
        return lander.x - self.settings.screen_width / 2.0

    def _draw(self) -> None:
        menu_screen = self.session.state in (
            GameState.TITLE,
            GameState.LEADERBOARD,
        )
        background_stage = STAGES[0] if menu_screen else self.session.current_stage
        if self.star_stage != background_stage:
            self._regenerate_stars(background_stage)

        self.screen.fill(background_stage.sky)
        camera_x = 0.0 if menu_screen else self.camera_x
        self._draw_stars(background_stage.star_color, camera_x)
        if not menu_screen and background_stage.star_count == 0:
            self._draw_haze()
        if self.session.state == GameState.TITLE:
            self._draw_title()
        elif self.session.state == GameState.LEADERBOARD:
            self._draw_leaderboard()
        else:
            self._draw_world()
            self._draw_hud()
            self._draw_overlay()
        pygame.display.flip()

    def _draw_stars(
        self, color: tuple[int, int, int], camera_x: float = 0.0
    ) -> None:
        for x, y, radius in self.stars:
            screen_x = (x - camera_x * 0.3) % self.settings.screen_width
            pygame.draw.circle(self.screen, color, (screen_x, y), radius)

    def _draw_haze(self) -> None:
        for y in (90, 180, 270):
            pygame.draw.rect(
                self.screen,
                (30, 23, 9),
                (0, y, self.settings.screen_width, 26),
            )

    def _draw_title(self) -> None:
        self._center_text("MOON DESCENT", 150, self.font_large, PHOSPHOR)
        self._center_text(
            "VECTOR FLIGHT SIMULATION", 232, self.font_small, AMBER
        )
        controls = (
            f"{'LEFT / RIGHT':<14}ROTATE",
            f"{'UP / SPACE':<14}MAIN THRUSTER",
            f"{'P':<14}PAUSE",
            f"{'R':<14}RESTART",
            f"{'ESC':<14}QUIT",
            f"{'L':<14}LEADERBOARD",
        )
        self._left_aligned_block(
            controls,
            320,
            32,
            self.font_small,
            WHITE,
        )
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

    def _draw_leaderboard(self) -> None:
        self._center_text("LEADERBOARD", 75, self.font_large, PHOSPHOR)
        lines = [" #    SCORE  BODY   NAME       DATE"]
        colors = [AMBER]
        for rank, entry in enumerate(
            self.session.leaderboard.entries,
            start=1,
        ):
            lines.append(
                f"{rank:>2}  {entry['score']:>7}  "
                f"{entry['body']:<7}{entry['name']:<11}{entry['date']}"
            )
            colors.append(
                AMBER
                if entry is self.session.fresh_leaderboard_entry
                else WHITE
            )
        self._left_aligned_block(
            lines,
            175,
            34,
            self.font_small,
            colors,
        )
        if not self.session.leaderboard.entries:
            self._center_text(
                "NO RECORDED MISSIONS",
                260,
                self.font_small,
                DIM,
            )
        self._center_text(
            "ENTER / ESC  TITLE",
            650,
            self.font_small,
            PHOSPHOR,
        )

    def _draw_world(self) -> None:
        terrain = self.session.terrain
        lander = self.session.lander
        if terrain is None or lander is None:
            return

        camera_x = self.camera_x
        stage = self.session.current_stage
        world_width = float(terrain.width)
        center_copy = math.floor(camera_x / world_width)
        world_shifts = tuple(
            copy_index * world_width
            for copy_index in range(center_copy - 1, center_copy + 2)
        )

        for shift in world_shifts:
            polygon = [
                (x + shift - camera_x, y) for x, y in terrain.polygon()
            ]
            surface_line = [
                (x + shift - camera_x, y) for x, y in terrain.points
            ]
            pygame.draw.polygon(self.screen, stage.ground_fill, polygon)
            pygame.draw.lines(
                self.screen,
                stage.terrain_color,
                False,
                surface_line,
                2,
            )

        for pad in terrain.pads:
            label = self.font_small.render(f"x{pad.multiplier}", True, AMBER)
            bonus_percent = int((pad.distance_bonus - 1.0) * 100)
            bonus_label = (
                self.font_small.render(
                    f"+{bonus_percent}%",
                    True,
                    DIM,
                )
                if bonus_percent >= 1
                else None
            )
            for shift in world_shifts:
                start_x = pad.start_x + shift - camera_x
                end_x = pad.end_x + shift - camera_x
                if end_x < 0.0 or start_x > self.settings.screen_width:
                    continue
                pygame.draw.line(
                    self.screen,
                    AMBER,
                    (start_x, pad.y),
                    (end_x, pad.y),
                    5,
                )
                self.screen.blit(
                    label,
                    (
                        pad.center_x
                        + shift
                        - camera_x
                        - label.get_width() / 2,
                        pad.y + 10,
                    ),
                )
                if bonus_label is not None:
                    self.screen.blit(
                        bonus_label,
                        (
                            pad.center_x
                            + shift
                            - camera_x
                            - bonus_label.get_width() / 2,
                            pad.y + 12 + label.get_height(),
                        ),
                    )

        if self.session.state not in (GameState.CRASHED, GameState.GAME_OVER):
            self._draw_lander(
                self.settings.screen_width / 2.0,
                lander.y,
                lander.angle,
            )

        for particle in self.particles:
            screen_x = (particle.x - camera_x) % world_width
            if screen_x > self.settings.screen_width:
                continue
            radius = 2 if particle.life > 0.3 else 1
            pygame.draw.circle(
                self.screen,
                particle.color,
                (int(screen_x), int(particle.y)),
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
            f"STAGE {self.session.stage}/{len(STAGES)} "
            f"{self.session.current_stage.name}",
            f"LIVES {self.session.lives}",
        )
        ppm = self.settings.pixels_per_meter
        right_lines = (
            f"ALT  {self.session.altitude / ppm:05.1f} M",
            f"H-S  {lander.velocity_x / ppm:+05.1f} M/S",
            f"V-S  {lander.velocity_y / ppm:+05.1f} M/S",
            f"FUEL {lander.fuel:06.1f}",
            f"GRAV {self.session.current_stage.gravity_ms2:4.2f} M/S2",
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
        capacity = self.settings.fuel_capacity
        fill_width = int(
            bar_width * min(1.0, max(0.0, lander.fuel / capacity))
        )
        pygame.draw.rect(
            self.screen,
            warning_color,
            (bar_x, bar_y, fill_width, bar_height),
        )
        if lander.fuel > capacity:
            extension_width = int(
                42
                * min(
                    1.0,
                    (lander.fuel - capacity)
                    / self.settings.max_time_bonus_fuel,
                )
            )
            pygame.draw.rect(
                self.screen,
                AMBER,
                (bar_x + bar_width + 4, bar_y, extension_width, bar_height),
            )

    def _draw_overlay(self) -> None:
        state = self.session.state
        if state == GameState.PAUSED:
            self._panel_message("PAUSED", "PRESS P TO RESUME", PHOSPHOR)
        elif state == GameState.STAGE_CLEAR:
            next_stage = self.session.next_stage
            award_line = (
                f"EMERGENCY +{self.session.last_award} POINTS"
                if (
                    self.session.last_landing_result
                    == LandingResult.EMERGENCY_LANDED
                )
                else f"+{self.session.last_award} POINTS"
            )
            self._panel_lines(
                f"{self.session.current_stage.name} CLEARED",
                (
                    award_line,
                    f"TIME {self.session.clear_elapsed:.1f}s  /  "
                    f"FUEL BONUS +{self.session.last_fuel_bonus:.0f}",
                    f"{'ENTER':<7}NEXT: "
                    f"{next_stage.name if next_stage else ''}",
                    f"{'L':<7}SAVE SCORE & END",
                    f"{'R':<7}NEW GAME",
                ),
                PHOSPHOR,
                hint_start=2,
            )
        elif state == GameState.CRASHED:
            self._panel_message("MODULE DESTROYED", "RETRYING...", RED)
        elif state == GameState.GAME_OVER:
            self._panel_lines(
                "MISSION ENDED",
                (
                    f"FINAL {self.session.final_score:06d}",
                    f"{'ENTER':<7}SAVE SCORE",
                    f"{'R':<7}RETRY",
                ),
                RED,
                hint_start=1,
            )
        elif state == GameState.VICTORY:
            self._panel_lines(
                "MISSION COMPLETE",
                (
                    f"FINAL {self.session.final_score:06d}",
                    f"{'ENTER':<7}SAVE SCORE",
                    f"{'R':<7}NEW GAME",
                ),
                PHOSPHOR,
                hint_start=1,
            )
        elif state == GameState.NAME_ENTRY:
            self._panel_lines(
                "ENTER CALLSIGN",
                (
                    f"{self.session.name_input}_",
                    f"{'ENTER':<7}SAVE",
                    f"{'ESC':<7}SKIP",
                ),
                PHOSPHOR,
                hint_start=1,
            )
        elif self.session.stage_intro_active:
            stage = self.session.current_stage
            self._panel_message(
                stage.name,
                f"GRAVITY {stage.gravity_ms2:.2f} M/S2",
                PHOSPHOR,
                self.font_large,
            )

    def _panel_lines(
        self,
        title: str,
        lines: tuple[str, ...],
        color: tuple[int, int, int],
        hint_start: int,
    ) -> None:
        panel_width = 720
        panel_height = 135 + len(lines) * 35
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((0, 8, 6, 220))
        pygame.draw.rect(panel, color, panel.get_rect(), 2)
        panel_x = self.settings.screen_width / 2 - panel_width / 2
        panel_y = self.settings.screen_height / 2 - panel_height / 2
        self.screen.blit(panel, (panel_x, panel_y))
        self._center_text(
            title,
            panel_y + 32,
            self.font_medium,
            color,
        )
        for index, line in enumerate(lines[:hint_start]):
            self._center_text(
                line,
                panel_y + 88 + index * 35,
                self.font_small,
                WHITE,
            )
        self._left_aligned_block(
            lines[hint_start:],
            panel_y + 88 + hint_start * 35,
            35,
            self.font_small,
            PHOSPHOR,
        )

    def _panel_message(
        self,
        title: str,
        subtitle: str,
        color: tuple[int, int, int],
        title_font: pygame.font.Font | None = None,
    ) -> None:
        title_font = title_font or self.font_medium
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
            self.settings.screen_height / 2
            - (62 if title_font is self.font_large else 48),
            title_font,
            color,
        )
        self._center_text(
            subtitle,
            self.settings.screen_height / 2
            + (30 if title_font is self.font_large else 15),
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

    def _left_aligned_block(
        self,
        lines: tuple[str, ...] | list[str],
        y: float,
        line_height: float,
        font: pygame.font.Font,
        color: tuple[int, int, int] | list[tuple[int, int, int]],
    ) -> None:
        """여러 줄을 같은 x에서 왼쪽 정렬하고 블록 전체를 화면 중앙에 둔다."""
        colors = color if isinstance(color, list) else [color] * len(lines)
        surfaces = [
            font.render(line, True, line_color)
            for line, line_color in zip(lines, colors)
        ]
        if not surfaces:
            return
        x = (
            self.settings.screen_width
            - max(surface.get_width() for surface in surfaces)
        ) / 2
        for index, surface in enumerate(surfaces):
            self.screen.blit(surface, (x, y + index * line_height))

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
