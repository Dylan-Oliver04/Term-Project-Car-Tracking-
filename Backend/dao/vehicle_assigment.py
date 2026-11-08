
from contextlib import contextmanager


from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from pydantic import BaseModel

from config.dbconfig import DB_CONFIG, POOL_CONFIG


_pool = None

class VehicleAssignmentCreate(BaseModel):
    vehicle_id: int
    driver_id: int
    assigned_from: str
    assigned_to: str | None = None


class VehicleAssignmentUpdate(BaseModel):
    vehicle_id: int | None = None
    driver_id: int | None = None
    assigned_from: str | None = None
    assigned_to: str | None = None

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

TABLE = sql.Identifier("vehicle_assignment")
COLUMNS = "assignment_id, vehicle_id, driver_id, assigned_from, assigned_to"
UPDATABLE = ("vehicle_id", "driver_id", "assigned_from", "assigned_to")


class VehicleAssignmentDAO:

    def get_assignments(self, vehicle_id, driver_id, active, limit, offset):

        where = []
        params = []
        if vehicle_id is not None:
            where.append("vehicle_id = %s")
            params.append(vehicle_id)
        if driver_id is not None:
            where.append("driver_id = %s")
            params.append(driver_id)
        if active is True:
            where.append("assigned_to IS NULL")
        elif active is False:
            where.append("assigned_to IS NOT NULL")
        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        with get_cursor() as cursor:
            cursor.execute(
                sql.SQL("SELECT COUNT(*) AS total FROM {}").format(TABLE) + sql.SQL(where_sql),
                params)
            total = cursor.fetchone()["total"]

            cursor.execute(
                sql.SQL("SELECT " + COLUMNS + " FROM {}").format(TABLE)
                + sql.SQL(where_sql + " ORDER BY assignment_id LIMIT %s OFFSET %s"),
                params + [limit, offset])
            rows = cursor.fetchall()
        return rows, total

    def get_assignment_by_id(self, assignment_id):
        with get_cursor() as cursor:
            cursor.execute(
                sql.SQL("SELECT " + COLUMNS + " FROM {} WHERE assignment_id = %s").format(TABLE),
                (assignment_id,))
            return cursor.fetchone()

    def vehicle_exists(self, vehicle_id):
        with get_cursor() as cursor:
            cursor.execute(
                sql.SQL("SELECT 1 FROM {} WHERE vehicle_id = %s").format(
                    sql.Identifier("vehicle")),
                (vehicle_id,))
            return cursor.fetchone() is not None

    def driver_exists(self, driver_id):
        with get_cursor() as cursor:
            cursor.execute(
                sql.SQL("SELECT 1 FROM {} WHERE driver_id = %s").format(
                    sql.Identifier("driver")),
                (driver_id,))
            return cursor.fetchone() is not None

    def create_assignment(self, data):
        with get_cursor() as cursor:

            #cursor.execute(sql.SQL("LOCK TABLE {} IN EXCLUSIVE MODE").format(TABLE))
            cursor.execute(
                sql.SQL("INSERT INTO {} (vehicle_id, driver_id, assigned_from, assigned_to) "
                        "VALUES (%(vehicle_id)s, %(driver_id)s, %(assigned_from)s, %(assigned_to)s) "
                        "RETURNING " + COLUMNS).format(TABLE),   #format(TABLE, TABLE)
                data)
            return cursor.fetchone()

    def update_assignment(self, assignment_id, fields):

        sets = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(sql.Identifier(col)) for col in fields)
        query = (sql.SQL("UPDATE {} SET ").format(TABLE) + sets
                 + sql.SQL(" WHERE assignment_id = %s RETURNING " + COLUMNS))
        with get_cursor() as cursor:
            cursor.execute(query, list(fields.values()) + [assignment_id])
            return cursor.fetchone()

    def delete_assignment(self, assignment_id):
        with get_cursor() as cursor:
            cursor.execute(
                sql.SQL("DELETE FROM {} WHERE assignment_id = %s").format(TABLE),
                (assignment_id,))
            return cursor.rowcount == 1
