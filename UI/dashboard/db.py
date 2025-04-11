import requests
import json
import dotenv
import os
import psycopg
from datetime import datetime

dotenv.load_dotenv()
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PWD = os.getenv("DB_PWD")
DB_PORT = os.getenv("DB_PORT")

# Use psycopg3's modern connection and context management
connection_string = f"postgresql://{DB_USER}:{DB_PWD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def normalize_date(date_str):
    if len(date_str) == 4:  # %Y
        return f"{date_str}-01-01"
    elif len(date_str) == 7:  # %Y-%M
        return f"{date_str}-01"
    return date_str  # %Y-%M-%D


def get_publications(start_date, end_date, genres):
  missing_genres = set(["OTHERS", "BOOK_ITEM", "CONFERENCE_PAPER", "ARTICLE"]) - set(genres)

  str_start_date = start_date.strftime("%Y-%m-%d")
  str_end_date = end_date.strftime("%Y-%m-%d")

  str_end_date = normalize_date(str_end_date)
  str_start_date = normalize_date(str_start_date)

  sql_query = None

  if "OTHERS" in genres:
    sql_query = """
    SELECT object_id, date
    FROM publications
    WHERE (
        -- Exact match for YYYY-MM-DD format
        (LENGTH(date) = 10 AND DATE(date) >= %s AND DATE(date) < %s
    ) OR (
        -- Match for YYYY-MM format
        LENGTH(date) = 7 AND DATE(date || '-01') >= %s AND DATE(date || '-01') < %s
    ) OR (
        -- Match for YYYY format
        LENGTH(date) = 4 AND DATE(date || '-01-01') >= %s AND DATE(date || '-01-01') < %s
    )) AND NOT (genre = ANY(%s));
    """
  else:
    missing_genres = set(genres)
    sql_query = """
    SELECT object_id, date
    FROM publications
    WHERE (
        -- Exact match for YYYY-MM-DD format
        (LENGTH(date) = 10 AND DATE(date) >= %s AND DATE(date) < %s
    ) OR (
        -- Match for YYYY-MM format
        LENGTH(date) = 7 AND DATE(date || '-01') >= %s AND DATE(date || '-01') < %s
    ) OR (
        -- Match for YYYY format
        LENGTH(date) = 4 AND DATE(date || '-01-01') >= %s AND DATE(date || '-01-01') < %s
    )) AND genre = ANY(%s);
    """


  with psycopg.connect(connection_string) as conn:
      with conn.cursor() as cursor:
          cursor.execute(sql_query, (str_start_date, str_end_date, str_start_date, str_end_date, str_start_date, str_end_date, [list(missing_genres)]))          # Fetch column names and data in one go
          data = cursor.fetchall()
  return data


def get_oa_publications(start_date, end_date, open_access, genres):
  str_start_date = start_date.strftime("%Y-%m-%d")
  str_end_date = end_date.strftime("%Y-%m-%d")
  missing_genres = set(["OTHERS", "BOOK_ITEM", "CONFERENCE_PAPER", "ARTICLE"]) - set(genres)

  str_end_date = normalize_date(str_end_date)
  str_start_date = normalize_date(str_start_date)

  if "OTHERS" in genres:
    sql_query = """
    SELECT object_id, date, open_access
    FROM publications
    WHERE (
        -- Exact match for YYYY-MM-DD format
        (LENGTH(date) = 10 AND DATE(date) >= %s AND DATE(date) < %s)
        OR
        -- Match for YYYY-MM format
        (LENGTH(date) = 7 AND DATE(date || '-01') >= %s AND DATE(date || '-01') < %s)
        OR
        -- Match for YYYY format
        (LENGTH(date) = 4 AND DATE(date || '-01-01') >= %s AND DATE(date || '-01-01') < %s)
    )
    AND open_access = %s AND NOT (genre = ANY(%s));
    """
  else:
    missing_genres = set(genres)
    sql_query = """
    SELECT object_id, date, open_access
    FROM publications
    WHERE (
        -- Exact match for YYYY-MM-DD format
        (LENGTH(date) = 10 AND DATE(date) >= %s AND DATE(date) < %s)
        OR
        -- Match for YYYY-MM format
        (LENGTH(date) = 7 AND DATE(date || '-01') >= %s AND DATE(date || '-01') < %s)
        OR
        -- Match for YYYY format
        (LENGTH(date) = 4 AND DATE(date || '-01-01') >= %s AND DATE(date || '-01-01') < %s)
    )
    AND open_access = %s AND genre = ANY(%s);
    """

  with psycopg.connect(connection_string) as conn:
      with conn.cursor() as cursor:
          cursor.execute(sql_query, (str_start_date, str_end_date, str_start_date, str_end_date, str_start_date, str_end_date, open_access,  [list(missing_genres)]))          # Fetch column names and data in one go
          columns = [desc.name for desc in cursor.description]
          data = cursor.fetchall()
  return data

def extract_month_year(date_str):
    try:
        # Parse full dates
        date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        try:
            # Parse "YYYY-MM" format
            date = datetime.strptime(date_str, '%Y-%m')
        except ValueError:
            try:
                # Parse "YYYY" format
                date = datetime.strptime(date_str, '%Y')
            except ValueError:
                return None  # Handle invalid formats
    return date.strftime('%Y-%m')
  
