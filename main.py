"""Entry point for Moon Descent (desktop and web builds)."""

import asyncio

from lunar_lander.app import LunarLanderApp


async def main() -> None:
    await LunarLanderApp().run_async()


# pygbag(웹 로더)은 __main__ 가드 안의 코드를 실행하지 않으므로 최상위에서 호출한다.
asyncio.run(main())
