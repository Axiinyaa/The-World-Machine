import json
from typing import Union

import mysql.connector as MySQLdb
from interactions import Snowflake

from load_data import load_config

ip = load_config('PHPma-IP')
user = load_config('PHPma-USERNAME')
password = load_config('PHPma-PASSWORD')
db_name = load_config('PHPma-DBNAME')

db: MySQLdb.MySQLConnection = MySQLdb.connect(host=ip, user=user, password=password, database=db_name)
cursor = db.cursor()


def get_datatype(data):
    if type(data) == str:
        return f"{data}"

    if type(data) == list or type(data) == bool:
        return json.dumps(data)

    return data


def get_leaderboard(sort_by: str):
    sql = 'SELECT p_key, {0} FROM user_data ORDER BY {0} DESC LIMIT 10;'.format(sort_by, sort_by)
    cursor.execute(sql)

    return cursor.fetchall()


def get_treasures():
    sql = f'SELECT * FROM Treasures'
    cursor.execute(sql)

    rv = cursor.fetchall()

    row_headers = [x[0] for x in cursor.description]

    json_data = []
    for result in rv:
        json_data.append(dict(zip(row_headers, result)))

    return json_data


def fetch(table: str, column: str, primary_key: Union[int, Snowflake]):
    if type(primary_key) == Snowflake:
        primary_key = int(primary_key)

    select_sql = f"SELECT {column} FROM {table} WHERE p_key = {primary_key}"
    column_sql = f"DESCRIBE {table} {column}"

    try:
        cursor.execute(select_sql)
    except:
        new_entry('server_data', primary_key)

    row = cursor.fetchone()

    cursor.execute(column_sql)
    column_data = cursor.fetchone()

    if row:

        value = row[0]

        # List Handling.
        if column_data[1] == 'longtext':
            value = json.loads(value)

        return value
    else:
        new_entry(table, primary_key)
        return fetch(table, column, primary_key)


def new_entry(table: str, primary_key: int):
    insert_sql = f'INSERT INTO `{table}` (p_key) VALUES ({primary_key})'
    cursor.execute(insert_sql)


def update(table: str, column: str, p_key, data):
    if not p_key:
        raise ValueError("Primary key is not set.")

    if type(p_key) == Snowflake:
        p_key = int(p_key)

    d_type = get_datatype(data)

    # Check if the primary key already exists in the table
    select_sql = f"SELECT * FROM `{table}` WHERE p_key = %s"
    cursor.execute(select_sql, (p_key,))

    row = cursor.fetchone()

    if row:
        update_sql = f"UPDATE `{table}` SET `{column}` = %s WHERE p_key = %s"
        cursor.execute(update_sql, (d_type, p_key))
    else:
        insert_sql = f"INSERT INTO `{table}` (p_key, `{column}`) VALUES (%s, %s)"
        cursor.execute(insert_sql, (p_key, d_type))

    try:
        db.commit()
    except Exception as e:
        print(f"Error committing changes to database: {e}")
        db.rollback()
        return None

    return fetch(table, column, p_key)


def increment_value(table: str, column: str, primary_key: int):
    v: int = fetch(table, column, primary_key)
    update(table, column, primary_key, v + 1)