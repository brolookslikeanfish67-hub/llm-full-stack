from dataclasses import dataclass
import logging
from typing import Optional, Set
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup, Comment

# Configure logging to see errors or status metrics in your terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# =====================================================================
# Custom Exceptions
# =====================================================================
class ScraperError(Exception):
    """Base exception class for web scraping pipeline failures."""


class FetchError(ScraperError):
    """Raised when an HTTP fetch fails after maximum backoff retries."""


class ParseError(ScraperError):
    """Raised when HTML parsing or text processing encounters an anomaly."""


# =====================================================================
# Data Models
# =====================================================================
@dataclass(frozen=True)
class ScrapedDocument:
    """Immutable model representing a cleanly extracted web document."""

    url: str
    title: str
    text: str
    status_code: int


# =====================================================================
# Scraper Implementation
# =====================================================================
class DocumentScraper:
    """Production-grade web document parser following Google Python Style conventions.

    Features connection pooling, dynamic backoff strategy, explicit URL validation,
    HTML noise decomposition, and full context manager support.
    """

    # Uninformative tags that pollute raw text output
    NOISE_TAG_NAMES: Set[str] = {
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

    def __init__(
        self,
        timeout_seconds: int = 10,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        user_agent: Optional[str] = None,
    ) -> None:
        self.timeout = timeout_seconds
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
        self.session = self._init_session(max_retries, backoff_factor)

    def _init_session(self, max_retries: int, backoff_factor: float) -> requests.Session:
        """Configures a reusable Session with exponential connection retry rules."""
        session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        return session

    def fetch(self, url: str) -> ScrapedDocument:
        """Fetches and parses a web page into a structured document object.

        Args:
            url: The targeted HTTP/HTTPS address.

        Returns:
            A populated ScrapedDocument instance.

        Raises:
            ValueError: If the input URL is malformed.
            FetchError: If network connectivity or server issues persist.
            ParseError: If parsing logic fails unexpectedly.
        """
        self._validate_url(url)

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("HTTP request failure for %s: %s", url, exc)
            raise FetchError(f"Failed to fetch resource at target URL: {url}") from exc

        try:
            # Use 'lxml' parser for speed over the default 'html.parser'
            # Note: requires `pip install lxml`
            soup = BeautifulSoup(response.content, "lxml")

            # Eliminate noise elements and hidden HTML comments
            for element in soup.find_all(self.NOISE_TAG_NAMES):
                element.decompose()

            # FIXED: Changed 'text=' to 'string=' for compatibility with BS4 v4.12+
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()

            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            lines = (line.strip() for line in soup.get_text(separator="\n").splitlines())
            clean_text = "\n".join(line for line in lines if line)

            return ScrapedDocument(
                url=url,
                title=title,
                text=clean_text,
                status_code=response.status_code,
            )
        except Exception as exc:
            logger.error("Parsing failure for %s: %s", url, exc)
            raise ParseError(f"Failed to extract text content from {url}") from exc

    @staticmethod
    def _validate_url(url: str) -> None:
        """Enforces web protocol schemes before dispatching network calls."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Malformed web address: '{url}'")

    def close(self) -> None:
        """Closes HTTP underlying transport connections."""
        self.session.close()

    def __enter__(self) -> "DocumentScraper":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


# =====================================================================
# Execution Block / Example Usage
# =====================================================================
if __name__ == "__main__":
    # Target URL for verification
    target_url = "https://example.com"
    
    print(f"--- Starting Scraper Testing on {target_url} ---")
    
    # Utilizing Context Manager syntax for automated teardown
    with DocumentScraper(timeout_seconds=5) as scraper:
        try:
            document = scraper.fetch(target_url)
            
            print("\n[SUCCESS] Document Successfully Retrieved")
            print(f"URL:          {document.url}")
            print(f"HTTP Status:  {document.status_code}")
            print(f"Page Title:   {document.title}")
            print(f"Clean Text Content snippet:\n")
            print("-" * 40)
            # Print the first 300 characters of clean text
            print(document.text[:300] + "...") 
            print("-" * 40)
            
        except ValueError as err:
            print(f"[URL ERROR] Checked address failed validation: {err}")
        except FetchError as err:
            print(f"[FETCH ERROR] Remote server unreachable or timed out: {err}")
        except ParseError as err:
            print(f"[PARSE ERROR] HTML structure syntax parsing anomaly: {err}")
