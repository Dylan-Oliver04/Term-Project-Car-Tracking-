from dao.location_ping import Location_PingDAO, Location_Ping, Location_Ping_Update
from fastapi import HTTPException
import math

class Location_Ping_Handler:
    def validate_ping_id(self, ping_id):
        if ping_id <= 0:
            raise HTTPException(
                status_code=400,
                detail="ping_id must be a positive integer."
            )

    def validate_pagination(self, limit, offset):

        if limit < 0 or offset < 0:
            raise HTTPException(
                status_code=400,
                detail="limit and offset must be non-negative."
            )

    def validate_time_range(self, from_ts, to_ts):

        if from_ts is not None and to_ts is not None:
            if from_ts >= to_ts:
                raise HTTPException(
                    status_code=400,
                    detail="from_ts must be earlier than to_ts."
                )

    def validate_bbox(self, bbox):

        if bbox is None:
            return None

        try:
            if isinstance(bbox, str):
                values = bbox.split(",")

            else:
                values = bbox

            if len(values) != 4:
                raise ValueError()

            values = [float(value) for value in values]

            min_lon, min_lat, max_lon, max_lat = values

            if not all(math.isfinite(value) for value in values):
                raise ValueError()

            if not (
                -180 <= min_lon <= 180
                and -180 <= max_lon <= 180
                and -90 <= min_lat <= 90
                and -90 <= max_lat <= 90
            ):
                raise ValueError()

            if min_lon >= max_lon or min_lat >= max_lat:
                raise ValueError()

            return values

        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid bbox. Expected "
                    "minLon,minLat,maxLon,maxLat "
                    "within valid WGS84 ranges."
                )
            )


    def validate_geometry(self, dao, geom):
        if not dao.check_geometry(geom):
            raise HTTPException(
                status_code=400,
                detail="Geometry must be a valid GeoJSON Point."
            )

#     Purpose: Create a new location ping for a vehicle. 
    def create_location_ping(self, new_location_ping : Location_Ping):
        dao = Location_PingDAO()
        if new_location_ping.vehicle_id <= 0:
            raise HTTPException(status_code=400,detail="vehicle_id must be positive.")
        
            
        if new_location_ping.ts is None:
            raise HTTPException(status_code=400,detail="ts is required.")
            
        if new_location_ping.geom is None:
            raise HTTPException(status_code=400,detail="geom is required.")
        self.validate_geometry(dao, new_location_ping.geom)
        if new_location_ping.speed_kph is not None:
            speed = new_location_ping.speed_kph
            if not math.isfinite(speed) or speed < 0:
                raise HTTPException(status_code=400,detail="speed_kph must be greater than or equal to zero.")
    
        if new_location_ping.heading_deg is not None:
            heading = new_location_ping.heading_deg
            if (not math.isfinite(heading) or heading < 0 or heading >= 360):
                raise HTTPException(status_code=400,detail="heading_deg must be between 0 and 360.")
        if not dao.vehicle_exists(new_location_ping.vehicle_id):
            raise HTTPException(status_code=404,detail="Vehicle does not exist.")
        return dao.create_location_ping(new_location_ping)

    
#      Return a paginated list of pings.
    def get_all_location_pings(self,vehicle_id=None, from_ts=None, to_ts=None, bbox=None, limit=100, offset=0):
        dao = Location_PingDAO()
        if vehicle_id is not None and vehicle_id <= 0:
            raise HTTPException(status_code=400,detail="vehicle_id must be a positive integer.")
        self.validate_time_range(from_ts, to_ts)
        self.validate_pagination(limit, offset)
        bbox = self.validate_bbox(bbox)
        return dao.get_all_location_pings(vehicle_id,from_ts,to_ts,bbox,limit,offset)


   
# GET /api/v1/location-pings/{ping_id}
    def get_location_ping_by_id(self, ping_id):
        self.validate_ping_id(ping_id)
        
        dao = Location_PingDAO()
        result = dao.get_location_ping_by_id(ping_id)
        if result is None:
            raise HTTPException(status_code=404, detail="ping_id does not exist.")
        return result

    
#  PUT /api/v1/location-pings/{ping_id} 
# Purpose: Partially or fully update a ping. 
    def update_location_ping(self, ping_id, location_ping:  Location_Ping_Update):
        self.validate_ping_id(ping_id)
        dao = Location_PingDAO()
        existing = dao.get_location_ping_by_id(ping_id)
        if existing is None:
            raise HTTPException(status_code=404,detail="Location ping does not exist.")
        data = location_ping.model_dump(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400,detail="Update payload cannot be empty.")

        if "vehicle_id" in data:
            if data["vehicle_id"] is None or data["vehicle_id"] <= 0:
                raise HTTPException(status_code=400,detail="vehicle_id must be positive.")

            if not dao.vehicle_exists(data["vehicle_id"]):
                raise HTTPException(status_code=404,detail="Referenced vehicle does not exist.")

        if "ts" in data and data["ts"] is None:
            raise HTTPException(status_code=400,detail="ts cannot be null.")

        if "geom" in data:
            if data["geom"] is None:
                raise HTTPException(status_code=400,detail="geom cannot be null.")
            self.validate_geometry(dao, data["geom"])

        if "speed_kph" in data:
            speed = data["speed_kph"]

            if (speed is not None and (not math.isfinite(speed) or speed < 0)):
                raise HTTPException(status_code=400,detail="speed_kph cannot be negative.")

        if "heading_deg" in data:
            heading = data["heading_deg"]

            if (heading is not None and (not math.isfinite(heading) or heading < 0 or heading >= 360)):
                raise HTTPException(status_code=400,detail="heading_deg must be within [0, 360).")

        result = dao.update_location_ping(ping_id, location_ping)

        if result is None:
            raise HTTPException(status_code=404,detail="Location ping does not exist.")

        return result


    # DELETE /api/v1/location-pings/{ping_id}
    #  Purpose: Delete a ping. 
    def delete_location_ping(self, ping_id):
        self.validate_ping_id(ping_id)
        dao = Location_PingDAO()
        deleted_id = dao.delete_location_ping(ping_id)
        if deleted_id is None:
            raise HTTPException(status_code=404,detail="Location ping does not exist.")
        else:
            return {"message": "Location ping deleted successfully.","ping_id": deleted_id}
    
    
    # GET /api/v1/vehicles/{vehicle_id}/pings 
    # Purpose: Return the pings associated with one vehicle. 
    def get_location_ping_by_vehicle_id(self,vehicle_id,limit=100,offset=0,from_ts=None,to_ts=None):
        dao = Location_PingDAO()
        if vehicle_id <= 0:
            raise HTTPException(status_code=400,detail="vehicle_id must be positive.")
    
        if not dao.vehicle_exists(vehicle_id):
            raise HTTPException(status_code=404,detail="Vehicle does not exist.")
    
        self.validate_time_range(from_ts, to_ts)
        self.validate_pagination(limit, offset)
    
        return dao.get_location_ping_by_vehicle_id(vehicle_id,limit,offset,from_ts,to_ts)
    

   