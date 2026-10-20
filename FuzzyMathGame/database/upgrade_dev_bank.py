"""Apply the additive chapter 4/5/8 migration once, with no updates or deletes."""
from init_dev_bank import ROOT, credentials
import mysql.connector


def main():
    connection = mysql.connector.connect(**credentials(), database='fuzzy_math_game_dev')
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT version FROM bank_meta ORDER BY version')
        versions = cursor.fetchall()
        if versions == [(1,), (2,)]:
            print('Migration 2 already applied; no changes made.')
            return
        if versions != [(1,)]:
            raise RuntimeError('Unexpected database version; stopped without changes.')
        for statement in (ROOT/'migration_002.sql').read_text(encoding='utf-8').split(';'):
            if statement.strip():
                cursor.execute(statement)
        connection.commit()
        print('Added chapters 4, 5, 8; previous question rows unchanged.')
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == '__main__':
    main()
