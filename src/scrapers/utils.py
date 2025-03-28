import asyncio
import logging
from typing import List
from random import choice, random

from playwright.async_api import async_playwright, Browser

from engine import config

log = logging.getLogger(__name__)


async def _fetch_single_page(browser: Browser, url: str) -> str:
    # break up requests in time slightly so the site is not strained
    await asyncio.sleep(random() * config.PLAYWRIGHT_POLL_JITTER_S)
    log.debug(f"Opening page for: {url}")
    # randomise identity a bit
    context = await browser.new_context(
        user_agent=choice(config.PLAYWRIGHT_USER_AGENTS),
        viewport=choice(config.PLAYWRIGHT_VIEWPORTS),
        locale=choice(config.PLAYWRIGHT_LOCALES),
    )
    page = await context.new_page()
    try:
        await page.goto(url)
        log.debug(f"Waiting for {url} to render...")
        await page.wait_for_timeout(config.PLAYWRIGHT_RENDER_WAIT_S * 1000)  # Wait for render
        html = await page.content()
        log.debug('html extracted')
        return html
    finally:
        await page.close()


async def _fetch_all_pages(urls: List[str]) -> List[str]:
    async with async_playwright() as p:
        log.debug("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        try:
            tasks = [_fetch_single_page(browser, url) for url in urls]
            html_pages = await asyncio.gather(*tasks)
            return html_pages
        finally:
            await browser.close()


def scrape_urls(urls):
    return asyncio.run(_fetch_all_pages(urls))
