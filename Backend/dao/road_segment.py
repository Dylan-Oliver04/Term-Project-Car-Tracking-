from config.dbconfig import DB_CONFIG, POOL_CONFIG
import json
import psycopg2
from pydantic import BaseModel
from typing import Optional
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool
from datetime import datetime


class RoadSegment(BaseModel):
    road_id: int
    name: str
    speed_limit_kph: Optional[int] = None
    geom: Optional[dict] = None
    created_at: datetime
    is_oneway: Optional[bool] = None
    direction: Optional[str] = None


class RoadSegmentCreate(BaseModel):
    name: str
    speed_limit_kph: Optional[int] = None
    geom: dict
    is_oneway: Optional[bool] = None
    direction: Optional[str] = None


class RoadSegmentUpdate(BaseModel):
    name: Optional[str] = None
    speed_limit_kph: Optional[int] = None
    geom: Optional[dict] = None
    is_oneway: Optional[bool] = None
    direction: Optional[str] = None

class RoadSegmentDao:
    def __init__(self):
        #Connection pools serve to create several connections to the DB
        #This makes the app faster because creating connections is
        #expensive. With the pool, you recycle existing connections
        self.pool  = SimpleConnectionPool(POOL_CONFIG["minconn"],
                                          POOL_CONFIG["maxconn"],
                                          **DB_CONFIG)
    
    #Purpose: Create a new road segment.
    def create_road_segment(self, road_segment):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        data = road_segment.model_dump()
        data["geom"] = json.dumps(data["geom"])

        query = """
            Insert into road_segment (
                road_id, 
                name, 
                speed_limit_kph, 
                geom,
                created_at, 
                is_oneway, 
                direction
            )
            Values (
                (SELECT MAX(road_id) + 1 FROM road_segment),
                %(name)s,
                %(speed_limit_kph)s,
                ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326),
                CURRENT_TIMESTAMP,
                %(is_oneway)s,
                %(direction)s
            )
            Returning
                road_id,
                name,
                speed_limit_kph,
                ST_AsGeoJSON(geom) AS geom,
                created_at,
                is_oneway,
                direction
        """
        try:
            cursor.execute(query, data)
            row = dict(cursor.fetchone())
            conn.commit()

            row["geom"] = json.loads(row["geom"]) if row["geom"] else None
            return RoadSegment(**row)
        except Exception:
            conn.rollback()
            raise
        finally:
            # Always close cursor
            cursor.close()
            # Return the connection to the pool
            self.pool.putconn(conn)

    # Purpose: Return a paginated list of road segments. Optional filters may include 
    # name, speed range, or bounding box or all of them.
    def get_road_segments(self, limit, offset, name, min_speed_kph, max_speed_kph, bbox) -> tuple[list[RoadSegment], int]:
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        # Extract bounding box coordinates
        if bbox is not None:
            min_lon, min_lat, max_lon, max_lat = bbox
        else:
            min_lon = min_lat = max_lon = max_lat = None

        count_query = """
            Select COUNT(*)
            From road_segment
            Where (%s IS NULL OR name ILIKE %s)
                AND (%s IS NULL OR speed_limit_kph >= %s)
                AND (%s IS NULL OR speed_limit_kph <= %s)
                AND (%s IS NULL OR ST_Intersects(
                    geom,
                    ST_MakeEnvelope(%s, %s, %s, %s, 4326)
          ))
        """

        cursor.execute(count_query, ( name, f"%{name}%" if name else None,
        min_speed_kph, min_speed_kph, max_speed_kph, max_speed_kph,
        min_lon, min_lon, min_lat, max_lon, max_lat))

        count = cursor.fetchone()[0]


        query = """
            SELECT road_id, name, speed_limit_kph, created_at
            FROM road_segment
            WHERE (%s IS NULL OR name ILIKE %s)
                AND (%s IS NULL OR speed_limit_kph >= %s)
                AND (%s IS NULL OR speed_limit_kph <= %s)
                AND (%s IS NULL OR ST_Intersects(
                    geom,
                    ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                ))
            ORDER BY road_id
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (name, f"%{name}%" if name else None,
        min_speed_kph, min_speed_kph, max_speed_kph, max_speed_kph,
        min_lon, min_lon, min_lat, max_lon, max_lat, limit, offset))

        result = []
        for row in cursor:
            result.append(dict(row))

        # Always close cursor
        cursor.close()
        # Return the connection to the pool
        self.pool.putconn(conn)
        return result, count

    # Purpose: Return one road segment by ID.
    def get_road_segment_by_ID(self, road_id):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        query = """
            Select road_id, name, speed_limit_kph,ST_AsGeoJSON(geom) AS geom, created_at, is_oneway, direction
            From road_segment
            Where road_id = %s
        """
        try:
            cursor.execute(query, (road_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            result = dict(row)
            result["geom"] = json.loads(result["geom"]) if result["geom"] else None
            return RoadSegment(**result)
        finally:
            # Always close cursor
            cursor.close()
            # Return the connection to the pool
            self.pool.putconn(conn)


    def update_road_segment(self, road_id, road_segment):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        try:
            # Retrieve the existing vehicle
            query = """
                Select road_id, name, speed_limit_kph,ST_AsGeoJSON(geom) AS geom, created_at, is_oneway, direction
                From road_segment
                Where road_id = %s
            """

            cursor.execute(query, (road_id,))            
            current = cursor.fetchone()
            if current is None:
                return None

            # Same merge method used in update_vehicle
            updates = road_segment.model_dump(exclude_unset=True)
            merged = dict(current)
            merged.update(updates)
            merged["road_id"] = road_id

            if isinstance(merged["geom"], dict):
                merged["geom"] = json.dumps(merged["geom"])

            query = """
                Update road_segment
                Set name = %(name)s,
                    speed_limit_kph = %(speed_limit_kph)s,
                    geom = ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326),
                    is_oneway = %(is_oneway)s,
                    direction = %(direction)s
                Where road_id = %(road_id)s
                Returning 
                    road_id, name, 
                    speed_limit_kph,
                    ST_AsGeoJSON(geom) AS geom,
                    created_at, is_oneway, 
                    direction
            """
            cursor.execute(query, merged)
            row = cursor.fetchone()
            conn.commit()
            result = dict(row)
            result["geom"] = json.loads(result["geom"]) if result["geom"] else None
            return RoadSegment(**result)
        except Exception:
            conn.rollback()
            raise
        finally:
            # Always close cursor
            cursor.close()
            # Return the connection to the pool
            self.pool.putconn(conn)

    # Purpose: Delete a road segment.
    def delete_road_segment(self, road_id):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        query = """
            Delete From road_segment
            Where road_id = %s
             road_id
        """
        try:
            cursor.execute(query, (road_id,))
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


    def get_road_segments_geojson(self, limit, offset, name, min_speed_kph, max_speed_kph):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        count_query = """
            SELECT COUNT(*)
            FROM road_segment
            WHERE (%s IS NULL OR name ILIKE %s)
              AND (%s IS NULL OR speed_limit_kph >= %s)
              AND (%s IS NULL OR speed_limit_kph <= %s)
        """
        query = """
            SELECT road_id, name, speed_limit_kph, is_oneway,
                   direction, created_at, ST_AsGeoJSON(geom) AS geom
            FROM road_segment
            WHERE (%s IS NULL OR name ILIKE %s)
              AND (%s IS NULL OR speed_limit_kph >= %s)
              AND (%s IS NULL OR speed_limit_kph <= %s)
            ORDER BY road_id
            LIMIT %s OFFSET %s
        """
        try:
            cursor.execute(count_query, (
                name, f"%{name}%" if name else None,
                min_speed_kph, min_speed_kph,
                max_speed_kph, max_speed_kph
            ))
            count = cursor.fetchone()[0]

            cursor.execute(query, (
                name, f"%{name}%" if name else None,
                min_speed_kph, min_speed_kph,
                max_speed_kph, max_speed_kph,
                limit, offset
            ))

            features = []
            for row in cursor:
                features.append({
                    "type": "Feature",
                    "geometry": json.loads(row["geom"]) if row["geom"] else None,
                    "properties": {
                        "road_id": row["road_id"],
                        "name": row["name"],
                        "speed_limit_kph": row["speed_limit_kph"],
                        "is_oneway": row["is_oneway"],
                        "direction": row["direction"],
                        "created_at": row["created_at"]
                    }
                })
            return {
                "type": "FeatureCollection",
                "count": count,
                "limit": limit,
                "offset": offset,
                "features": features
            }
        finally:
            cursor.close()
            self.pool.putconn(conn)

    # Purpose: Check if the geometry is valid.
    def check_geometry(self, geom):
        # Get Connection from pool
        conn = self.pool.getconn()
        cursor = conn.cursor(cursor_factory=DictCursor)

        query = """
            SELECT ST_IsValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
        """

        try:
            cursor.execute(query, (json.dumps(geom),))
            result = cursor.fetchone()
            return result[0]

        except psycopg2.Error:
            conn.rollback()
            return False

        finally:
            # Always close cursor
            cursor.close()
            # Return connection to the pool
            self.pool.putconn(conn)