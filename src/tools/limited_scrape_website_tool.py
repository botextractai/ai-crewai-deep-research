from pydantic import Field
from crewai.tools import BaseTool
from crewai_tools import ScrapeWebsiteTool
from src.utils import get_scrape_max_chars

class LimitedScrapeWebsiteTool(BaseTool):
    name: str = "Read website content (limited)"
    description: str = (
        "Read website content through ScrapeWebsiteTool with a strict output size cap "
        "to prevent oversized context payloads."
    )
    max_chars: int = Field(default_factory=get_scrape_max_chars)
    scraper: ScrapeWebsiteTool = Field(default_factory=ScrapeWebsiteTool, exclude=True)
    
    def _run(self, website_url: str) -> str:
        content = self.scraper.run(website_url=website_url)
        content = content if isinstance(content, str) else str(content)
        
        if len(content) <= self.max_chars:
            return content
        
        truncated = content[: self.max_chars]
        return (
            f"{truncated}\n\n"
            f"[TRUNCATED] Original scraped content exceeded {self.max_chars} characters."
        )
