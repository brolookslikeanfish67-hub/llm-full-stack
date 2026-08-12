import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, status
import httpx
from pydantic import BaseModel, HttpUrl

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scraper_service")


# --- Schemas ---
class ScrapeRequest(BaseModel):
    url: HttpUrl
    timeout: float = 10.0


class ScrapeResponse(BaseModel):
    url: str
    title: str
    content: str
    word_count: int


# --- Service Layer ---
class ScrapingService:
    """Async web scraping service optimized for LLM ingestion."""

    NOISE_TAGS = {
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "noscript",
        "svg",
        "form",
        "aside",
    }

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def scrape_and_clean(self, url: str, timeout: float = 10.0) -> ScrapeResponse:
        """Fetches a URL, strips DOM bloat, and returns structured LLM-ready text."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            response = await self.client.get(
                url, headers=headers, timeout=timeout, follow_redirects=True
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("HTTP status error for %s: %s", url, exc)
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Target server returned HTTP {exc.response.status_code}",
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Network error fetching %s: %s", url, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to connect to the target website",
            ) from exc

        soup = BeautifulSoup(response.content, "lxml")

        for tag in soup.find_all(self.NOISE_TAGS):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        lines = (line.strip() for line in soup.get_text(separator="\n").splitlines())
        clean_text = "\n".join(line for line in lines if line)

        return ScrapeResponse(
            url=str(response.url),
            title=title,
            content=clean_text,
            word_count=len(clean_text.split()),
        )


# --- Lifespan Context Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and shutdown tasks (HTTP client lifecycle)."""
    app.state.http_client = httpx.AsyncClient(
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
    )
    yield  # Pause execution during server runtime
    await app.state.http_client.aclose()  # Trigger clean socket closure on app shutdown


# --- FastAPI Application ---
app = FastAPI(
    title="LLM Web Scraping Ingestion API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/api/v1/scrape", response_model=ScrapeResponse)
async def scrape_endpoint(payload: ScrapeRequest) -> ScrapeResponse:
    """Ingests a webpage and converts it into a clean format suitable for LLM contexts."""
    scraper = ScrapingService(client=app.state.http_client)
    return await scraper.scrape_and_clean(
        url=payload.url.unicode_string(),
        timeout=payload.timeout,
    )
