import asyncio
from typing import Any, AsyncIterator, Iterator, List, Optional
import aiohttp
import async_timeout
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document
try:
    from playwright.async_api import async_playwright
except ImportError:
    raise ImportError(
        "playwright is required for ChromiumLoader. "
        "Please install it with `pip install playwright` and `playwright install chromium`"
    )
from undetected_playwright import Malenia

from ..utils.logging import get_logger
logger = get_logger(__name__)
class ChromiumLoader(BaseLoader):
    def __init__(
        self,
        urls: List[str],
        *,
        headless: bool = True,
        load_state: str = "domcontentloaded",
        storage_state: Optional[str] = None,
        browser_name: str = "chromium",
        retry_limit: int = 1,
        timeout: int = 60,
        **kwargs: Any,
    ):
        self.browser_config = kwargs
        self.headless = headless
        self.urls = urls
        self.load_state = load_state
        self.storage_state = storage_state
        self.browser_name = browser_name
        self.retry_limit = retry_limit
        self.timeout = timeout
    async def ascrape_playwright(self, url: str, browser_name: str = "chromium") -> str:
        logger.info(f"Starting scraping with playwright for {url}...")
        results = ""
        attempt = 0
        while attempt < self.retry_limit:
            browser = None
            context = None
            page = None
            try:
                async with async_playwright() as p, async_timeout.timeout(self.timeout):
                    if browser_name == "chromium":
                        browser = await p.chromium.launch(
                            headless=self.headless,
                            **self.browser_config,
                        )
                    elif browser_name == "firefox":
                        browser = await p.firefox.launch(
                            headless=self.headless,
                            **self.browser_config,
                        )
                    else:
                        raise ValueError(f"Invalid browser name: {browser_name}")
                    context = await browser.new_context(
                        storage_state=self.storage_state,
                        ignore_https_errors=True,
                    )
                    await Malenia.apply_stealth(context)
                    page = await context.new_page()
                    await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                    await page.wait_for_load_state(self.load_state, timeout=self.timeout * 1000)
                    results = await page.content()
                    logger.debug(f"Content scraped successfully for {url}")
                    return results
            except (aiohttp.ClientError, asyncio.TimeoutError, Exception) as e:
                attempt += 1
                logger.error(f"Attempt {attempt}/{self.retry_limit} failed for {url}: {type(e).__name__} - {e}")
                if attempt == self.retry_limit:
                     logger.error(f"Failed to scrape {url} after {self.retry_limit} attempts.")
                     return ""
            finally:
                if browser:
                    try:
                        await browser.close()
                    except Exception as e_browser:
                        logger.debug(f"Error closing browser for {url}: {e_browser}")
        return ""
    def lazy_load(self) -> Iterator[Document]:
        for url in self.urls:
            try:
                 html_content = asyncio.run(self.ascrape_playwright(url, self.browser_name))
                 metadata = {"source": url}
                 if not html_content:
                      metadata["error"] = "Failed to fetch content"
                 yield Document(page_content=html_content, metadata=metadata)
            except Exception as e:
                 logger.error(f"Error during lazy_load for {url}: {e}")
                 yield Document(page_content="", metadata={"source": url, "error": str(e)})
    async def alazy_load(self) -> AsyncIterator[Document]:
        tasks = [self.ascrape_playwright(url, self.browser_name) for url in self.urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            url = self.urls[i]
            metadata = {"source": url}
            if isinstance(result, Exception):
                logger.error(f"Error during alazy_load for {url}: {result}")
                yield Document(page_content="", metadata={"source": url, "error": str(result)})
            else:
                 if not result:
                      metadata["error"] = "Failed to fetch content"
                 yield Document(page_content=result, metadata=metadata)
    def load(self) -> List[Document]:
        return list(self.lazy_load())
    async def aload(self) -> List[Document]:
         docs = []
         async for doc in self.alazy_load():
             docs.append(doc)
         return docs
