"""URL scraper tool – fetch and extract text from web pages."""

from typing import Any

import httpx


def scrape_url(url: str, max_length: int = 5000) -> dict[str, Any]:
    """Fetch a URL and extract readable text content.

    Args:
        url: URL to scrape.
        max_length: Maximum characters of text to return.

    Returns:
        Dict with url, title, text, and status_code.
    """
    try:
        response = httpx.get(url, timeout=15, follow_redirects=True)
        response.raise_for_status()
    except Exception as e:
        return {"url": url, "title": "", "text": "", "error": str(e), "status_code": 0}

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    text = soup.get_text(separator="\n", strip=True)[:max_length]
    return {
        "url": url,
        "title": title,
        "text": text,
        "status_code": response.status_code,
    }
