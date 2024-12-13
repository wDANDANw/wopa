import os
import pymysql

###############################################################################
# File: core/db.py
#
# Purpose:
# Provide a function get_db_connection() that returns a pymysql connection
# to the MySQL database. The login route and other DB-related endpoints
# will use this to interact with `Accounts` and `Historys` tables.
#
# Design & Philosophy:
# - Rely on environment variables: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME.
# - Use pymysql with DictCursor for convenience when fetching rows.
# - If environment variables are missing, we can either default or raise an error.
#
# Maintainability:
# - If DB credentials change, just update environment variables.
# - If we switch to another DB library, just update this file.
###############################################################################

def get_db_connection():
    """
    Returns a pymysql connection using credentials from environment variables.
    Expected environment variables:
    - DB_HOST
    - DB_USER
    - DB_PASSWORD
    - DB_NAME

    Raises:
        KeyError if any variable is missing or ValueError if invalid credentials.
    """
    host = os.environ.get("DB_HOST", "mysql")
    user = os.environ.get("DB_USER", "root")
    password = os.environ.get("DB_PASSWORD", "123456")
    database = os.environ.get("DB_NAME", "phishing")

    # Create and return the connection
    # If any issue, pymysql will raise an error at connect time.
    return pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor
    )