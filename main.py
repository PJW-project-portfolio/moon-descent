"""Entry point for Moon Descent (desktop and web builds)."""

import asyncio

from lunar_lander.app import LunarLanderApp


async def main() -> None:
    await LunarLanderApp().run_async()


if __name__ == "__main__":
    asyncio.run(main())
