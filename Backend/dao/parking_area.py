from config.dbconfig import DB_CONFIG, POOL_CONFIG
import json
import psycopg2
from pydantic import BaseModel
from typing import Optional
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool
from datetime import datetime

class ParkingArea(BaseModel):
    parking_area_id: int
    name: str
    capacity: Optional[int] = None
    geom: Optional[dict] = None
    created_at: datetime


class ParkingAreaCreate(BaseModel):
    name: str
    capacity: Optional[int] = None
    geom: dict


class ParkingAreaUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = None
    geom: Optional[dict] = None


class ParkingAreaDao:
    def __init__(self):
        # Same structure as VehicleDao
        self.pool = SimpleConnectionPool(POOL_CONFIG["minconn"],
                                         POOL_CONFIG["maxconn"],
                                         **DB_CONFIG)

    def create_parking_area(self, area):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        data = area.model_dump()
        data["geom"] = json.dumps(data["geom"])

        query = """
            Insert into parking_area (
                parking_area_id, 
                name, 
                capacity, 
                geom, 
                created_at
            )
            VALUES (
                (SELECT MAX(parking_area_id) + 1 FROM parking_area),
                %(name)s,
                %(capacity)s,
                ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326),
                CURRENT_TIMESTAMP
            )
            Returning parking_area_id, 
            name, 
            capacity,
            ST_AsGeoJSON(geom) AS geom, 
            created_at
        """

        try:
            cursor.execute(query, data)
            row = cursor.fetchone()
            conn.commit()

            result = dict(row)
            result["geom"] = json.loads(result["geom"])
            return ParkingArea(**result)
        except Exception:
            conn.rollback()
            raise
        finally:
            # Always close cursor
            cursor.close()
            # Return the connection to the pool
            self.pool.putconn(conn)


    def get_parking_areas(self, limit, offset, name, bbox):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        if bbox is not None:
            min_lon, min_lat, max_lon, max_lat = bbox
        else:
            min_lon = min_lat = max_lon = max_lat = None

        count_query = """
            Select COUNT(*)
            From parking_area
            Where (%s IS NULL OR name ILIKE %s)
              AND (%s IS NULL OR ST_Intersects(
                  geom, 
                  ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                ))
        """

        cursor.execute(count_query, ( name, f"%{name}%" if name else None, min_lon, min_lon, min_lat, max_lon, max_lat))
        count = cursor.fetchone()[0]

        query = """
            SELECT parking_area_id, name, capacity, created_at
            FROM parking_area
            WHERE (%s IS NULL OR name ILIKE %s)
              AND (%s IS NULL OR ST_Intersects(
                  geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326)))
            ORDER BY parking_area_id
            LIMIT %s OFFSET %s
        """

        cursor.execute(query, (name, f"%{name}%" if name else None, min_lon, min_lon, min_lat, max_lon, max_lat, limit, offset ))

        result = []
        for row in cursor:
            result.append(dict(row))

        # Always close cursor
        cursor.close()
        # Return the connection to the pool
        self.pool.putconn(conn)
        return result, count


    def get_parking_area_by_ID(self, parking_area_id):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        query = """
            Select parking_area_id, name, capacity, ST_AsGeoJSON(geom) AS geom, created_at
            FROM parking_area
            WHERE parking_area_id = %s
        """
        try:
            cursor.execute(query, (parking_area_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            result = dict(row)
            result["geom"] = json.loads(result["geom"]) if result["geom"] else None
            return ParkingArea(**result)
        finally:
            # Always close cursor
            cursor.close()
            # Return the connection to the pool
            self.pool.putconn(conn)


    def update_parking_area(self, parking_area_id, area):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        try:
            query = """
                Select parking_area_id, name, capacity, ST_AsGeoJSON(geom) AS geom, created_at
                From parking_area
                Where parking_area_id = %s
            """

            cursor.execute(query, (parking_area_id,))
            current = cursor.fetchone()
            if current is None:
                return None

            # Same merge method used in update_vehicle
            updates = area.model_dump(exclude_unset=True)
            merged = dict(current)
            merged.update(updates)
            merged["parking_area_id"] = parking_area_id

            if isinstance(merged["geom"], dict):
                merged["geom"] = json.dumps(merged["geom"])
            
            query = """
                Update parking_area
                Set name = %(name)s,
                    capacity = %(capacity)s,
                    geom = ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326)
                Where parking_area_id = %(parking_area_id)s
                Returning 
                    parking_area_id, 
                    name, 
                    capacity,
                    ST_AsGeoJSON(geom) AS geom, 
                    created_at
            """
            cursor.execute(query, merged)
            row = cursor.fetchone()
            conn.commit()
            result = dict(row)
            result["geom"] = json.loads(result["geom"]) if result["geom"] else None
            return ParkingArea(**result)
        except Exception:
            conn.rollback()
            raise
        finally:
            # Always close cursor
            cursor.close()
            # Return the connection to the pool
            self.pool.putconn(conn)


    def delete_parking_area(self, parking_area_id):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        query = """
            Delete From parking_area
            Where parking_area_id = %s
            Returning parking_area_id
        """
        try:
            cursor.execute(query, (parking_area_id,))
            rows = cursor.fetchone()

            if rows is None:
                return None
        
            conn.commit()
            return rows
        except Exception:
            conn.rollback()
            raise
        finally:
            # Always close cursor
            cursor.close()
            # Return the connection to the pool
            self.pool.putconn(conn)

    def check_geometry(self, geom):
        conn = self.pool.getconn()
        cursor = conn.cursor(cursor_factory=DictCursor)
        query = """
            SELECT ST_IsValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
        """
        try:
            cursor.execute(query, (json.dumps(geom),))
            row = cursor.fetchone()
            return row[0]
        
        except psycopg2.Error:
            conn.rollback()
            return False
        
        finally:
            # Always close cursor
            cursor.close()
            # Return connection to the pool
            self.pool.putconn(conn)