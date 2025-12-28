import pymysql
import config

try:
    conn = pymysql.connect(
        host=config.MYSQL_HOST,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        port=config.MYSQL_PORT
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config.MYSQL_DATABASE}")
    print(f"Database {config.MYSQL_DATABASE} created successfully")
    conn.close()
except Exception as e:
    print(f"Error creating database: {e}")
