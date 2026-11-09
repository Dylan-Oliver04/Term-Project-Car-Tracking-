from config.dbconfig import DB_CONFIG, POOL_CONFIG
import json
import psycopg2
from pydantic import BaseModel
from typing import Optional
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool
from datetime import datetime
import math

class Trip(BaseModel):
    trip_id : Optional[int] | None = None
    vehicle_id : int
    start_ts : datetime
    end_ts : datetime
    start_geom: Optional[dict] = None
    end_geom: Optional[dict] = None
    distance_km: Optional[float] = None
    
class TripUpdate(BaseModel):
    vehicle_id: Optional[int] = None
    start_ts: Optional[datetime] = None
    end_ts: Optional[datetime] = None
    start_geom: Optional[dict] = None
    end_geom: Optional[dict] = None
    distance_km: Optional[float] = None

SELECT_TRIP = """
        SELECT
            trip_id,
            vehicle_id,
            start_ts,
            end_ts,
            ST_AsGeoJSON(start_geom)::json AS start_geom,
            ST_AsGeoJSON(end_geom)::json AS end_geom,
            distance_km
        FROM trip
    """
SELECT_TRIP_SUMMARY = "SELECT trip_id, vehicle_id, start_ts, end_ts, distance_km FROM trip"
SELECT_TRIP_BY_VEHICLE = "SELECT trip_id, start_ts, end_ts, distance_km FROM trip"

class TripDAO:
    _pool = None
    def __init__(self):
        if TripDAO._pool is None:
              TripDAO._pool = SimpleConnectionPool(
                  POOL_CONFIG["minconn"], POOL_CONFIG["maxconn"], **DB_CONFIG)
        self.pool = TripDAO._pool


  # Check if vehicle exists
    def vehicle_exists(self, vehicle_id):
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM vehicle WHERE vehicle_id = %s",
                (vehicle_id,)
            )
            return cursor.fetchone() is not None
        finally:
            cursor.close()
            self.pool.putconn(conn)


#     POST /api/v1/trips
#  Purpose: Create a new trip. 
    def create_trip(self, new_trip: Trip) -> int:
        conn = self.pool.getconn()
        cursor = conn.cursor(cursor_factory=DictCursor)
        try:
            data = new_trip.model_dump()
            query = """
            INSERT INTO trip (vehicle_id, start_ts, end_ts, start_geom, end_geom, distance_km)
            VALUES (%s, %s, %s,
            ST_SetSRID(ST_GeomFromGeoJSON(%s::text), 4326),
            ST_SetSRID(ST_GeomFromGeoJSON(%s::text), 4326),
            %s)
            RETURNING trip_id
            """
            cursor.execute(query, (
                            data["vehicle_id"],
                            data["start_ts"],
                            data["end_ts"],
                            json.dumps(data["start_geom"]) if data["start_geom"] else None,
                            json.dumps(data["end_geom"]) if data["end_geom"] else None,
                            data["distance_km"]
                        ))
            trip_id = cursor.fetchone()[0]
            conn.commit()
            return trip_id
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            self.pool.putconn(conn)
        

    
# GET /api/v1/trips Purpose: Return a paginated list of trips
    def get_all_trips( self,vehicle_id=None, from_ts=None, to_ts=None, limit=50, offset=0):
        conn = self.pool.getconn()
        cursor = conn.cursor(cursor_factory=DictCursor)
        try: 
            conditions = []
            params = []
            if vehicle_id is not None:
                conditions.append("vehicle_id = %s")
                params.append(vehicle_id)

            if from_ts is not None:
                conditions.append("start_ts >= %s")
                params.append(from_ts)

            if to_ts is not None:
                conditions.append("start_ts <= %s")
                params.append(to_ts)
            
            where_clause = ""
            if conditions:
                where_clause = " WHERE " + " AND ".join(conditions)
            count_query = (
                "SELECT COUNT(*) AS count FROM trip "
                + where_clause
            )
            cursor.execute(count_query, tuple(params))
            count = cursor.fetchone()["count"]

            query = (SELECT_TRIP_SUMMARY + where_clause + " ORDER BY trip_id ASC LIMIT %s OFFSET %s")
            cursor.execute(query, tuple(params + [limit, offset]))

            items = [dict(row) for row in cursor.fetchall()]
            return {
                "items": items,
                "limit": limit,
                "offset": offset,
                "count": count
            }
        finally:
            cursor.close()
            self.pool.putconn(conn)
            


# GET /api/v1/trips/{trip_id} 
# Purpose: Return one trip by ID. 
    def get_trip_by_id(self, trip_id):
       conn = self.pool.getconn()
       try:
           with conn.cursor(cursor_factory=DictCursor) as cur:
               cur.execute(SELECT_TRIP + " WHERE trip_id = %s", (trip_id,))
               row = cur.fetchone()
           return Trip(**dict(row)) if row else None
       finally:
           self.pool.putconn(conn)


