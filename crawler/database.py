import os
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
import json
from datetime import datetime

class Database:
    def __init__(self):
        load_dotenv()
        self.connection = self.get_connection(
            os.getenv('DB_NAME'),
            os.getenv('DB_HOST'),
            os.getenv('DB_PASSWORD'),
            os.getenv('DB_PORT'),
            os.getenv('DB_USER')
        )
        self.construct_schema()

    def get_connection(self, db_name, db_host, db_password, db_port, db_user):
        try:
            connection = psycopg2.connect(
                dbname=db_name,
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port
            )
            print("Database connection successful.")
            return connection
        except Exception as error:
            print(f"Error connecting to the database: {error}")
            raise error

    def ensure_connection(self):
        try:
            self.connection.cursor().execute("SELECT 1")
        except (Exception, psycopg2.OperationalError):
            print("Reconnecting to the database...")
            self.connection = self.get_connection(
                os.getenv('DB_NAME'),
                os.getenv('DB_HOST'),
                os.getenv('DB_PASSWORD'),
                os.getenv('DB_PORT'),
                os.getenv('DB_USER')
            )

    def construct_schema(self):
        """Create the database schema if it doesn't already exist."""
        try:
            with self.connection.cursor() as cursor:

                # # Drop tables if they exist

                # cursor.execute("""
                # DROP TABLE IF EXISTS urls, pages;
                # """)

                # # Commit the changes
                # self.connection.commit()

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS urls (
                    id SERIAL PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    crawled BOOLEAN DEFAULT FALSE,
                    added_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS pages (
                    id SERIAL PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    metadata JSONB,
                    content JSONB,
                    added_at TIMESTAMP DEFAULT NOW()
                );
                """)
                self.connection.commit()
        except Exception as error:
            print(f"Error creating schema: {error}")
            self.connection.rollback()

    def insert_url(self, urls):
        """Insert a list of URLs into the queue."""
        try:
            with self.connection.cursor() as cursor:
                for url in urls:
                    cursor.execute("""
                    INSERT INTO urls (url) 
                    VALUES (%s) 
                    ON CONFLICT (url) DO NOTHING;
                    """, (url,))
                self.connection.commit()
        except Exception as error:
            print(f"Error inserting URLs: {error}")
            self.connection.rollback()

    def get_next_url(self):
        """Fetch the next uncrawled URL."""
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                SELECT url FROM urls WHERE crawled = FALSE LIMIT 1;
                """)
                row = cursor.fetchone()
                if row:
                    cursor.execute("""
                    UPDATE urls SET crawled = TRUE WHERE url = %s;
                    """, (row['url'],))
                    self.connection.commit()
                    return row['url']
                return None
        except Exception as error:
            print(f"Error fetching next URL: {error}")
            self.connection.rollback()
            return None

    def insert_page(self, url, page_data):
        """Insert crawled page data into the database."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                INSERT INTO pages (url, metadata, content) 
                VALUES (%s, %s, %s)
                ON CONFLICT (url) DO NOTHING;
                """, (url, json.dumps(page_data['page_metadata']), json.dumps(page_data['page_content'])))
                self.connection.commit()
        except Exception as error:
            print(f"Error inserting page: {error}")
            self.connection.rollback()

    def insert_outbound_links(self, links):
        """Insert outbound links into the URL queue."""
        self.insert_url(links)
