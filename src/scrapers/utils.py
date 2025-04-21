import asyncio
import logging
from random import choice, random
from typing import List

from playwright.async_api import Browser, TimeoutError, async_playwright

from engine import config

log = logging.getLogger(__name__)


async def _fetch_single_page(browser: Browser, url: str, page_load_indicator_selector: str) -> str:
    # break up requests in time slightly so the site is not strained
    await asyncio.sleep(random() * config.PLAYWRIGHT_POLL_JITTER_S)
    log.debug(f'Opening page for: {url}')
    # randomise identity a bit
    context = await browser.new_context(
        user_agent=choice(config.PLAYWRIGHT_USER_AGENTS),
        viewport=choice(config.PLAYWRIGHT_VIEWPORTS),
        locale=choice(config.PLAYWRIGHT_LOCALES),
    )
    page = await context.new_page()
    try:
        await page.goto(url, timeout=config.PLAYWRIGHT_LOAD_TIMEOUT_S * 1000)
        log.debug(f'Waiting for {url} to render...')

        await page.wait_for_selector(page_load_indicator_selector, timeout=config.PLAYWRIGHT_LOAD_TIMEOUT_S * 1000)

        html = await page.content()
        log.debug('html extracted')
        return html
    except TimeoutError:
        html = await page.content()
        log.warning(
            f'Timed out when fetching {url}, page url was {page.url}, '
            f'page title was {await page.title()}, content contained {html[:10000]}, '
            'returning empty string.'
        )
        return ''
    finally:
        await page.close()


async def scrape_urls(urls: List[str], page_load_indicator_selector: str) -> List[str]:
    async with async_playwright() as p:
        log.debug('Launching browser...')
        browser = await p.chromium.launch(headless=True)
        try:
            tasks = [_fetch_single_page(browser, url, page_load_indicator_selector) for url in urls]
            html_pages = await asyncio.gather(*tasks)
            return html_pages
        finally:
            await browser.close()
