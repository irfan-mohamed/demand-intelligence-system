import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import psycopg2
import pandas as pd
from config.config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def run_query(sql: str) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql(sql, conn)

def run_sql(sql: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()

def run_sql_file(filepath: str):
    with open(filepath, "r") as f:
        sql = f.read()
    run_sql(sql)
    print(f"Executed: {filepath}")
