"""Regenerate the play-guide infographics.

1. 실제 게임 화면을 헤드리스로 그려 docs/infographic/shots/에 저장한다.
2. docs/infographic/의 HTML 두 장을 Chromium으로 열어 2배 해상도 PNG로 내보낸다.
     index.html   → play-guide.png          (README용 세로형 전체 가이드)
     compact.html → play-guide-compact.png  (게임 화면 한 장 위 설명 레이어)
   Playwright가 없으면 1단계만 하고 설치 방법을 출력한다.
       python -m pip install playwright
       python -m playwright install chromium

HTML의 숫자는 settings.py · stages.py 값을 옮겨 적은 것이므로 그 값을
바꾸면 HTML 문구도 함께 고친다.
"""

import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pygame  # noqa: E402

from lunar_lander import leaderboard  # noqa: E402
from lunar_lander.app import LunarLanderApp  # noqa: E402
from lunar_lander.game_state import GameState  # noqa: E402
from lunar_lander.terrain import LandingPad  # noqa: E402


GUIDE_DIR = PROJECT_ROOT / "docs" / "infographic"
SHOTS_DIR = GUIDE_DIR / "shots"
# (원본 HTML, 출력 PNG, 뷰포트 너비, 뷰포트 높이)
PAGES = (
    ("index.html", "play-guide.png", 1200, 800),
    ("compact.html", "play-guide-compact.png", 1280, 720),
)


def pad_with_multiplier(app: LunarLanderApp, multiplier: int) -> LandingPad:
    assert app.session.terrain is not None
    return next(
        pad
        for pad in app.session.terrain.pads
        if pad.multiplier == multiplier
    )


def pose_in_flight(
    app: LunarLanderApp,
    stage: int,
    multiplier: int,
    offset_x: float,
    height: float,
    velocity: tuple[float, float],
    angle: float,
    fuel: float,
    score: int = 0,
) -> None:
    """Place the lander near a pad mid-descent with its thruster firing."""
    session = app.session
    session.new_game()
    if stage > 1:
        session.stage = stage
        session._prepare_round(fuel)
    session.score = session.high_score = score
    pad = pad_with_multiplier(app, multiplier)
    lander = session.lander
    assert lander is not None
    lander.x = pad.center_x - offset_x
    lander.y = pad.y - session.settings.lander_bottom_offset - height
    lander.velocity_x, lander.velocity_y = velocity
    lander.angle = angle
    lander.fuel = fuel
    session.stage_intro_elapsed = session.settings.round_transition_seconds
    app.previous_state = session.state
    app.particles.clear()
    for _ in range(24):  # 불꽃 입자가 퍼질 만큼 몇 프레임 분사한다
        lander.thrusting = True
        app._emit_effects(1 / 60)
        app._update_particles(1 / 60)
    app._draw()


def touch_down_on_pad(app: LunarLanderApp) -> None:
    """Land on the x4 pad for real so the clear panel shows the game's award."""
    session = app.session
    session.new_game()
    pad = pad_with_multiplier(app, 4)
    lander = session.lander
    assert lander is not None
    lander.x = pad.center_x
    lander.y = pad.y - session.settings.lander_bottom_offset - 0.1
    lander.velocity_x, lander.velocity_y = 4.0, 15.0
    lander.angle = 3.0
    lander.fuel = 38.5
    session.stage_intro_elapsed = session.settings.round_transition_seconds
    session.stage_elapsed = 38.0
    session.update(0.01)
    assert session.state == GameState.STAGE_CLEAR
    app.particles.clear()
    app._draw()
    print(
        f"clear panel: +{session.last_award} points, "
        f"fuel bonus +{session.last_fuel_bonus:.1f}"
    )


def save(app: LunarLanderApp, name: str) -> None:
    path = SHOTS_DIR / name
    pygame.image.save(app.screen, str(path))
    print(f"Saved {path.relative_to(PROJECT_ROOT)}")


def capture_shots() -> None:
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    # 캡처용 게임이 실제 records/ 기록을 건드리지 않게 임시 폴더를 쓴다.
    with tempfile.TemporaryDirectory() as folder:
        with patch.object(
            leaderboard, "LEADERBOARD_PATH", Path(folder) / "leaderboard.json"
        ), patch.object(
            leaderboard,
            "LEGACY_LEADERBOARD_PATH",
            Path(folder) / "legacy" / "leaderboard.json",
        ):
            app = LunarLanderApp(seed=1)
            pose_in_flight(app, 1, 4, 170, 150, (16, 22), -10, 46.3)
            save(app, "hud.png")

            for stage, multiplier, score, name in (
                (1, 2, 0, "stage_moon.png"),
                (2, 3, 486, "stage_mars.png"),
                (3, 5, 1233, "stage_venus.png"),
            ):
                app = LunarLanderApp(seed=3)
                pose_in_flight(
                    app, stage, multiplier, 230, 210, (24, 14), -14, 78.0, score
                )
                save(app, name)

            app = LunarLanderApp(seed=1)
            touch_down_on_pad(app)
            save(app, "clear.png")
    pygame.quit()


def render_pages() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Playwright가 없어 PNG 내보내기를 건너뜁니다.\n"
            "  python -m pip install playwright\n"
            "  python -m playwright install chromium"
        )
        return

    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            proxy={"server": proxy} if proxy else None
        )
        for source, output, width, height in PAGES:
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=2,
            )
            page.goto((GUIDE_DIR / source).as_uri(), wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            output_path = GUIDE_DIR / output
            page.screenshot(path=str(output_path), full_page=True)
            page.close()
            print(f"Saved {output_path.relative_to(PROJECT_ROOT)}")
        browser.close()


def main() -> None:
    os.chdir(PROJECT_ROOT)
    capture_shots()
    render_pages()


if __name__ == "__main__":
    main()
