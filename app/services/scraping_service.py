import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScrapingResult:
    """Immutable data container for scraped document attributes."""
    url: str
    title: str
    text: str
    status_code: int


def scrape_website(
    url: str,
    timeout: float = 10.0,
    headers: Optional[dict[str, str]] = None,
) -> Optional[ScrapingResult]:
    """Fetches a webpage, strips visual noise, and extracts clean plain text.

    Args:
        url: The web address to scrape.
        timeout: Maximum request duration in seconds.
        headers: Optional custom HTTP headers to override defaults.

    Returns:
        A ScrapingResult instance on success, or None on failure.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid HTTP/HTTPS URL: {url}")

    default_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    merged_headers = {**default_headers, **(headers or {})}

    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            response = client.get(url, headers=merged_headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("HTTP error fetching %s: %s", url, exc)
        return None

    # Parse DOM tree using 'lxml' for higher execution speed
    soup = BeautifulSoup(response.content, "lxml")

    # Decompose script, styling, and navigation bloat
    unwanted_tags = ["script", "style", "nav", "footer", "header", "noscript", "svg", "form", "aside"]
    for element in soup.find_all(unwanted_tags):
        element.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    
    # Extract line-separated text and purge empty whitespace
    lines = (line.strip() for line in soup.get_text(separator="\n").splitlines())
    clean_text = "\n".join(line for line in lines if line)

    return ScrapingResult(
        url=str(response.url),
        title=title,
        text=clean_text,
        status_code=response.status_code,
    )
