from config.dbconfig import DB_CONFIG, POOL_CONFIG
import json
import psycopg2
from pydantic import BaseModel
from typing import Optional
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool
from datetime import datetime


class Vehicle(BaseModel):
    vehicle_id : Optional[int] | None = None
    vehicle_type_id : Optional[int] | None = None
    vehicle_status_id : Optional[int] | None = None
    plate_number : str
    make : str
    model : str
    year : int
    created_at : datetime

class VehicleUpdate(BaseModel):
    vehicle_type_id: Optional[int] = None
    vehicle_status_id: Optional[int] = None
    plate_number: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None

class VehicleCreate(BaseModel):
    vehicle_type_id: int
    vehicle_status_id: int
    plate_number: str
    make: str
    model: str
    year: int

class VehicleDao:
    def __init__(self):
        #Connection pools serve to create several connections to the DB
        #This makes the app faster because creating connections is
        #expensive. With the pool, you recycle existing connections
        self.pool  = SimpleConnectionPool(POOL_CONFIG["minconn"],
                                          POOL_CONFIG["maxconn"],
                                          **DB_CONFIG)

        
    def create_vehicle(self, vehicle):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        query = """
            insert into vehicle (
                vehicle_id,
                vehicle_type_id, 
                vehicle_status_id, 
                plate_number,
                make,
                model,
                year,
                created_at
            )
            Values (
            (SELECT MAX(vehicle_id) + 1 FROM vehicle),
                %(vehicle_type_id)s,
                %(vehicle_status_id)s,
                %(plate_number)s,
                %(make)s,
                %(model)s,
                %(year)s,
                CURRENT_TIMESTAMP
            )
            returning *
        """
        try:
            cursor.execute(query, vehicle.model_dump())
            row = cursor.fetchone()

            conn.commit()

            return Vehicle(**row)
        finally:
            # Always close cursor
            cursor.close()
            # Return the connection to the pool
            self.pool.putconn(conn)

    
    # Purpose: Return a paginated list of vehicles. The endpoint supports filtering by 
        # plate_number, status, or both.  
    # Validations and business rules:
    # limit and offset must be non-negative integers.
    # status filter is optional and may be provided as a status name or status ID, depending on 
        # the implementation.
    # plate_number filter is optional, supports partial matching. 
    def get_vehicles(self, limit, offset, status,plate_number) -> tuple[list[Vehicle], int]:
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        count_query = """
            Select COUNT(*)
            From vehicle
            Where (%s IS NULL OR plate_number ILIKE %s) AND (%s IS NULL OR vehicle_status_id = %s)
        """

        cursor.execute(count_query, (plate_number, f"%{plate_number}%" if plate_number else None, status, status))

        count = cursor.fetchone()[0]


        query = """
            Select *
            From vehicle
            Where (%s IS NULL OR plate_number ILIKE %s) AND (%s IS NULL OR vehicle_status_id = %s)
            Order By vehicle_id
            Limit %s Offset %s
        """
        cursor.execute(query, (plate_number, f"%{plate_number}%" if plate_number else None, status, status, limit, offset))

        result : list[Vehicle] = []
        for row in cursor:
            result.append(Vehicle(**row))
        # Always close cursor
        cursor.close()
        # Return the connection to the pool
        self.pool.putconn(conn)
        return result, count

    # Purpose: Return one vehicle by ID.
    # Validations and business rules: vehicle_id must be a positive integer.
    def get_vehicle_by_ID(self, vehicle_id) -> Optional[Vehicle]:
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        query = """
            Select *
            From vehicle
            Where vehicle_id = %s
        """
        cursor.execute(query, (vehicle_id,))

        result : Optional[Vehicle] = None
        result = cursor.fetchone()
        # Always close cursor
        cursor.close()
        # Return the connection to the pool
        self.pool.putconn(conn)
        return result

    # Purpose: Partially or fully update a vehicle. 
    def update_vehicle(self, vehicle_id, vehicle):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        # Retrieve the existing vehicle
        cursor.execute("SELECT * FROM vehicle WHERE vehicle_id = %s",(vehicle_id,))

        current = cursor.fetchone()
        if current is None:
            cursor.close()
            self.pool.putconn(conn)
            return None

        # Merge existing values with updated values
        updates = vehicle.model_dump(exclude_unset=True)
        merged = dict(current)
        merged.update(updates)
        merged["vehicle_id"] = vehicle_id

        query = """
            Update vehicle
            set vehicle_type_id  = %(vehicle_type_id)s,
                vehicle_status_id  = %(vehicle_status_id)s,
                plate_number  = %(plate_number)s,
                make  = %(make)s,
                model  = %(model)s,
                year  = %(year)s
            Where vehicle_id = %(vehicle_id)s
            Returning *
        """
        
        cursor.execute(query, merged)

        row = cursor.fetchone()

        conn.commit()
        # Always close cursor
        cursor.close()
        # Return the connection to the pool
        self.pool.putconn(conn)
        return Vehicle(**row)

    def delete_vehicle(self, vehicle):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        query = """
            Delete From vehicle
            where vehicle_id = %s
            returning vehicle_id
        """
        try:
            cursor.execute(query, (vehicle,))
            rows = cursor.fetchone()

            if rows is None:
                return None
            
            conn.commit()

            return rows
        
        except psycopg2.errors.ForeignKeyViolation:
            conn.rollback()
            return "Conflict"
        
        finally:
            # Always close cursor
            cursor.close()
            # Return the connection to the pool
            self.pool.putconn(conn)

    def get_current_location(self, vehicle_id):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        query = """
            SELECT
                v.vehicle_id,
                v.plate_number,
                vs.name AS status,
                vk.name AS vehicle_kind,
                ft.name AS fuel_type,
                vt.emissions_rating,
                lp.ts AS last_ts,
                ST_AsGeoJSON(lp.geom) AS last_geom,
                lp.speed_kph,
                lp.heading_deg

            FROM vehicle AS v

            INNER JOIN location_ping AS lp
                ON v.vehicle_id = lp.vehicle_id

            INNER JOIN vehicle_status AS vs
                ON v.vehicle_status_id = vs.vehicle_status_id

            INNER JOIN vehicle_type AS vt
                ON v.vehicle_type_id = vt.vehicle_type_id

            INNER JOIN vehicle_kind AS vk
                ON vt.vehicle_kind_id = vk.vehicle_kind_id

            INNER JOIN fuel_type AS ft
                ON vt.fuel_type_id = ft.fuel_type_id

            WHERE v.vehicle_id = %s
            ORDER BY lp.ts DESC, lp.ping_id DESC
            LIMIT 1
        """
        cursor.execute(query, (vehicle_id,))
        row = cursor.fetchone()
    
        # Always close cursor
        cursor.close()
        # Return the connection to the pool
        self.pool.putconn(conn)

        if row is None:
            return None

        result = dict(row)
        result["last_geom"] = json.loads(result["last_geom"])

        return result

    def check_vehicle_status_id(self, vehicle_status_id) :
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        query = """
            Select 1
            From vehicle_status
            Where vehicle_status_id = %s
        """
        cursor.execute(query, (vehicle_status_id,))

        result = cursor.fetchone()
        # Always close cursor
        cursor.close()
        # Return the connection to the pool
        self.pool.putconn(conn)
        return result is not None

    def check_vehicle_type_id(self, vehicle_type_id) :
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        query = """
            Select 1
            From vehicle_type
            Where vehicle_type_id = %s
        """
        cursor.execute(query, (vehicle_type_id,))

        result = cursor.fetchone()
        # Always close cursor
        cursor.close()
        # Return the connection to the pool
        self.pool.putconn(conn)
        return result is not None

    def check_plate_number(self, plate_number, vehicle_id):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        query = """
            Select 1
            From vehicle
            Where plate_number = %s AND vehicle_id != %s
        """
        cursor.execute(query, (plate_number, vehicle_id))
        result = cursor.fetchone()
        # Always close cursor
        cursor.close()
        # Return the connection to the pool
        self.pool.putconn(conn)
        return result is not None
    
    # Purpose: Check if a plate number already exists for POST.
    def check_new_plate_number(self, plate_number):
        # Get Connection from pool
        conn = self.pool.getconn()
        # Now get the cursor. Instead of creating a new one, we use an existing one
        cursor = conn.cursor(cursor_factory=DictCursor)

        query = """
            Select 1
            From vehicle
            Where plate_number = %s
        """

        cursor.execute(query, (plate_number,))
        result = cursor.fetchone()

        cursor.close()
        self.pool.putconn(conn)

        return result is not None
   
