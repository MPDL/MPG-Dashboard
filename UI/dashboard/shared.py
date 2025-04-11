from pathlib import Path
import psycopg2
import os 
import dotenv
import pandas as pd
import numpy as np

dotenv.load_dotenv()
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PWD = os.getenv("DB_PWD")
DB_PORT = os.getenv("DB_PORT")

connection = psycopg2.connect(database=DB_NAME, user=DB_USER, password=DB_PWD, host=DB_HOST, port=DB_PORT)
cursor = connection.cursor()

def get_publications():
    cursor.execute("SELECT * FROM publications")
    df = pd.DataFrame(cursor.fetchall(), columns=[desc[0] for desc in cursor.description])
    return df

def open_access(df):
    open_access = df.groupby("open_access", dropna=False).count()
    open_access_count=open_access["title"][True]
    closed_access_count=open_access["title"][False]
    not_findable_count = open_access["title"][np.nan]
    return open_access_count, closed_access_count, not_findable_count




publications = get_publications()
open_access_count, closed_access_count, not_findable_count = open_access(publications)
