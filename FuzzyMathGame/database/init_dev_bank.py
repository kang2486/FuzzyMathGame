"""Initialize only the named dev database. Never overwrite existing data."""
import os
from pathlib import Path
import re
import mysql.connector

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent


def credentials():
    # Read the existing local setting without logging or exporting the password.
    if not os.getenv('FUZZY_DB_PASSWORD'):
        text = (PROJECT/'啟動程式.bat').read_text(encoding='utf-8-sig')
        match = re.search(r'set\s+"FUZZY_DB_PASSWORD=(.*?)"', text, re.I)
        if not match:
            raise RuntimeError('請在本機設定 FUZZY_DB_PASSWORD。')
        os.environ['FUZZY_DB_PASSWORD'] = match[1]
    return dict(host=os.getenv('FUZZY_DB_HOST','localhost'),
                port=int(os.getenv('FUZZY_DB_PORT','3306')),
                user=os.getenv('FUZZY_DB_USER','root'), password=os.environ['FUZZY_DB_PASSWORD'])


def main():
    connection = mysql.connector.connect(**credentials())
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT TABLE_NAME FROM information_schema.tables WHERE TABLE_SCHEMA='fuzzy_math_game_dev'")
        existing = {row[0] for row in cursor.fetchall()}
        if existing:
            if 'bank_meta' not in existing:
                raise RuntimeError('開發庫已存在未辨識的資料表，停止；不覆蓋。')
            cursor.execute('SELECT version FROM fuzzy_math_game_dev.bank_meta ORDER BY version')
            if cursor.fetchall() not in ([(1,)], [(1,), (2,)]):
                raise RuntimeError('開發庫版本不符，停止；不覆蓋。')
            print('Development bank already initialized; no changes made.')
            return
        for file in ('schema.sql','seed.sql'):
            for statement in (ROOT/file).read_text(encoding='utf-8').split(';'):
                if statement.strip():
                    cursor.execute(statement)
        connection.commit()
        print('Created fuzzy_math_game_dev; original databases untouched.')
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == '__main__':
    main()
