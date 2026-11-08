
from contextlib import contextmanager


from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

from config.dbconfig import DB_CONFIG, POOL_CONFIG


_pool = None


@contextmanager
def get_cursor():

    global _pool
    if _pool is None:
        _pool = SimpleConnectionPool(POOL_CONFIG["minconn"], POOL_CONFIG["maxconn"], **DB_CONFIG)
    conn = _pool.getconn()
    cursor = None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        _pool.putconn(conn, close=bool(conn.closed))

TABLE = sql.Identifier("driver")
COLUMNS = "driver_id, first_name, last_name, license_number, hired_at"
UPDATABLE = ("first_name", "last_name", "license_number", "hired_at")


class DriverDAO:

    def get_drivers(self, name, license_number, limit, offset):

        where = []
        params = []
        if name:

            where.append("(first_name ILIKE %s OR last_name ILIKE %s "
                         "OR (first_name || ' ' || last_name) ILIKE %s)")
            pattern = f"%{name}%"
            params += [pattern, pattern, pattern]
        if license_number:
            where.append("license_number ILIKE %s")
            params.append(f"%{license_number}%")
        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        with get_cursor() as cursor:
            cursor.execute(
                sql.SQL("SELECT COUNT(*) AS total FROM {}").format(TABLE) + sql.SQL(where_sql),
                params)
            total = cursor.fetchone()["total"]

            cursor.execute(
                sql.SQL("SELECT " + COLUMNS + " FROM {}").format(TABLE)
                + sql.SQL(where_sql + " ORDER BY driver_id LIMIT %s OFFSET %s"),
                params + [limit, offset])
            rows = cursor.fetchall()
        return rows, total

    def get_driver_by_id(self, driver_id):
        with get_cursor() as cursor:
            cursor.execute(
                sql.SQL("SELECT " + COLUMNS + " FROM {} WHERE driver_id = %s").format(TABLE),
                (driver_id,))
            return cursor.fetchone()

    def license_exists(self, license_number, exclude_driver_id=None):
        query = sql.SQL("SELECT 1 FROM {} WHERE license_number = %s").format(TABLE)
        params = [license_number]
        if exclude_driver_id is not None:
            query += sql.SQL(" AND driver_id <> %s")
            params.append(exclude_driver_id)
        with get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone() is not None

    def create_driver(self, data):
        with get_cursor() as cursor:

            #cursor.execute(sql.SQL("LOCK TABLE {} IN EXCLUSIVE MODE").format(TABLE))
            cursor.execute(
                sql.SQL("INSERT INTO {} (first_name, last_name, license_number, hired_at) "
                        "VALUES (%(first_name)s, %(last_name)s, %(license_number)s, %(hired_at)s) "
                        "RETURNING " + COLUMNS).format(TABLE),  #format(TABLE, TABLE)
                data)
            return cursor.fetchone()

    def update_driver(self, driver_id, fields):

        sets = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(sql.Identifier(col)) for col in fields)
        query = (sql.SQL("UPDATE {} SET ").format(TABLE) + sets
                 + sql.SQL(" WHERE driver_id = %s RETURNING " + COLUMNS))
        with get_cursor() as cursor:
            cursor.execute(query, list(fields.values()) + [driver_id])
            return cursor.fetchone()

    def has_assignments(self, driver_id):
        with get_cursor() as cursor:
            cursor.execute(
                sql.SQL("SELECT 1 FROM {} WHERE driver_id = %s LIMIT 1").format(
                    sql.Identifier("vehicle_assignment")),
                (driver_id,))
            return cursor.fetchone() is not None

    def delete_driver(self, driver_id):
        with get_cursor() as cursor:
            cursor.execute(
                sql.SQL("DELETE FROM {} WHERE driver_id = %s").format(TABLE),
                (driver_id,))
            return cursor.rowcount == 1
