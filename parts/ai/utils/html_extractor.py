# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re
import requests
import unicodedata
from lxml import html

from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

from odoo.tools.urls import urljoin

_logger = logging.getLogger(__name__)


class HTMLExtractor:
    """
    Extracts text content from HTML sources (URLs or HTML strings) as a series of paragraphs,
    simplifying the hierarchical structure into a clean text format.
    """

    def __init__(self, env, internal_domains=None):
        self.env = env
        # Define non-content XPaths to exclude
        self.exclude_xpath = [
            "//script", "//style", "//noscript", "//iframe", "//comment()",
            "//*[contains(@style, 'display:none') or contains(@style, 'visibility:hidden')]"
        ]

        # semantic layout elements
        self.exclude_xpath += [
            "//nav", "//footer", "//header", "//aside",
            "//*[@role='navigation' or @role='banner' or @role='contentinfo']",
            "//*[contains(@id, 'footer') or contains(@id, 'header') or @id='top' or @id='bottom']"
        ]

        # layout classes
        layout_keywords = ["menu", "footer", "header", "nav", "sidebar", "breadcrumb", "modal", "popup"]
        class_filter = " or ".join(f"contains(@class, '{k}')" for k in layout_keywords)
        self.exclude_xpath.append(f"//*[{class_filter}]")

        # odoo-website specific unnecessary elements
        odoo_ui_classes = ["o_mega_menu", "o_not_editable", "o_search", "js_language_selector", "s_cookie_bar", "o_livechat_button", "o_newsletter_popup"]
        odoo_ui_class_filter = " or ".join(f"contains(@class, '{c}')" for c in odoo_ui_classes)
        self.exclude_xpath.append(f"//*[{odoo_ui_class_filter}]")
        self.internal_domains = internal_domains
        self.__robots_cache = {}

    def scrap(self, url):
        """
        Scrape a webpage and extract text content.
        Args:
            url (str): The URL to scrape
        Returns:
            dict: Dictionary with 'content' and 'title' keys, or None if scraping fails
        """
        html_content, error_message = self._fetch_url(url)
        if not html_content:
            return {"content": None, "title": None, "error": error_message}

        parser = html.HTMLParser(remove_blank_text=True, remove_comments=True, remove_pis=True)
        tree = html.fromstring(html_content, parser=parser)

        # Extract metadata
        title = self._get_title(tree)

        # Clean HTML tree
        self._clean_html_tree(tree)

        # Extract content as paragraphs
        content = self._extract_content(tree)
        if not content:
            return {"content": None, "title": None, "error": "No extractable content found on the page."}

        return {"content": content, "title": title, "error": None}

    def extract_from_html(self, html_content):
        """
        Extract text content from HTML string (e.g., from a knowledge HTML field body).
        Args:
            html_content (str): The HTML content as a string
            title (str, optional): Optional title for the content
        Returns:
            dict: Dictionary with 'content' and 'title' keys
        """
        if not html_content:
            return {"content": ""}

        # Wrap content in a proper HTML structure to ensure _clean_html_tree works correctly
        wrapped_html = f"<html><body>{html_content}</body></html>"
        parser = html.HTMLParser(remove_blank_text=True, remove_comments=True, remove_pis=True)
        tree = html.fromstring(wrapped_html, parser=parser)

        # Clean HTML tree
        self._clean_html_tree(tree)

        # Extract content as paragraphs
        content = self._extract_content(tree)

        return {"content": content}

    def _is_internal_domain(self, url):
        """
        Check if the URL is of an internal domain.
        :param url: The URL to check
        :type url: str
        :return: True if the URL is of an internal domain, False otherwise
        :rtype: bool
        """
        if not self.internal_domains or not url:
            return False

        url_hostname = urlparse(url).hostname
        if not url_hostname:
            return False

        # Standardize to punycode (IDNA) for matching international domains
        try:
            url_hostname = url_hostname.encode('idna').decode('ascii').lower()
        except (UnicodeError, Exception):
            url_hostname = url_hostname.lower()

        for candidate in self.internal_domains:
            if url_hostname == candidate or url_hostname.endswith('.' + candidate):
                return True
        return False

    def _allowed_by_robots(self, url, user_agent="Odoobot/1.0"):
        """
        Check if URL is allowed via robots.txt with caching and specific error handling.
        :param url: The URL to check
        :type url: str
        :param user_agent: The user agent to use
        :type user_agent: str
        :return: True if the URL is allowed, False otherwise
        :rtype: bool
        """
        if self._is_internal_domain(url):
            return True

        parsed = urlparse(url)
        # Ensure we only check robots.txt for the root of the domain
        robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")

        if robots_url not in self.__robots_cache:
            rp = RobotFileParser()
            try:
                response = requests.get(robots_url, timeout=5)
                response.raise_for_status()

                rp.parse(response.text.splitlines())
                self.__robots_cache[robots_url] = rp
            except requests.exceptions.RequestException as e:
                response = getattr(e, 'response', None)
                if response and response.status_code == 404:
                    self.__robots_cache[robots_url] = None
                _logger.warning("Defaulting to ALLOW: Robots.txt unreachable at %s: %s", robots_url, e)
                return True

        cached_rp = self.__robots_cache.get(robots_url)
        return cached_rp.can_fetch(user_agent, url) if cached_rp else True

    def _fetch_url(self, url):
        """Fetch URL content"""
        try:
            if not self._allowed_by_robots(url):
                error_msg = self.env._("The site's rules (robots.txt) prevent reading this page.")
                _logger.info(error_msg)
                return None, error_msg

            headers = {
                "User-Agent": "Odoobot/1.0 (+https://www.odoo.com)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # Check content type to ensure we're dealing with HTML
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
                error_msg = self.env._("URL %(url)s returned non-HTML content: %(content_type)s") % {'url': url, 'content_type': content_type}
                _logger.warning(error_msg)
                return None, error_msg

            if not response.content:
                error_msg = self.env._("URL %s returned empty content") % url
                _logger.warning(error_msg)
                return None, error_msg

            return response.content, None
        except requests.exceptions.RequestException as e:
            error_msg = self.env._("Failed to fetch URL: %s") % e
            _logger.warning(error_msg)
            return None, error_msg

    def _get_title(self, tree):
        """Extract page title."""
        titles = tree.xpath("//title/text()")
        if titles:
            return titles[0].strip()
        return ""

    def _clean_html_tree(self, tree):
        """Clean HTML by removing unwanted elements."""
        # Identify content containers to avoid deleting them or their ancestors
        content_container_xpath = "//main|//article|//*[@id='wrap']|//*[@id='main']|//*[@id='product_details']|//*[hasclass('o_wblog_post_content_field')]|//div[@role='main']|//div[@id='content']|//div[@class='content']"
        protected_nodes = tree.xpath(content_container_xpath)

        # Remove unwanted elements
        for xpath in self.exclude_xpath:
            for element in tree.xpath(xpath):
                # Never remove an element that is or contains a protected content container
                if any(p == element or element in p.iterancestors() for p in protected_nodes):
                    continue

                if element.getparent() is not None:
                    element.getparent().remove(element)

    def _extract_content(self, tree):
        """
        Extract content as a series of paragraphs
        """
        main_content = tree.xpath("//main|//article|//*[@id='wrap']|//*[@id='main']|//*[@id='product_details']|//*[hasclass('o_wblog_post_content_field')]|//div[@role='main']|//div[@id='content']|//div[@class='content']")
        if not main_content:
            main_content = tree.xpath("//body")
            if not main_content:
                _logger.warning("Could not find any content container in the HTML")
                return ""

        paragraphs = []

        current_heading = None
        current_paragraph_parts = []

        for element in main_content[0].xpath(".//*"):
            tag = element.tag

            # Check if this is a heading element
            if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # If we have a previous heading, add it (with or without content)
                if current_heading:
                    if current_paragraph_parts:
                        paragraph = f"{current_heading}. {' '.join(current_paragraph_parts)}"
                    else:
                        paragraph = current_heading
                    paragraphs.append(paragraph)
                    current_paragraph_parts = []

                # Set the new heading
                heading_text = self._get_element_text(element)
                if heading_text:
                    current_heading = self._normalize_text(heading_text)

            # Process paragraph content
            elif tag == 'p':
                text = self._get_element_text(element)
                if text:
                    text = self._normalize_text(text)
                    if current_heading:
                        current_paragraph_parts.append(text)
                    else:
                        # No heading, add as standalone paragraph
                        paragraphs.append(text)

            # Process unordered lists
            elif tag == 'ul':
                # Skip navigation and menu lists
                if any(cls in (element.get("class", "") or "").lower() for cls in ["menu", "nav", "navigation"]):
                    continue

                list_items = []
                for li in element.xpath("./li"):
                    item_text = self._get_element_text(li)
                    if item_text:
                        list_items.append(f"• {item_text}")

                if list_items:
                    list_text = " ".join(list_items)
                    if current_heading:
                        current_paragraph_parts.append(list_text)
                    else:
                        paragraphs.append(list_text)

            # Process ordered lists
            elif tag == 'ol':
                list_items = []
                for i, li in enumerate(element.xpath("./li")):
                    item_text = self._get_element_text(li)
                    if item_text:
                        list_items.append(f"{i + 1}. {item_text}")

                if list_items:
                    list_text = " ".join(list_items)
                    if current_heading:
                        current_paragraph_parts.append(list_text)
                    else:
                        paragraphs.append(list_text)

            # Process tables
            elif tag == 'table':
                # Skip layout tables
                if element.get("role") == "presentation":
                    continue

                table_text = self._process_table_as_text(element)
                if table_text:
                    if current_heading:
                        current_paragraph_parts.append(table_text)
                    else:
                        paragraphs.append(table_text)

            # Process div and span elements with direct text
            elif tag in ['div', 'span'] and element.xpath(".//text()") and not element.xpath("./p"):
                # Check if this element directly contains text (not just in its children)
                direct_text = "".join(t.strip() for t in element.xpath("./text()") if t.strip())

                if direct_text:
                    text = self._normalize_text(direct_text)
                    if current_heading:
                        current_paragraph_parts.append(text)
                    else:
                        paragraphs.append(text)

        if current_heading:
            if current_paragraph_parts:
                paragraph = f"{current_heading}. {' '.join(current_paragraph_parts)}"
            else:
                paragraph = current_heading
            paragraphs.append(paragraph)

        return "\n\n".join(p.strip() for p in paragraphs if p.strip())

    def _process_table_as_text(self, table):
        """Process a table element and return its text content."""

        captions = table.xpath("./caption")
        caption_text = self._get_element_text(captions[0]) if captions else ""

        # Process table headers
        headers = []
        for th in table.xpath(".//th"):
            text = self._get_element_text(th)
            headers.append(text if text else "")

        # Process table rows
        table_rows = []
        for tr in table.xpath(".//tr[td]"):
            row_data = []
            for td in tr.xpath("./td"):
                text = self._get_element_text(td)
                row_data.append(text if text else "")

            if row_data:
                table_rows.append(" | ".join(row_data))

        # Combine table content
        table_content = []
        if caption_text:
            table_content.append(caption_text + ":")

        if headers:
            table_content.append(" | ".join(headers))

        table_content.extend(table_rows)

        return " ".join(table_content)

    def _get_element_text(self, element):
        """Get text content from an element, preserving whitespace where appropriate."""
        if element is None:
            return ""

        # Get all text nodes
        texts = []
        for t in element.xpath(".//text()"):
            if t.is_text:
                parent = t.getparent()
                if parent is not None and parent.tag in ["pre", "code"]:
                    # Preserve whitespace in pre/code blocks
                    texts.append(t)
                else:
                    # Normalize whitespace in regular text
                    texts.append(t.strip())

        return " ".join(t for t in texts if t)

    def _normalize_text(self, text):
        """Normalize text by handling whitespace, unicode, and other issues."""
        if not text:
            return ""
        # Normalize unicode characters
        text = unicodedata.normalize("NFKC", text)
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text)
        # Remove excessive newlines
        text = re.sub(r'\n+', ' ', text)
        # Remove control characters and special characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        # Remove HTML tags
        text = re.sub(r'[<>{}[\]\\]', '', text)
        return text.strip()
