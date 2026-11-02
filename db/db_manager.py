import os

import dotenv
from psycopg import DatabaseError, connect
from psycopg.rows import dict_row

# Load environment variables from .env file
dotenv.load_dotenv()


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.DB_HOST = os.getenv('DB_HOST')
        self.DB_NAME = os.getenv('DB_NAME')
        self.DB_USER = os.getenv('DB_USER')
        self.DB_PWD = os.getenv('DB_PWD')
        self.DB_PORT = os.getenv('DB_PORT')

    def connect(self):
        try:
            self.connection = connect(
                dbname=self.DB_NAME,
                user=self.DB_USER,
                password=self.DB_PWD,
                host=self.DB_HOST,
                port=self.DB_PORT,
                autocommit=True,
                row_factory=dict_row,  # <-- returns dicts instead of tuples
            )
            self.cursor = self.connection.cursor()
            print('    Connected to the database')

        except DatabaseError as error:
            print(f'    Unable to connect to database: {error}')

    def add_publication(self, publication):
        sql_string = """
            INSERT INTO publications (
                pure_title, openalex_title, pure_id, openalex_id, doi, pure_oa_status, openalex_oa_status,
                openalex_oa, manual_download, discoverable, pure_genre, openalex_type, crossref_type,
                publication_year, publication_date, publisher
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        self.cursor.execute(
            sql_string,
            (
                publication['pure_title'],
                publication['openalex_title'],
                publication['pure_id'],
                publication['openalex_id'],
                publication['doi'],
                publication['pure_oa_status'],
                publication['openalex_oa_status'],
                publication['openalex_oa'],
                publication['manual_download'],
                publication['discoverable'],
                publication['pure_genre'],
                publication['openalex_type'],
                publication['crossref_type'],
                publication['publication_year'],
                publication['publication_date'],
                publication['publisher'],
            ),
        )
        return publication['pure_id']

    def add_pdf_url(
        self,
        pdf_url_id,
        pure_id,
        pdf_url,
        locator_url,
        pure_content_category,
        openalex_version,
        pure_oa_status,
        openalex_oa,
        url_source,
    ):
        self.cursor.execute(
            'INSERT INTO publication_pdf_urls (pdf_url_id, pure_id, pdf_url, locator_url, pure_content_category, '
            'openalex_version, pure_oa_status, openalex_oa, url_source) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (
                pdf_url_id,
                pure_id,
                pdf_url,
                locator_url,
                pure_content_category,
                openalex_version,
                pure_oa_status,
                openalex_oa,
                url_source,
            ),
        )

    def delete_pdf_urls_by_id(self, publication_id):
        self.cursor.execute('DELETE FROM publication_pdf_urls WHERE pure_id = %s', (publication_id,))

    def put_data_sharing_status(self, publication_id, data_mentioned, data_shared):
        self.cursor.execute(
            'UPDATE publications SET data_mentioned = %s, data_shared = %s WHERE pure_id = %s',
            (data_mentioned, data_shared, publication_id),
        )

    def put_software_sharing_status(self, publication_id, software_used, software_shared, software_created):
        self.cursor.execute(
            'UPDATE publications SET software_used = %s, software_shared = %s, software_created = %s '
            'WHERE pure_id = %s',
            (software_used, software_shared, software_created, publication_id),
        )

    def check_publication_exists(self, doi):
        self.cursor.execute('SELECT 1 FROM publications WHERE doi = %s', (doi,))
        return self.cursor.fetchone() is not None

    def check_publication_exists_by_name_and_year(self, pure_id):
        self.cursor.execute('SELECT 1 FROM publications WHERE pure_id = %s', (pure_id,))
        return self.cursor.fetchone() is not None

    def get_urls_by_publication_id(self, publication_id):
        self.cursor.execute('SELECT pdf_url FROM publication_pdf_urls WHERE pure_id = %s', (publication_id,))
        list_of_dicts = self.cursor.fetchall()  # returns list of dicts with 'pdf_url' keys

        return [d.get('pdf_link') for d in list_of_dicts]

    def get_unevaluated_papers_publication_year(self, publication_year):
        self.cursor.execute('SELECT * FROM publications WHERE year = %s AND open_data IS NULL', (publication_year,))
        return self.cursor.fetchall()  # returns list of dicts

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            print('    Database connection closed')
