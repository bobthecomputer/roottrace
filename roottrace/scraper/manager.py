from __future__ import annotations

from dataclasses import dataclass

from roottrace.config import Settings, settings


@dataclass(slots=True)
class ScraperPlan:
    platform: str
    tool: str
    rate_qps: float
    max_items: int
    cookies_path: str | None
    legal_note: str


class ScraperManager:
    """Validate and describe fallback scraper usage."""

    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    def build_plan(self) -> ScraperPlan | None:
        if not self.config.scraper_platform or not self.config.scraper_tool:
            return None
        if not self.config.legal_note:
            raise PermissionError("Scraper legal note required before activation")
        return ScraperPlan(
            platform=self.config.scraper_platform,
            tool=self.config.scraper_tool,
            rate_qps=self.config.scraper_rate_qps,
            max_items=self.config.scraper_max_items,
            cookies_path=(
                str(self.config.scraper_cookies_path)
                if self.config.scraper_cookies_path
                else None
            ),
            legal_note=self.config.legal_note,
        )


__all__ = ["ScraperManager", "ScraperPlan"]
