from dao.vehicle import VehicleDao, Vehicle, VehicleUpdate, VehicleCreate
from fastapi import HTTPException, Response

# Validations and business rules from PDF
# limit and offset must be non-negative integers.
# status filter is optional and may be provided as a status name or status ID, depending on the implementation.
# plate_number filter is optional, supports partial matching.
class VehicleHandler:
    def create_vehicle(self, vehicle):

        data = vehicle.model_dump()

        if not data["plate_number"].strip():
            raise HTTPException(status_code=400,detail="Malformed JSON or invalid payload shape." )


        if data["year"] is None or data["year"] < 1950 or data["year"] > 2100:
             raise HTTPException(status_code=400, detail="Malformed JSON or empty payload.")

        dao = VehicleDao()

        if "plate_number" in data:
            if dao.check_new_plate_number(data["plate_number"]):
                raise HTTPException(status_code=409, detail="Updated plate_number conflicts with another vehicle.")

        if "vehicle_type_id" in data:
            if not dao.check_vehicle_type_id(data["vehicle_type_id"]):
                raise HTTPException(status_code=404, detail="vehicle_id or referenced foreign key does not exist")

        if "vehicle_status_id" in data:
            if not dao.check_vehicle_status_id(data["vehicle_status_id"]):
                        raise HTTPException(status_code=404, detail="vehicle_id or referenced foreign key does not exist")

        result = dao.create_vehicle(VehicleCreate(**data))
        return result

    def get_vehicles(self, limit, offset, status,plate_number):
        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400,detail="Invalid query parameter values." )
            
        dao = VehicleDao()
        vehicles,count = dao.get_vehicles(limit, offset, status,plate_number)
        
        return {"items" : vehicles, "limit" : limit, "offset" : offset, "count" : count}
        # return {"Vehicleid" : 1, "VehicleName" : "Cooked"}

    def get_vehicle_by_ID(self, vehicle_id):
        if vehicle_id < 0:
            raise HTTPException(status_code=400,detail="Invalid query parameter values." )
            
        dao = VehicleDao()
        vehicle = dao.get_vehicle_by_ID(vehicle_id)

        if vehicle is None:
            raise HTTPException(status_code=404,detail="vehicle_id does not exist." )
        return Vehicle(**vehicle)

    def update_vehicle(self, vehicle_id, vehicle):
        if vehicle_id <= 0:
            raise HTTPException(status_code=404,detail="vehicle_id or referenced foreign key does not exist" )
        
        pending_updates = vehicle.model_dump(exclude_unset=True)
        if not pending_updates:
            raise HTTPException(status_code=400,detail="Malformed JSON or empty payload." )

        if "year" in pending_updates:
            if pending_updates["year"] is None or pending_updates["year"] < 1950 or pending_updates["year"] > 2100:
                raise HTTPException(status_code=400, detail="Malformed JSON or empty payload.")

        dao = VehicleDao()
        vehicle_exist = dao.get_vehicle_by_ID(vehicle_id)

        if vehicle_exist is None:
            raise HTTPException(status_code=404,detail="vehicle_id does not exist." )

        if "plate_number" in pending_updates:
            if dao.check_plate_number(pending_updates["plate_number"], vehicle_id):
                raise HTTPException(status_code=409, detail="Updated plate_number conflicts with another vehicle.")

        if "vehicle_type_id" in pending_updates:
            if not dao.check_vehicle_type_id(pending_updates["vehicle_type_id"]):
                raise HTTPException(status_code=404, detail="vehicle_id or referenced foreign key does not exist")

        if "vehicle_status_id" in pending_updates:
            if not dao.check_vehicle_status_id(pending_updates["vehicle_status_id"]):
                        raise HTTPException(status_code=404, detail="vehicle_id or referenced foreign key does not exist")

        if any(value is None for value in pending_updates.values()):
            raise HTTPException(status_code=400,detail="Updated fields cannot be null.")

       
        update = dao.update_vehicle(vehicle_id, vehicle)
        return update

    def delete_vehicle(self, vehicle_id):
        if vehicle_id < 0:
            raise HTTPException(status_code=400,detail="Invalid query parameter values." )
            
        dao = VehicleDao()
        result = dao.delete_vehicle(vehicle_id)

        if result is None:
            raise HTTPException(status_code=404,detail="vehicle_id does not exist." )

        if result == "Conflict":
            raise HTTPException(status_code=409,detail="Deletion is blocked by business rules /foreign key constraints." )
        
        return {
            "message": "Vehicle deleted successfully.",
            "vehicle_id": result["vehicle_id"]
        }

    # Purpose: Return the most recent location of a vehicle.
    def get_current_location(self, vehicle_id):
            if vehicle_id < 0:
                raise HTTPException(status_code=400,detail="vehicle_id is not a positive integer." )

            dao = VehicleDao()
            vehicle_exist = dao.get_vehicle_by_ID(vehicle_id)

            if vehicle_exist is None:
                raise HTTPException(status_code=404,detail="vehicle_id does not exist." )

            location = dao.get_current_location(vehicle_id)

            # Vehicle exists but has no recorded pings
            if location is None:
                return Response(status_code=204)

            return location


