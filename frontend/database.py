import os
import logging
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
import heapq


class Database:
    def __init__(self):
        load_dotenv()
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

        try:
            self.connection = self.get_connection(
                os.getenv("DB_NAME"),
                os.getenv("DB_HOST"),
                os.getenv("DB_PASSWORD"),
                os.getenv("DB_PORT"),
                os.getenv("DB_USER"),
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize the database: {e}")
            self.connection = None

    def get_connection(self, db_name, db_host, db_password, db_port, db_user):
        if not all([db_name, db_host, db_password, db_port, db_user]):
            raise ValueError("One or more required environment variables are missing.")
        try:
            connection = psycopg2.connect(
                dbname=db_name,
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port,
            )
            self.logger.info("Database connection successful.")
            return connection
        except Exception as error:
            self.logger.error(f"Error connecting to the database: {error}")
            raise error

    def ensure_connection(self):
        try:
            self.connection.cursor().execute("SELECT 1")
        except (Exception, psycopg2.OperationalError):
            self.logger.warning("Reconnecting to the database...")
            self.connection = self.get_connection(
                os.getenv("DB_NAME"),
                os.getenv("DB_HOST"),
                os.getenv("DB_PASSWORD"),
                os.getenv("DB_PORT"),
                os.getenv("DB_USER"),
            )

    def search(self, query):
        self.ensure_connection()
        query_words = [word.lower().strip() for word in query.split()]  # Normalize query words
        url_scores = {}

        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Step 1: Exact match search
                for word in query_words:
                    cursor.execute("""
                        SELECT urls FROM reverse_index WHERE word = %s;
                    """, (word,))
                    result = cursor.fetchone()
                    if result and result['urls']:
                        urls = result['urls']
                        for url in urls:
                            url_scores[url] = url_scores.get(url, 0) + 1

                # Step 2: Partial match search
                for word in query_words:
                    cursor.execute("""
                        SELECT word, urls FROM reverse_index WHERE word LIKE %s LIMIT 100;
                    """, (f"%{word}%",))  # Limit the results for partial match
                    results = cursor.fetchall()
                    for row in results:
                        urls = row['urls']
                        for url in urls:
                            url_scores[url] = url_scores.get(url, 0) + 0.5  # Partial matches get lower weight

                # Step 3: Sort URLs by score in descending order (only take top 100)
                sorted_urls = heapq.nlargest(100, url_scores.items(), key=lambda x: x[1])

                # Step 4: Fetch titles and descriptions for top URLs
                result_array = []

                for url, score in sorted_urls:
                    cursor.execute("""
                        SELECT metadata->>'page_title' as title, metadata->>'page_description' as description
                        FROM pages WHERE url = %s;
                    """, (url,))
                    page = cursor.fetchone()
                    if page:
                        result_array.append({
                            "url": url,
                            "title": page['title'] if page['title'] else "No Title",
                            "description": page['description'] if page['description'] else "No Description",
                            "score": score
                        })

                return result_array
        except Exception as error:
            self.logger.error(f"Error during search: {error}")
            return []