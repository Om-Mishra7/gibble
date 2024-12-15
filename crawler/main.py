import uuid
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from database import Database

class GibbleCrawler:
    def __init__(self):
        self.db = Database()
        self.db.ensure_connection()

        self.base_crawl_url = ["https://en.wikipedia.org/wiki/Main_Page"]
        self.db.insert_url(self.base_crawl_url)

        self.disallowed_extensions = [
            ".jpg", ".png", ".gif", ".svg", ".pdf", ".doc", ".zip", ".exe", ".tar.gz"
        ]

        self.stats = {
            "crawl_session_id": str(uuid.uuid4()),
            "total_urls_crawled": 0,
            "total_urls_failed": 0,
            "total_urls_skipped": 0,
            "total_urls_queued": 0,
            "total_urls": 0
        }

    def crawl(self, url):
        """Crawl a single URL and extract information."""
        self.stats["total_urls"] += 1

        try:
            response = self._fetch_url(url)
            if not response:
                return

            soup = BeautifulSoup(response.content, 'html.parser')
            canonical_url = response.url

            # Extract metadata and content
            parsed_page = self._parse_page(soup, canonical_url)
            outbound_links = self._extract_outbound_links(soup, url)

            # Insert into the database
            self.db.insert_page(canonical_url, parsed_page)

            self.stats["total_urls_crawled"] += 1

        except Exception as error:
            self.stats["total_urls_failed"] += 1

    def _fetch_url(self, url):
        """Fetch the content of a URL."""
        try:
            response = requests.get(
                url,
                timeout=5,
                allow_redirects=True,
                headers={'User-Agent': 'GibbleCrawler v0.3'}
            )

            if response.status_code != 200:
                self.stats["total_urls_failed"] += 1
                return None

            return response
        except requests.exceptions.RequestException:
            self.stats["total_urls_failed"] += 1
            return None

    def _parse_page(self, soup, canonical_url):
        """Extract page metadata and content."""
        page_title = soup.title.string if soup.title else "No title"
        page_description = soup.find("meta", property="og:description")
        page_description = page_description["content"] if page_description else "No description"
        page_outbound_links = self._extract_outbound_links(soup, canonical_url)

        return {
            "page_metadata": {
                "canonical_url": canonical_url,
                "page_title": page_title,
                "page_description": page_description
            },
            "page_content": {
                "page_text": soup.get_text().strip(),
                "page_outbound_links": page_outbound_links
            }
        }

    def _extract_outbound_links(self, soup, base_url):
        """Extract and normalize outbound links from a page."""
        links = set()

        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if not href or href.startswith('#'):
                continue

            # Normalize relative URLs
            full_url = urljoin(base_url, href)

            # Skip URLs with disallowed extensions
            if any(full_url.lower().endswith(ext) for ext in self.disallowed_extensions):
                self.stats["total_urls_skipped"] += 1
                continue

            # Validate URL structure
            parsed_url = urlparse(full_url)
            if parsed_url.scheme not in ('http', 'https'):
                self.stats["total_urls_skipped"] += 1
                continue

            links.add(full_url)

        self.stats["total_urls_queued"] += len(links)
        return list(links)

    def _display_stats(self):
        """Continuously display crawler statistics."""
        # Clear the screen
        print("\033[H\033[J")
        print("\nCrawler Statistics:")
        print(f"Session ID: {self.stats['crawl_session_id']}")
        print(f"Total URLs Crawled: {self.stats['total_urls_crawled']}")
        print(f"Total URLs Failed: {self.stats['total_urls_failed']}")
        print(f"Total URLs Skipped: {self.stats['total_urls_skipped']}")
        print(f"Total URLs Queued: {self.stats['total_urls_queued']}")
        print(f"Total URLs Processed: {self.stats['total_urls']}")
        

    def run(self):
        """Start the crawling process."""
        while True:
            url_to_crawl = self.db.get_next_url()
            if not url_to_crawl:
                print("URL queue exhausted, crawler shutting down.")
                break

            self.crawl(url_to_crawl)
            self._display_stats()

# Ensure you have the Database class code present above for this to integrate correctly.

if __name__ == "__main__":
    crawler = GibbleCrawler()
    crawler.run()