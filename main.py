"""Entry point for Moon Descent (desktop and web builds)."""

import asyncio

# pygbag(웹 빌드)은 main.py의 import 목록을 보고 필요한 웹용 패키지를 내려받으므로,
# 게임 패키지 내부에서만 쓰더라도 여기서 pygame을 직접 import해야 한다.
import pygame  # noqa: F401

from lunar_lander.app import LunarLanderApp


async def main() -> None:
    await LunarLanderApp().run_async()


# pygbag(웹 로더)은 __main__ 가드 안의 코드를 실행하지 않으므로 최상위에서 호출한다.
asyncio.run(main())