# PUT /api/v1/trips/{trip_id} Purpose: 
# Partially or fully update a trip. 
    def update_trip(self, trip_id, trip: TripUpdate):
        conn = self.pool.getconn()
        cursor = conn.cursor(cursor_factory=DictCursor)
        try:
            data = trip.model_dump(exclude_unset=True)
            if not data:
                return None
            
            allowed_fields = {
                            "vehicle_id",
                            "start_ts",
                            "end_ts",
                            "start_geom",
                            "end_geom",
                            "distance_km"
                        }
            
            fields = []
            params = []
            
            for field, value in data.items():
            
                if field not in allowed_fields:
                    continue
            
                if field in ("start_geom", "end_geom"):
                    fields.append(
                            f"{field} = ST_SetSRID("
                            "ST_GeomFromGeoJSON(%s::text), 4326)"
                        )
                    params.append(
                    json.dumps(value) if value is not None else None
                    )
            
                else:
                    fields.append(f"{field} = %s")
                    params.append(value)
            
            if not fields:
                return None
            
            query = """
                UPDATE trip
                SET """ + ", ".join(fields) + """
                WHERE trip_id = %s
                RETURNING trip_id
            """
            
            params.append(trip_id)
            cursor.execute(query, tuple(params))
            result = cursor.fetchone()
            
            if result is None:
                conn.rollback()
                return None
            conn.commit()
            
        
        except Exception:
            conn.rollback()
            raise
        
        finally:
            cursor.close()
            self.pool.putconn(conn)
        return self.get_trip_by_id(trip_id)


# DELETE /api/v1/trips/{trip_id} 
# Purpose: Delete a trip. 
    def delete_trip(self, trip_id):
        conn = self.pool.getconn()
        cursor = conn.cursor(cursor_factory=DictCursor)
        try:
            query = """
                    DELETE FROM trip 
                    WHERE trip_id = %s 
                    RETURNING trip_id
                    """
            cursor.execute(query, (trip_id,))
            result = cursor.fetchone()
            conn.commit()
            return result[0] if result else None
        except Exception:
            conn.rollback()
            raise
        
        finally:
            cursor.close()
            self.pool.putconn(conn)

     
# GET /api/v1/vehicles/{vehicle_id}/trips
#  Purpose: Return the trips associated with one vehicle. 
    def get_trip_by_vehicle_id(self, vehicle_id, limit=50, offset=0, from_ts=None, to_ts=None):
        conn = self.pool.getconn()
        cursor = conn.cursor(cursor_factory=DictCursor)
        try: 
            conditions = ["vehicle_id = %s"]
            params = [vehicle_id]
            if from_ts is not None:
                conditions.append("start_ts >= %s")
                params.append(from_ts)
            if to_ts is not None:
                conditions.append("start_ts <= %s")
                params.append(to_ts)
            where_clause = " WHERE " + " AND ".join(conditions)
            count_query = (
                "SELECT COUNT(*) AS count FROM trip "
                + where_clause
            )
            cursor.execute(count_query, tuple(params))
            count = cursor.fetchone()["count"]
            query = (SELECT_TRIP_BY_VEHICLE + where_clause + " ORDER BY trip_id ASC LIMIT %s OFFSET %s")
            cursor.execute(query, tuple(params + [limit, offset]))
            items = [dict(row) for row in cursor.fetchall()]
            return {
                "vehicle_id": vehicle_id,
                "items": items,
                "limit": limit,
                "offset": offset,
                "count": count
            }
        finally:
            cursor.close()
            self.pool.putconn(conn)
        
    def check_geometry(self, geom):
            if not isinstance(geom, dict):
                return False
            if geom.get("type") != "Point":
                return False
            coordinates = geom.get("coordinates")
            if not isinstance(coordinates, list) or len(coordinates) != 2:
                return False
            lon, lat = coordinates
            if (isinstance(lon, bool) or isinstance(lat, bool) or not isinstance(lon, (int, float)) or not isinstance(lat, (int, float))):
                return False
            if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
                return False
            conn = self.pool.getconn()
            cursor = conn.cursor()
            try:
                query = """
                    SELECT
                        ST_GeometryType(g) = 'ST_Point'
                        AND ST_SRID(g) = 4326
                        AND ST_IsValid(g)
                    FROM (
                        SELECT ST_SetSRID(
                            ST_GeomFromGeoJSON(%s::text),
                            4326
                        ) AS g
                    ) AS geometry_check
                """
                cursor.execute(query, (json.dumps(geom),))
                result = cursor.fetchone()
    
                return result is not None and result[0] is True
            except (ValueError, TypeError, psycopg2.Error):
                conn.rollback()
                return False
            finally:
                cursor.close()
                self.pool.putconn(conn)
    

    

