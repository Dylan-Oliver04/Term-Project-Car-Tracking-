from dao.trip import TripDAO, Trip, TripUpdate
from fastapi import HTTPException
import math


class TripHandler:
    def validate_trip_id(self, trip_id):
        if trip_id <= 0:
            raise HTTPException(
                status_code=400,
                detail="trip_id must be a positive integer."
            )

    def validate_time_range(self, from_ts, to_ts):
        if from_ts is not None and to_ts is not None:
            if from_ts > to_ts:
                raise HTTPException(
                    status_code=400,
                    detail="from_ts must be earlier than to_ts."
                )

    def validate_pagination(self, limit, offset):
        if limit < 0 or offset < 0:
            raise HTTPException(
                status_code=400,
                detail="limit and offset must be non-negative."
            )


    def validate_geometry(self, dao, geometry, status=400):
        if geometry is not None and not dao.check_geometry(geometry):
            raise HTTPException(status_code=status,
                                detail="Geometry must be a valid GeoJSON Point.")


# POST /api/v1/trips
#  Purpose: Create a new trip. 
    def create_trip(self, new_trip: Trip):
        dao = TripDAO()
        if new_trip.vehicle_id <= 0:
            raise HTTPException(status_code=400, detail="vehicle_id must be positive.")

        if new_trip.end_ts <= new_trip.start_ts:
            raise HTTPException(status_code=400, detail="end_ts must be later than start_ts.")

        if new_trip.distance_km is not None and new_trip.distance_km < 0:
            raise HTTPException(status_code=400, detail="distance_km must be greater than or equal to zero.")

        self.validate_geometry(dao, new_trip.start_geom)
        self.validate_geometry(dao, new_trip.end_geom)

        if not dao.vehicle_exists(new_trip.vehicle_id):
            raise HTTPException(status_code=404, detail="Vehicle does not exist.")

        return dao.get_trip_by_id(dao.create_trip(new_trip))


 
# GET /api/v1/trips 
# Purpose: Return a paginated list of trips. Optional filters may include vehicle_id and time interval. 
    def get_all_trips(self, vehicle_id=None, from_ts=None,to_ts=None,limit=50,offset=0):
        dao = TripDAO()
        if vehicle_id is not None and vehicle_id <= 0:
            raise HTTPException(status_code=400,detail="vehicle_id must be a positive integer.")
        
        self.validate_time_range(from_ts, to_ts)
        self.validate_pagination(limit, offset)
        
        return dao.get_all_trips(vehicle_id, from_ts, to_ts, limit, offset)

    

# GET /api/v1/trips/{trip_id} 
# Purpose: Return one trip by ID. 
    def get_trip_by_id(self, trip_id):
        self.validate_trip_id(trip_id)
        dao = TripDAO()
        result = dao.get_trip_by_id(trip_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        return result


# PUT /api/v1/trips/{trip_id} Purpose: 
# Partially or fully update a trip.  
    def update_trip(self, trip_id, trip):
        dao = TripDAO()
        if trip_id <= 0:
            raise HTTPException(status_code=400,detail="trip_id must be positive.")
        existing = dao.get_trip_by_id(trip_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        data = trip.model_dump(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400,detail="Update payload cannot be empty.")
        if "vehicle_id" in data:
            if data["vehicle_id"] is None or data["vehicle_id"] <= 0:
                raise HTTPException(status_code=422,detail="vehicle_id must be positive.")
        
            if not dao.vehicle_exists(data["vehicle_id"]):
                raise HTTPException(status_code=404,detail="Referenced vehicle does not exist.")
        
        start_ts = data.get("start_ts", existing.start_ts)
        end_ts = data.get("end_ts", existing.end_ts)
        
        if start_ts is None or end_ts is None or end_ts <= start_ts:
            raise HTTPException(status_code=422, detail="end_ts must be later than start_ts.")

        if "distance_km" in data:
            distance = data["distance_km"]
            if (distance is not None and distance < 0):
                raise HTTPException(status_code=422, detail="distance_km cannot be negative.")
        self.validate_geometry(dao, data.get("start_geom"), status=422)
        self.validate_geometry(dao, data.get("end_geom"), status=422)
        result = dao.update_trip(trip_id, trip)
        if result is None:
            raise HTTPException(status_code=422,detail="Trip could not be updated.")
        return result
    


# DELETE /api/v1/trips/{trip_id} 
# Purpose: Delete a trip. . 
    def delete_trip(self, trip_id):
        self.validate_trip_id(trip_id)
        dao = TripDAO()
        result = dao.delete_trip(trip_id)
        if result is None:
            raise HTTPException(status_code=404, detail="trip_id does not exist.")
        else:
            return {"message": "Trip deleted successfully.","trip_id": result}

# GET /api/v1/vehicles/{vehicle_id}/trips
#  Purpose: Return the trips associated with one vehicle. 
    def get_trip_by_vehicle_id(self,vehicle_id,limit=50,offset=0,from_ts=None,to_ts=None):
        dao = TripDAO()
        if vehicle_id <= 0:
            raise HTTPException(status_code=400,detail="vehicle_id must be positive.")
        
        if not dao.vehicle_exists(vehicle_id):
            raise HTTPException(status_code=404,detail="Vehicle does not exist.")
        self.validate_time_range(from_ts, to_ts)
        self.validate_pagination(limit, offset)
        
        return dao.get_trip_by_vehicle_id(vehicle_id,limit,offset,from_ts,to_ts)
