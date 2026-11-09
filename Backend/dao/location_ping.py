from config.dbconfig import DB_CONFIG, POOL_CONFIG
import json
import psycopg2
from pydantic import BaseModel
from typing import Optional
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool
from datetime import datetime
import math

 
class Location_Ping(BaseModel):
    ping_id : Optional[int] = None
    vehicle_id : int
    ts: datetime
    geom: dict
    speed_kph: Optional[float] = None
    heading_deg: Optional[float] = None

class Location_Ping_Update(BaseModel):
    vehicle_id: Optional[int] = None
    ts: Optional[datetime] = None
    geom: Optional[dict] = None
    speed_kph: Optional[float] = None
    heading_deg: Optional[float] = None


class Location_PingDAO:
    _pool = None

    def __init__(self):
        if Location_PingDAO._pool is None:
            Location_PingDAO._pool = SimpleConnectionPool(
                POOL_CONFIG["minconn"], POOL_CONFIG["maxconn"], **DB_CONFIG)
        self.pool = Location_PingDAO._pool


    SELECT_PING = """
        SELECT
        ping_id,
        vehicle_id,
        ts,
        ST_AsGeoJSON(geom)::json AS geom,
        speed_kph,
        heading_deg
        FROM location_ping
        """

    SELECT_PING_SUMMARY = ("SELECT ping_id, vehicle_id, ts, speed_kph, heading_deg "
                           "FROM location_ping")
    
    SELECT_PING_BY_VEHICLE = ("SELECT ping_id, ts, ST_AsGeoJSON(geom)::json AS geom, "
                              "speed_kph, heading_deg FROM location_ping")

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
                        ST_GeomFromGeoJSON(%s),
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


    def vehicle_exists(self, vehicle_id):
        conn = self.pool.getconn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM vehicle WHERE vehicle_id = %s", (vehicle_id,))
            return cursor.fetchone() is not None
        finally:
            cursor.close()
            self.pool.putconn(conn)
    
    
    #GET /api/v1/location-pings
    # Purpose: Return a paginated list of pings. 
    def get_all_location_pings(self,vehicle_id=None,from_ts=None,to_ts=None,bbox=None,limit=100,offset=0):
        conn = self.pool.getconn()
        cursor = conn.cursor(cursor_factory=DictCursor)
        try:
            conditions = []
            params = []
        
            if vehicle_id is not None:
                conditions.append("vehicle_id = %s")
                params.append(vehicle_id)
        
            if from_ts is not None:
                conditions.append("ts >= %s")
                params.append(from_ts)
        
            if to_ts is not None:
                conditions.append("ts <= %s")
                params.append(to_ts)
        
            if bbox is not None:
                conditions.append("""
                    ST_Intersects(
                    geom,
                    ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                    )
                """)
                params.extend(bbox)
        
            where_clause = ""
        
            if conditions:
                where_clause = " WHERE " + " AND ".join(conditions)
        
            count_query = (
                "SELECT COUNT(*) AS count FROM location_ping "
                + where_clause
            )
        
            cursor.execute(count_query, tuple(params))
            count = cursor.fetchone()["count"]
        
            query = (self.SELECT_PING_SUMMARY + where_clause + " ORDER BY ping_id ASC LIMIT %s OFFSET %s")
            cursor.execute(
                query,
                tuple(params + [limit, offset])
            )
        
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
        

    
    # GET /api/v1/location-pings/{ping_id}
    #  Purpose: Return one ping by ID. 
    def get_location_ping_by_id(self, ping_id: int) -> Optional[Location_Ping]:
        conn = self.pool.getconn()
        cursor = conn.cursor(cursor_factory=DictCursor)
        try:
            query = """
            select ping_id, vehicle_id, ts, ST_AsGeoJSON(geom)::json AS geom, speed_kph, heading_deg
            from location_ping
            where ping_id = %s"""
            cursor.execute(query, (ping_id,))
            result : Optional[Location_Ping] = None
            result = cursor.fetchone()
            return Location_Ping(**dict(result)) if result else None
        finally:
            cursor.close()
            self.pool.putconn(conn)
        

    # GET /api/v1/vehicles/{vehicle_id}/pings 
    # Purpose: Return the pings associated with one vehicle.
    def get_location_ping_by_vehicle_id(self,vehicle_id,limit=100,offset=0,from_ts=None,to_ts=None):
        conn = self.pool.getconn()
        cursor = conn.cursor(cursor_factory=DictCursor)
        try:
            conditions = ["vehicle_id = %s"]
            params = [vehicle_id]

            if from_ts is not None:
                conditions.append("ts >= %s")
                params.append(from_ts)

            if to_ts is not None:
                conditions.append("ts <= %s")
                params.append(to_ts)

            where_clause = " WHERE " + " AND ".join(conditions)

            count_query = (
                "SELECT COUNT(*) AS count FROM location_ping "
                + where_clause
            )

            cursor.execute(count_query, tuple(params))
            count = cursor.fetchone()["count"]

            query = (self.SELECT_PING_BY_VEHICLE + where_clause + " ORDER BY ping_id ASC LIMIT %s OFFSET %s")
            cursor.execute(
                query,
                tuple(params + [limit, offset])
            )

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



    # POST /api/v1/location-pings
    # Purpose: Create a new location ping for a vehicle.
    def create_location_ping(self, new_location_ping: Location_Ping):
        conn = self.pool.getconn()
        cursor = conn.cursor()
        try:
            data = new_location_ping.model_dump()
            query = """
                INSERT INTO location_ping (vehicle_id, ts, geom, speed_kph, heading_deg)
                VALUES ( %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s, %s )
                RETURNING ping_id
            """
            cursor.execute(query, (data["vehicle_id"], data["ts"], json.dumps(data["geom"]),data["speed_kph"],data["heading_deg"] ))
            ping_id = cursor.fetchone()[0]
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            self.pool.putconn(conn)
        return self.get_location_ping_by_id(ping_id)
    

    #PUT /api/v1/location-pings/{ping_id} 
    #Purpose: Partially or fully update a ping.     
    def update_location_ping(self, ping_id, location_ping):
        conn = self.pool.getconn()
        cursor = conn.cursor()
        try:
            data = location_ping.model_dump(exclude_unset=True)
            if not data:
                return None
            allowed_fields = {"vehicle_id","ts","geom","speed_kph","heading_deg"}
            fields = []
            params = []
            for field, value in data.items():
                if field not in allowed_fields:
                    continue
                if field == "geom":
                    fields.append("""geom = ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)""")
                    params.append(json.dumps(value))
                else:
                    fields.append(f"{field} = %s")
                    params.append(value)
            if not fields:
                return None
            query = """
                UPDATE location_ping
                SET """ + ", ".join(fields) + """
                WHERE ping_id = %s
                RETURNING ping_id
            """
            params.append(ping_id)
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
        return self.get_location_ping_by_id(ping_id)

    #DELETE /api/v1/location-pings/{ping_id}
    #Purpose: Delete a ping. 
    def delete_location_ping(self, ping_id):
        conn = self.pool.getconn()
        cursor = conn.cursor()
        try:
            query = """
                DELETE FROM location_ping
                WHERE ping_id = %s
                RETURNING ping_id
            """
            cursor.execute(query, (ping_id,))
            result = cursor.fetchone()
            conn.commit()
            return result[0] if result else None
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            self.pool.putconn(conn)
