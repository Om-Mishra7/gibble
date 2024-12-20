import os
import logging
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
import re
import json
import string


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
            self.construct_schema()
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

    def construct_schema(self):
        """Create the database schema if it doesn't already exist."""
        try:
            with self.connection.cursor() as cursor:
                # Drop the tables if they already exist                
                # cursor.execute("DROP TABLE IF EXISTS reverse_index;")

                # cursor.execute("UPDATE pages SET indexed = FALSE;")

                # self.connection.commit()

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reverse_index (
                        word TEXT PRIMARY KEY,
                        urls JSONB
                    );
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE pages ADD COLUMN IF NOT EXISTS indexed BOOLEAN DEFAULT FALSE;
                    """
                )
                self.connection.commit()
                self.logger.info("Schema construction completed.")
        except Exception as error:
            self.logger.error(f"Error creating schema: {error}")
            self.connection.rollback()

    def get_number_of_pages(self):
        """Get the total number of pages."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM pages;")
                return cursor.fetchone()[0]
        except Exception as error:
            self.logger.error(f"Error fetching number of pages: {error}")
            self.connection.rollback()
            return 0

    def get_page_to_index(self):
        """Fetch the next uncrawled URL."""
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT url, content FROM pages
                    WHERE indexed = FALSE
                    LIMIT 1;
                    """
                )
                page = cursor.fetchone()
                return page["url"], page["content"] if page else (None, None)
        except Exception as error:
            self.logger.error(f"Error fetching page: {error}")
            self.connection.rollback()
            return None, None

    def insert_index(self, url, words):
        """Insert the index into the database."""
        try:
            with self.connection.cursor() as cursor:
                for word in words:
                    cursor.execute(
                        """
                        INSERT INTO reverse_index (word, urls)
                        VALUES (%s, %s)
                        ON CONFLICT (word) DO UPDATE
                        SET urls = reverse_index.urls || %s;
                        """,
                        (word, json.dumps([url]), json.dumps([url])),
                    )
                self.connection.commit()
                self.logger.info(f"Index for {url} inserted successfully.")
        except Exception as error:
            self.logger.error(f"Error inserting index: {error}")
            self.connection.rollback()

    def mark_page_indexed(self, url):
        """Mark the page as indexed."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("UPDATE pages SET indexed = TRUE WHERE url = %s;", (url,))
                self.connection.commit()
                self.logger.info(f"Page {url} marked as indexed.")
        except Exception as error:
            self.logger.error(f"Error marking page as indexed: {error}")
            self.connection.rollback()

    def __del__(self):
        if self.connection:
            self.connection.close()
            self.logger.info("Database connection closed.")


class Indexer:
    def __init__(self):
        self.db = Database()
        self.db.ensure_connection()

        self.analytics = {
            "number_of_pages": self.db.get_number_of_pages(),
            "pages_indexed": 0,
            "words_indexed": 0
        }

    def index_page(self, url, content):
        """Index words longer than 3 characters from the page content."""
        content = content["page_text"]

        words = content.split()
        words = [word.lower().strip(string.punctuation + string.whitespace) for word in words]

        # Remove common words using a set for faster lookups
        common_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'about', 'above', 'after', 'along',
            'amid', 'among', 'as', 'at', 'by', 'for', 'from', 'in', 'into', 'like',
            'minus', 'near', 'of', 'off', 'on', 'onto', 'out', 'over', 'past', 'per',
            'plus', 'since', 'till', 'to', 'under', 'until', 'up', 'via', 'vs', 'with',
            'that', 'can', 'cannot', 'could', 'may', 'might', 'must', 'need', 'ought',
            'shall', 'should', 'will', 'would', 'have', 'had', 'has', 'having', 'be',
            'is', 'am', 'are', 'was', 'were', 'being', 'been', 'get', 'gets', 'got',
            'gotten', 'getting', 'use', 'uses', 'used', 'using', 'one', 'two', 'three',
            'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'first', 'second',
            'third', 'many', 'much', 'more', 'most', 'other', 'another'
        }

        # Remove all non-english words

        words = [word for word in words if re.fullmatch(r'[a-zA-Z]+', word)]

        words = [word for word in words if word not in common_words and len(word) > 3]

        self.analytics['words_indexed'] += len(words)

        self.db.insert_index(url, list(set(words)))

    def run(self):
        while True:
            url, content = self.db.get_page_to_index()
            if url is None:
                print("No more pages to index.")
                break

            self.index_page(url, content)
            self.db.mark_page_indexed(url)

            self.analytics['pages_indexed'] += 1

            print("\033[H\033[J")
            print("\nIndexer Statistics:")
            print(f"Pages to index: {self.analytics['number_of_pages']}")
            print(f"Pages indexed: {self.analytics['pages_indexed']}")
            print(f"Words indexed: {self.analytics['words_indexed']}")
            print(f"Percentage complete: {self.analytics['pages_indexed'] / self.analytics['number_of_pages'] * 100:.2f}%")


if __name__ == "__main__":
    indexer = Indexer()
    indexer.run()
