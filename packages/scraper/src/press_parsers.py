"""Site-specific press release parsers.

Each parser handles a specific competitor's press release page structure,
extracting article lists (title, URL, date) from listing pages and
body text from individual article pages.

Supported sources:
- SUUMO (Recruit): https://www.recruit.co.jp/newsroom/
- athome: https://athome-inc.jp/news/
- Canary (BluAge): corporate press page
"""

import re
from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag


# Field length limits per design spec
MAX_TITLE_LENGTH = 512
MAX_URL_LENGTH = 2048
MAX_BODY_LENGTH = 100_000


class PressSourceParser(ABC):
    """Base class for site-specific press release parsers."""

    # URL patterns that are clearly NOT press release articles
    _NON_ARTICLE_URL_PATTERNS = re.compile(
        r"(^/$|^#|/contact/?$|/career/?$|/recruit/?$|/about/?$|/company/?$"
        r"|/mission/?$|/member/?$|/service/?$|/services/?$|/privacy/?$"
        r"|/terms/?$|/sitemap/?$|/faq/?$|/login/?$|/signup/?$"
        r"|/download/?$|/seminar/?$|/whitepaper/?$"
        r"|/cookie/?$|javascript:|mailto:)",
        re.IGNORECASE,
    )

    # Title patterns that indicate non-article pages
    _NON_ARTICLE_TITLE_PATTERNS = re.compile(
        r"^(Mission|Member|Services|Contact|Career|About|会社概要"
        r"|お問い合わせ|採用情報|事業内容|ミッション|メンバー"
        r"|プライバシー|利用規約|サイトマップ|お役立ち資料"
        r"|セミナー|資料ダウンロード)(\s|$)",
        re.IGNORECASE,
    )

    @abstractmethod
    def parse_article_list(self, html: str, base_url: str = "") -> list[dict]:
        """Extract article list from a press release listing page.

        Args:
            html: Raw HTML of the listing page.
            base_url: Base URL for resolving relative links.

        Returns:
            List of dicts with keys: title (str), url (str), published_at (str|None)
        """
        ...

    @abstractmethod
    def parse_article_body(self, html: str) -> str:
        """Extract main content text from an individual article page.

        Args:
            html: Raw HTML of the article page.

        Returns:
            Plain text content of the article body, truncated to MAX_BODY_LENGTH.
        """
        ...

    def _truncate_title(self, title: str) -> str:
        """Truncate title to MAX_TITLE_LENGTH characters."""
        if len(title) <= MAX_TITLE_LENGTH:
            return title
        return title[:MAX_TITLE_LENGTH]

    def _truncate_body(self, body: str) -> str:
        """Truncate body text to MAX_BODY_LENGTH characters."""
        if len(body) <= MAX_BODY_LENGTH:
            return body
        return body[:MAX_BODY_LENGTH]

    def _truncate_url(self, url: str) -> str:
        """Truncate URL to MAX_URL_LENGTH characters."""
        if len(url) <= MAX_URL_LENGTH:
            return url
        return url[:MAX_URL_LENGTH]

    def _clean_text(self, text: str) -> str:
        """Clean extracted text by normalizing whitespace."""
        # Replace multiple whitespace/newlines with single space
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _is_valid_article(self, title: str, url: str, source_url: str = "") -> bool:
        """Check if a parsed item is actually a press release article.

        Filters out navigation pages, static pages, and non-article URLs.

        Args:
            title: Article title.
            url: Article URL.
            source_url: The listing page URL (to exclude self-references).

        Returns:
            True if the item looks like a valid press article.
        """
        if not title or not url:
            return False

        # Exclude the listing page itself
        if source_url and url.rstrip("/") == source_url.rstrip("/"):
            return False

        # Exclude URLs matching non-article patterns
        parsed = urlparse(url)
        path = parsed.path
        if self._NON_ARTICLE_URL_PATTERNS.search(path):
            return False

        # Exclude titles matching non-article patterns
        if self._NON_ARTICLE_TITLE_PATTERNS.match(title.strip()):
            return False

        # Exclude very short titles that are likely nav items
        if len(title.strip()) < 10:
            return False

        return True

    def _resolve_url(self, url: str, base_url: str) -> str:
        """Resolve a potentially relative URL against the base URL."""
        if not url:
            return ""
        if url.startswith(("http://", "https://")):
            return self._truncate_url(url)
        return self._truncate_url(urljoin(base_url, url))

    def _parse_date_text(self, date_text: str) -> Optional[str]:
        """Attempt to parse a Japanese date string into ISO format.

        Handles patterns like:
        - 2025年1月15日
        - 2025.01.15
        - 2025/01/15
        - 2025-01-15

        Returns:
            ISO date string (YYYY-MM-DD) or None if parsing fails.
        """
        if not date_text:
            return None

        date_text = date_text.strip()

        # Pattern: 2025年1月15日 or 2025年01月15日
        match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_text)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"

        # Pattern: 2025.01.15 or 2025.1.15
        match = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", date_text)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"

        # Pattern: 2025/01/15 or 2025/1/15
        match = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", date_text)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"

        # Pattern: 2025-01-15
        match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_text)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"

        return None


