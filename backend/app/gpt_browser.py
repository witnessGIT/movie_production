from __future__ import annotations

import asyncio
import sys

from .storage import ROOT, safe_id


async def launch(profile_id: str) -> None:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise SystemExit("Playwright 未安装。请执行: pip install -e '.[browser]' && playwright install chromium") from exc

    profile_dir = ROOT / "browser_profiles" / safe_id(profile_id)
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            viewport={"width": 1440, "height": 920},
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://chatgpt.com", wait_until="domcontentloaded")
        print(f"ChatGPT browser profile opened: {profile_id}")
        stop = asyncio.Event()
        context.on("close", lambda: stop.set())
        await stop.wait()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.gpt_browser <profile_id>")
    asyncio.run(launch(sys.argv[1]))
