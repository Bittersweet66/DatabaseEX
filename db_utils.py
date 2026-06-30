# db_utils.py
import pymysql
from config import DB_CONFIG

class DBConnection:
    @staticmethod
    def get_conn():
        return pymysql.connect(**DB_CONFIG)

    @staticmethod
    def execute_query(sql, params=None, fetch_all=True):
        conn = None
        cursor = None
        try:
            conn = DBConnection.get_conn()
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            if sql.strip().upper().startswith('SELECT'):
                return cursor.fetchall() if fetch_all else cursor.fetchone()
            else:
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()