class SuumoPressParser(PressSourceParser):
    """Parser for SUUMO (Recruit) press release pages.

    SUUMO press releases are hosted on Recruit's newsroom:
    https://www.recruit.co.jp/newsroom/

    Typical page structure:
    - Article list items within a news list container
    - Each item has a date element, category tag, and title link
    """

    def parse_article_list(self, html: str, base_url: str = "") -> list[dict]:
        """Parse SUUMO/Recruit newsroom article listing."""
        soup = BeautifulSoup(html, "lxml")
        articles: list[dict] = []

        # Recruit newsroom uses various list structures
        # Try common patterns for news listing pages

        # Pattern 1: dl/dt/dd structure (common in Japanese corporate sites)
        for item in soup.select("dl.news-list dt, dl.newsList dt"):
            date_elem = item
            dd_elem = item.find_next_sibling("dd")
            if not dd_elem:
                continue
            link = dd_elem.find("a")
            if not link:
                continue
            article = self._extract_from_link(link, date_elem.get_text(), base_url)
            if article:
                articles.append(article)

        if articles:
            return articles

        # Pattern 2: li-based news items
        for item in soup.select(
            "li.news-item, li.newsItem, .news-list li, .newsList li, "
            ".newsroom-list li, ul.list li"
        ):
            link = item.find("a")
            if not link:
                continue
            # Look for date in a time/span/p element
            date_text = self._find_date_in_element(item)
            article = self._extract_from_link(link, date_text, base_url)
            if article:
                articles.append(article)

        if articles:
            return articles

        # Pattern 3: article/section based
        for item in soup.select(
            "article, .article-item, .press-item, .news-entry"
        ):
            link = item.find("a")
            if not link:
                continue
            date_text = self._find_date_in_element(item)
            article = self._extract_from_link(link, date_text, base_url)
            if article:
                articles.append(article)

        if articles:
            return articles

        # Fallback: find all links that look like press release articles
        articles = self._fallback_link_extraction(soup, base_url)
        return articles

    def parse_article_body(self, html: str) -> str:
        """Parse SUUMO/Recruit article page body text."""
        soup = BeautifulSoup(html, "lxml")

        # Try common article body selectors for Recruit newsroom
        body_selectors = [
            ".news-detail__body",
            ".newsDetail__body",
            ".article-body",
            ".articleBody",
            ".press-body",
            ".entry-content",
            "article .content",
            "article",
            ".main-content",
            "main",
        ]

        for selector in body_selectors:
            elem = soup.select_one(selector)
            if elem and len(elem.get_text(strip=True)) > 50:
                return self._truncate_body(self._clean_text(elem.get_text(separator=" ")))

        # Fallback: largest text block
        return self._extract_largest_text_block(soup)

    def _extract_from_link(
        self, link: Tag, date_text: str, base_url: str
    ) -> Optional[dict]:
        """Extract article info from a link element."""
        href = link.get("href", "")
        title = self._clean_text(link.get_text())
        if not title or not href:
            return None
        return {
            "title": self._truncate_title(title),
            "url": self._resolve_url(str(href), base_url),
            "published_at": self._parse_date_text(date_text),
        }

    def _find_date_in_element(self, elem: Tag) -> str:
        """Find a date string within an element."""
        # Check time element first
        time_elem = elem.find("time")
        if time_elem:
            datetime_attr = time_elem.get("datetime", "")
            if datetime_attr:
                return str(datetime_attr)
            return time_elem.get_text()

        # Check span/p with date-like class
        for selector in [".date", ".time", ".news-date", ".newsDate", "span.date"]:
            date_elem = elem.select_one(selector)
            if date_elem:
                return date_elem.get_text()

        # Look for date pattern in text
        text = elem.get_text()
        match = re.search(
            r"\d{4}[年./\-]\d{1,2}[月./\-]\d{1,2}日?", text
        )
        if match:
            return match.group(0)

        return ""

    def _fallback_link_extraction(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        """Fallback: extract links that look like press releases."""
        articles: list[dict] = []
        seen_urls: set[str] = set()

        for link in soup.find_all("a", href=True):
            href = str(link["href"])
            # Filter for likely press/news article links
            if not re.search(
                r"(news|press|release|newsroom|recruit\.co\.jp/newsroom)",
                href,
                re.IGNORECASE,
            ):
                continue
            title = self._clean_text(link.get_text())
            if not title or len(title) < 5:
                continue
            url = self._resolve_url(href, base_url)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            articles.append({
                "title": self._truncate_title(title),
                "url": url,
                "published_at": None,
            })

        return articles

    def _extract_largest_text_block(self, soup: BeautifulSoup) -> str:
        """Extract the largest text block from the page as fallback."""
        # Remove script, style, nav, header, footer
        for tag in soup.find_all(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        best_text = ""
        for elem in soup.find_all(["div", "article", "section", "main"]):
            text = self._clean_text(elem.get_text(separator=" "))
            if len(text) > len(best_text):
                best_text = text

        return self._truncate_body(best_text)


class AthomePressParser(PressSourceParser):
    """Parser for athome press release pages.

    athome press releases are on their corporate site:
    https://athome-inc.jp/news/

    Typical page structure:
    - News list with date, category label, and title link
    """

    def parse_article_list(self, html: str, base_url: str = "") -> list[dict]:
        """Parse athome corporate news article listing."""
        soup = BeautifulSoup(html, "lxml")
        articles: list[dict] = []

        # Pattern 1: Table-like or dl-based news list
        for item in soup.select(
            "dl.news-list dt, dl.newsList dt, .news-list dl dt"
        ):
            date_elem = item
            dd_elem = item.find_next_sibling("dd")
            if not dd_elem:
                continue
            link = dd_elem.find("a")
            if not link:
                continue
            article = self._extract_article_item(link, date_elem.get_text(), base_url)
            if article:
                articles.append(article)

        if articles:
            return articles

        # Pattern 2: List items with date + title structure
        for item in soup.select(
            ".news-item, .newsItem, .news-list li, .newsList li, "
            ".press-list li, .topics-list li, ul.news li"
        ):
            link = item.find("a")
            if not link:
                continue
            date_text = self._find_date_text(item)
            article = self._extract_article_item(link, date_text, base_url)
            if article:
                articles.append(article)

        if articles:
            return articles

        # Pattern 3: Section/div blocks with links
        for item in soup.select(
            ".news-block, .newsBlock, .press-release-item, "
            "article.news, .entry, .post-item"
        ):
            link = item.find("a")
            if not link:
                continue
            date_text = self._find_date_text(item)
            article = self._extract_article_item(link, date_text, base_url)
            if article:
                articles.append(article)

        if articles:
            return articles

        # Fallback: generic link extraction
        return self._generic_link_extraction(soup, base_url)

    def parse_article_body(self, html: str) -> str:
        """Parse athome article page body text."""
        soup = BeautifulSoup(html, "lxml")

        # Try athome-specific article body selectors
        body_selectors = [
            ".news-detail",
            ".newsDetail",
            ".article-content",
            ".articleContent",
            ".entry-content",
            ".entryContent",
            ".press-content",
            ".news-body",
            "article .body",
            "article",
            ".main-content",
            "main",
        ]

        for selector in body_selectors:
            elem = soup.select_one(selector)
            if elem and len(elem.get_text(strip=True)) > 50:
                return self._truncate_body(self._clean_text(elem.get_text(separator=" ")))

        # Fallback
        return self._extract_main_content(soup)

    def _extract_article_item(
        self, link: Tag, date_text: str, base_url: str
    ) -> Optional[dict]:
        """Extract article info from a link element."""
        href = link.get("href", "")
        title = self._clean_text(link.get_text())
        if not title or not href:
            return None
        return {
            "title": self._truncate_title(title),
            "url": self._resolve_url(str(href), base_url),
            "published_at": self._parse_date_text(date_text),
        }

    def _find_date_text(self, elem: Tag) -> str:
        """Find date text within an element."""
        # Check time element
        time_elem = elem.find("time")
        if time_elem:
            datetime_attr = time_elem.get("datetime", "")
            if datetime_attr:
                return str(datetime_attr)
            return time_elem.get_text()

        # Check common date class patterns
        for selector in [
            ".date", ".time", ".news-date", ".newsDate",
            "span.date", "p.date", ".post-date",
        ]:
            date_elem = elem.select_one(selector)
            if date_elem:
                return date_elem.get_text()

        # Search for date pattern in text
        text = elem.get_text()
        match = re.search(r"\d{4}[年./\-]\d{1,2}[月./\-]\d{1,2}日?", text)
        if match:
            return match.group(0)

        return ""

    def _generic_link_extraction(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        """Generic extraction of news-like links."""
        articles: list[dict] = []
        seen_urls: set[str] = set()

        for link in soup.find_all("a", href=True):
            href = str(link["href"])
            if not re.search(
                r"(news|press|release|topics|info)", href, re.IGNORECASE
            ):
                continue
            title = self._clean_text(link.get_text())
            if not title or len(title) < 5:
                continue
            url = self._resolve_url(href, base_url)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            articles.append({
                "title": self._truncate_title(title),
                "url": url,
                "published_at": None,
            })

        return articles

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content as fallback."""
        for tag in soup.find_all(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        best_text = ""
        for elem in soup.find_all(["div", "article", "section", "main"]):
            text = self._clean_text(elem.get_text(separator=" "))
            if len(text) > len(best_text):
                best_text = text

        return self._truncate_body(best_text)


class CanaryPressParser(PressSourceParser):
    """Parser for カナリー (Canary / BluAge Inc.) press release pages.

    Canary press releases are on BluAge corporate site.
    Typical structure: modern SPA-like corporate site with news sections.
    """

    def parse_article_list(self, html: str, base_url: str = "") -> list[dict]:
        """Parse Canary/BluAge corporate news article listing."""
        soup = BeautifulSoup(html, "lxml")
        articles: list[dict] = []

        # Pattern 1: Modern card/list structure
        for item in soup.select(
            ".news-item, .newsItem, .news-card, .newsCard, "
            ".press-item, .pressItem, .post-item, .postItem"
        ):
            link = item.find("a")
            if not link:
                # Sometimes the whole card is wrapped in a link
                parent_link = item.find_parent("a")
                if parent_link:
                    link = parent_link
                else:
                    continue
            date_text = self._find_date_text(item)
            article = self._extract_article(link, item, date_text, base_url)
            if article:
                articles.append(article)

        if articles:
            return articles

        # Pattern 2: List items (ul/ol)
        for item in soup.select(
            ".news-list li, .newsList li, .press-list li, "
            ".topics li, .information li, ul.news li"
        ):
            link = item.find("a")
            if not link:
                continue
            date_text = self._find_date_text(item)
            article = self._extract_article(link, item, date_text, base_url)
            if article:
                articles.append(article)

        if articles:
            return articles

        # Pattern 3: Article/section elements
        for item in soup.select(
            "article, .article, .entry, .post, section.news-item"
        ):
            link = item.find("a")
            if not link:
                continue
            date_text = self._find_date_text(item)
            article = self._extract_article(link, item, date_text, base_url)
            if article:
                articles.append(article)

        if articles:
            return articles

        # Fallback: generic link-based extraction
        return self._fallback_extraction(soup, base_url)

    def parse_article_body(self, html: str) -> str:
        """Parse Canary/BluAge article page body text."""
        soup = BeautifulSoup(html, "lxml")

        # Try various content selectors
        body_selectors = [
            ".news-content",
            ".newsContent",
            ".article-body",
            ".articleBody",
            ".entry-content",
            ".entryContent",
            ".post-content",
            ".postContent",
            ".press-body",
            ".content-area",
            "article .content",
            "article",
            "main .content",
            "main",
        ]

        for selector in body_selectors:
            elem = soup.select_one(selector)
            if elem and len(elem.get_text(strip=True)) > 50:
                return self._truncate_body(self._clean_text(elem.get_text(separator=" ")))

        # Fallback
        return self._extract_largest_block(soup)

    def _extract_article(
        self, link: Tag, container: Tag, date_text: str, base_url: str
    ) -> Optional[dict]:
        """Extract article info from link and its container."""
        href = link.get("href", "")
        # Try to get title from link text, or h2/h3 in container
        title = self._clean_text(link.get_text())
        if not title or len(title) < 3:
            # Try heading within container
            heading = container.find(["h2", "h3", "h4"])
            if heading:
                title = self._clean_text(heading.get_text())
        if not title or not href:
            return None
        return {
            "title": self._truncate_title(title),
            "url": self._resolve_url(str(href), base_url),
            "published_at": self._parse_date_text(date_text),
        }

    def _find_date_text(self, elem: Tag) -> str:
        """Find date text in element."""
        # Check time element
        time_elem = elem.find("time")
        if time_elem:
            datetime_attr = time_elem.get("datetime", "")
            if datetime_attr:
                return str(datetime_attr)
            return time_elem.get_text()

        # Check date-class elements
        for selector in [
            ".date", ".time", ".news-date", ".newsDate",
            "span.date", ".post-date", ".entry-date",
        ]:
            date_elem = elem.select_one(selector)
            if date_elem:
                return date_elem.get_text()

        # Search for date pattern
        text = elem.get_text()
        match = re.search(r"\d{4}[年./\-]\d{1,2}[月./\-]\d{1,2}日?", text)
        if match:
            return match.group(0)

        return ""

    def _fallback_extraction(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        """Fallback extraction using generic link patterns."""
        articles: list[dict] = []
        seen_urls: set[str] = set()

        for link in soup.find_all("a", href=True):
            href = str(link["href"])
            if not re.search(
                r"(news|press|release|topics|info|blog)", href, re.IGNORECASE
            ):
                continue
            title = self._clean_text(link.get_text())
            if not title or len(title) < 5:
                continue
            url = self._resolve_url(href, base_url)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            articles.append({
                "title": self._truncate_title(title),
                "url": url,
                "published_at": None,
            })

        return articles

    def _extract_largest_block(self, soup: BeautifulSoup) -> str:
        """Extract largest text block as fallback."""
        for tag in soup.find_all(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        best_text = ""
        for elem in soup.find_all(["div", "article", "section", "main"]):
            text = self._clean_text(elem.get_text(separator=" "))
            if len(text) > len(best_text):
                best_text = text

        return self._truncate_body(best_text)


class ItandiPressParser(PressSourceParser):
    """Parser for ITANDI (イタンジ) press release pages.

    ITANDI news is on their service site:
    https://service.itandi.co.jp/news

    The site is SPA-based with tab navigation (ITANDI BB, 賃貸管理, etc.).
    Articles have dated entries with links to individual pages.
    """

    def parse_article_list(self, html: str, base_url: str = "") -> list[dict]:
        """Parse ITANDI news article listing.

        Focus on extracting only dated news items, ignoring navigation tabs
        and service description pages.
        """
        soup = BeautifulSoup(html, "lxml")
        articles: list[dict] = []
        seen_urls: set[str] = set()

        # Look for elements with date patterns followed by links
        # ITANDI uses patterns like: "2026.06.18 お知らせ [title]"
        for elem in soup.find_all(["article", "li", "div", "a"]):
            text = elem.get_text()
            # Must have a date pattern to be considered an article
            date_match = re.search(
                r"(\d{4})[./](\d{1,2})[./](\d{1,2})", text
            )
            if not date_match:
                continue

            # Find link in or around this element
            link = None
            if elem.name == "a":
                link = elem
            else:
                link = elem.find("a", href=True)

            if not link:
                continue

            href = str(link.get("href", ""))
            if not href or href.startswith("#") or href == "/":
                continue

            title = self._clean_text(link.get_text())
            if not title or len(title) < 10:
                # Try parent or sibling for a better title
                parent = elem if elem.name != "a" else elem.parent
                if parent:
                    # Extract text after the date
                    full_text = self._clean_text(parent.get_text())
                    # Remove the date prefix to get the title
                    title_match = re.sub(
                        r"^\d{4}[./]\d{1,2}[./]\d{1,2}\s*(プレスリリース|お知らせ|PRESS RELEASE|NEWS)?\s*",
                        "", full_text
                    ).strip()
                    if title_match and len(title_match) > 10:
                        title = title_match[:MAX_TITLE_LENGTH]

            if not title or len(title) < 10:
                continue

            url = self._resolve_url(href, base_url)

            # Skip non-article URLs (same domain service pages)
            if re.search(
                r"/(download|seminar|whitepaper|contact|about)/?$",
                url, re.IGNORECASE
            ):
                continue

            if url in seen_urls:
                continue
            seen_urls.add(url)

            year, month, day = date_match.groups()
            published_at = f"{year}-{int(month):02d}-{int(day):02d}"

            articles.append({
                "title": self._truncate_title(title),
                "url": url,
                "published_at": published_at,
            })

        return articles

    def parse_article_body(self, html: str) -> str:
        """Parse ITANDI article page body text."""
        soup = BeautifulSoup(html, "lxml")

        # Remove non-content elements
        for tag in soup.find_all(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        # Try ITANDI-specific content selectors
        body_selectors = [
            ".news-content",
            ".article-content",
            ".entry-content",
            "article",
            "main .content",
            "main",
        ]

        for selector in body_selectors:
            elem = soup.select_one(selector)
            if elem and len(elem.get_text(strip=True)) > 100:
                return self._truncate_body(self._clean_text(elem.get_text(separator=" ")))

        # Fallback: largest block
        best_text = ""
        for elem in soup.find_all(["div", "article", "section", "main"]):
            text = self._clean_text(elem.get_text(separator=" "))
            if len(text) > len(best_text):
                best_text = text

        return self._truncate_body(best_text)


class GenericPressParser(PressSourceParser):
    """Generic fallback parser using common HTML patterns.

    Uses standard semantic HTML elements (h1/h2, article, main) to extract
    content when no site-specific parser is available.
    """

    def parse_article_list(self, html: str, base_url: str = "") -> list[dict]:
        """Parse article list using generic HTML patterns."""
        soup = BeautifulSoup(html, "lxml")
        articles: list[dict] = []

        # Strategy 1: article elements
        for item in soup.find_all("article"):
            link = item.find("a")
            if not link:
                continue
            date_text = self._find_date_generic(item)
            title = self._clean_text(link.get_text())
            href = link.get("href", "")
            if not title or not href or len(title) < 3:
                # Try heading
                heading = item.find(["h1", "h2", "h3", "h4"])
                if heading:
                    title = self._clean_text(heading.get_text())
                    heading_link = heading.find("a")
                    if heading_link and heading_link.get("href"):
                        href = str(heading_link["href"])
            if title and href:
                articles.append({
                    "title": self._truncate_title(title),
                    "url": self._resolve_url(str(href), base_url),
                    "published_at": self._parse_date_text(date_text),
                })

        if articles:
            return articles

        # Strategy 2: ul/ol list with links
        for item in soup.select("ul li, ol li"):
            link = item.find("a")
            if not link:
                continue
            title = self._clean_text(link.get_text())
            href = link.get("href", "")
            if not title or not href or len(title) < 5:
                continue
            # Filter out navigation links
            if href.startswith("#") or href in ("/", ""):
                continue
            date_text = self._find_date_generic(item)
            articles.append({
                "title": self._truncate_title(title),
                "url": self._resolve_url(str(href), base_url),
                "published_at": self._parse_date_text(date_text),
            })

        if articles:
            return articles

        # Strategy 3: heading + link combinations
        for heading in soup.find_all(["h2", "h3"]):
            link = heading.find("a")
            if not link:
                # Check next sibling for link
                next_elem = heading.find_next_sibling()
                if next_elem:
                    link = next_elem.find("a")
            if not link:
                continue
            title = self._clean_text(heading.get_text())
            href = link.get("href", "")
            if title and href:
                articles.append({
                    "title": self._truncate_title(title),
                    "url": self._resolve_url(str(href), base_url),
                    "published_at": None,
                })

        return articles

    def parse_article_body(self, html: str) -> str:
        """Parse article body using generic HTML patterns."""
        soup = BeautifulSoup(html, "lxml")

        # Remove non-content elements
        for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        # Strategy 1: main element
        main = soup.find("main")
        if main and len(main.get_text(strip=True)) > 50:
            return self._truncate_body(self._clean_text(main.get_text(separator=" ")))

        # Strategy 2: article element
        article = soup.find("article")
        if article and len(article.get_text(strip=True)) > 50:
            return self._truncate_body(self._clean_text(article.get_text(separator=" ")))

        # Strategy 3: content-like div/section
        content_selectors = [
            ".content", ".entry-content", ".article-content",
            ".post-content", ".main-content", "#content", "#main",
        ]
        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem and len(elem.get_text(strip=True)) > 50:
                return self._truncate_body(self._clean_text(elem.get_text(separator=" ")))

        # Strategy 4: largest block element
        best_text = ""
        for elem in soup.find_all(["div", "section"]):
            text = self._clean_text(elem.get_text(separator=" "))
            if len(text) > len(best_text):
                best_text = text

        return self._truncate_body(best_text)

    def _find_date_generic(self, elem: Tag) -> str:
        """Find date using generic patterns."""
        # time element
        time_elem = elem.find("time")
        if time_elem:
            datetime_attr = time_elem.get("datetime", "")
            if datetime_attr:
                return str(datetime_attr)
            return time_elem.get_text()

        # Date class
        date_elem = elem.select_one(".date, .time, [class*=date]")
        if date_elem:
            return date_elem.get_text()

        # Pattern in text
        text = elem.get_text()
        match = re.search(r"\d{4}[年./\-]\d{1,2}[月./\-]\d{1,2}日?", text)
        if match:
            return match.group(0)

        return ""


def get_parser_for_source(source_name: str) -> PressSourceParser:
    """Factory function to get the appropriate parser for a given source.

    Args:
        source_name: Name of the press source (case-insensitive).
                     Matches on prefix/substring (e.g., "suumo-press" → SuumoPressParser).

    Returns:
        A parser instance for the source, or GenericPressParser if no
        specific parser is available.
    """
    name_lower = source_name.lower()

    # Match by prefix/substring to handle names like "suumo-press", "suumo-data"
    if "suumo" in name_lower:
        return SuumoPressParser()
    if "athome" in name_lower:
        return AthomePressParser()
    if "canary" in name_lower or "bluage" in name_lower:
        return CanaryPressParser()
    if "itandi" in name_lower:
        return ItandiPressParser()

    return GenericPressParser()
