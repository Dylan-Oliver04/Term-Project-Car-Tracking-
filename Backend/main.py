from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from datetime import datetime
import json

# Import DAO Api Specifications from dao folder
from dao.vehicle import Vehicle, VehicleUpdate, VehicleCreate
from dao.road_segment import RoadSegmentCreate, RoadSegmentUpdate
from dao.parking_area import ParkingAreaCreate, ParkingAreaUpdate
from dao.location_ping import Location_Ping, Location_Ping_Update
from dao.trip import Trip, TripUpdate
from dao.vehicle_assigment import VehicleAssignmentDAO, VehicleAssignmentCreate, VehicleAssignmentUpdate
from dao.driver import DriverDAO, DriverCreate, DriverUpdate


# Import Handler Api Specifications from handler folder
from handler.vehicle import VehicleHandler
from handler.road_segment import RoadSegmentHandler
from handler.parking_area import ParkingAreaHandler
from handler.vehicle_assigment import VehicleAssignmentHandler
from handler.location_ping import Location_Ping_Handler
from handler.trip import TripHandler
from handler.driver import DriverDAO, DriverHandler

app = FastAPI()

origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5.1 Vehicle
@app.post("/api/v1/vehicles", status_code=201)
async def create_vehicle(vehicle_data: VehicleCreate):
    return VehicleHandler().create_vehicle(vehicle_data)

@app.get("/api/v1/vehicles")
async def get_vehicles(limit : int = 20, offset : int = 0, status : int | None = None,plate_number : str | None = None):
    return VehicleHandler().get_vehicles(limit, offset, status,plate_number)

@app.get("/api/v1/vehicles/{vehicle_id}")
async def get_vehicle_by_ID(vehicle_id : int):
    return VehicleHandler().get_vehicle_by_ID(vehicle_id)

@app.put("/api/v1/vehicles/{vehicle_id}")
async def update_vehicle(vehicle_id : int, vehicle_data : VehicleUpdate):
    return VehicleHandler().update_vehicle(vehicle_id, vehicle_data)

@app.delete("/api/v1/vehicles/{vehicle_id}")
async def delete_vehicle(vehicle_id : int):
    return VehicleHandler().delete_vehicle(vehicle_id)

@app.get("/api/v1/vehicles/{vehicle_id}/current-location")
async def get_current_location(vehicle_id: int):
    return VehicleHandler().get_current_location(vehicle_id)


#5.2 Road Segment
@app.post("/api/v1/road-segments", status_code=201)
async def create_road_segment(segment_data: RoadSegmentCreate):
    return RoadSegmentHandler().create_road_segment(segment_data)

@app.get("/api/v1/road-segments")
async def get_road_segments(limit: int = 20, offset: int = 0, name: str | None = None, 
                            min_speed_kph: int | None = None, max_speed_kph: int | None = None, bbox: str | None = None):
    return RoadSegmentHandler().get_road_segments( limit, offset, name, min_speed_kph, max_speed_kph, bbox)

@app.get("/api/v1/road-segments/geojson")
async def get_road_segments_geojson(limit: int = 15000, offset: int = 0, name: str | None = None,
                                   min_speed_kph: int | None = None,max_speed_kph: int | None = None):
    result = RoadSegmentHandler().get_road_segments_geojson(limit, offset, name, min_speed_kph, max_speed_kph)
    return JSONResponse(content=jsonable_encoder(result), media_type="application/geo+json")

@app.get("/api/v1/road-segments/{road_id}")
async def get_road_segment_by_ID(road_id: int):
    return RoadSegmentHandler().get_road_segment_by_ID(road_id)

@app.put("/api/v1/road-segments/{road_id}")
async def update_road_segment(road_id: int, segment_data: RoadSegmentUpdate):
    return RoadSegmentHandler().update_road_segment(road_id, segment_data)

@app.delete("/api/v1/road-segments/{road_id}")
async def delete_road_segment(road_id: int):
    return RoadSegmentHandler().delete_road_segment(road_id)


#5.3 Parking Area
@app.post("/api/v1/parking-areas", status_code=201)
async def create_parking_area(area_data: ParkingAreaCreate):
    return ParkingAreaHandler().create_parking_area(area_data)

@app.get("/api/v1/parking-areas")
async def get_parking_areas(limit: int = 20, offset: int = 0, name: str | None = None, bbox: str | None = None):
    return ParkingAreaHandler().get_parking_areas(limit, offset, name, bbox)

@app.get("/api/v1/parking-areas/{parking_area_id}")
async def get_parking_area_by_ID(parking_area_id: int):
    return ParkingAreaHandler().get_parking_area_by_ID(parking_area_id)

@app.put("/api/v1/parking-areas/{parking_area_id}")
async def update_parking_area(parking_area_id: int, area_data: ParkingAreaUpdate):
    return ParkingAreaHandler().update_parking_area(parking_area_id, area_data)

@app.delete("/api/v1/parking-areas/{parking_area_id}")
async def delete_parking_area(parking_area_id: int):
    return ParkingAreaHandler().delete_parking_area(parking_area_id)

#5.4 Location Ping
@app.post("/api/v1/location-pings", status_code=201)
async def create_location_ping(ping_data: Location_Ping):
    return Location_Ping_Handler().create_location_ping(ping_data)

@app.get("/api/v1/location-pings")
async def get_location_pings(vehicle_id: int | None = None, from_ts: datetime | None = None,
                             to_ts: datetime | None = None, bbox: str | None = None,
                             limit: int = 100, offset: int = 0):
    return Location_Ping_Handler().get_all_location_pings(
        vehicle_id=vehicle_id, from_ts=from_ts, to_ts=to_ts, bbox=bbox, limit=limit, offset=offset)

@app.get("/api/v1/location-pings/{ping_id}")
async def get_location_ping_by_ID(ping_id: int):
    return Location_Ping_Handler().get_location_ping_by_id(ping_id)

@app.put("/api/v1/location-pings/{ping_id}")
async def update_location_ping(ping_id: int, ping_data: Location_Ping_Update):
    return Location_Ping_Handler().update_location_ping(ping_id, ping_data)

@app.delete("/api/v1/location-pings/{ping_id}")
async def delete_location_ping(ping_id: int):
    return Location_Ping_Handler().delete_location_ping(ping_id)

@app.get("/api/v1/vehicles/{vehicle_id}/pings")
async def get_vehicle_pings(vehicle_id: int, limit: int = 100, offset: int = 0,
                            from_ts: datetime | None = None, to_ts: datetime | None = None):
    return Location_Ping_Handler().get_location_ping_by_vehicle_id(
        vehicle_id, limit=limit, offset=offset, from_ts=from_ts, to_ts=to_ts)


#5.5 Trip
@app.post("/api/v1/trips", status_code=201)
async def create_trip(trip_data: Trip):
    return TripHandler().create_trip(trip_data)

@app.get("/api/v1/trips")
async def get_trips(vehicle_id: int | None = None, from_ts: datetime | None = None,
                    to_ts: datetime | None = None, limit: int = 50, offset: int = 0):
    return TripHandler().get_all_trips(
        vehicle_id=vehicle_id, from_ts=from_ts, to_ts=to_ts, limit=limit, offset=offset)

@app.get("/api/v1/trips/{trip_id}")
async def get_trip_by_ID(trip_id: int):
    return TripHandler().get_trip_by_id(trip_id)

@app.put("/api/v1/trips/{trip_id}")
async def update_trip(trip_id: int, trip_data: TripUpdate):
    return TripHandler().update_trip(trip_id, trip_data)

@app.delete("/api/v1/trips/{trip_id}")
async def delete_trip(trip_id: int):
    return TripHandler().delete_trip(trip_id)

@app.get("/api/v1/vehicles/{vehicle_id}/trips")
async def get_vehicle_trips(vehicle_id: int, limit: int = 50, offset: int = 0,
                            from_ts: datetime | None = None, to_ts: datetime | None = None):
    return TripHandler().get_trip_by_vehicle_id(
        vehicle_id, limit=limit, offset=offset, from_ts=from_ts, to_ts=to_ts)


# 5.6 Driver
@app.post("/api/v1/drivers", status_code=201)
async def create_driver(request: DriverCreate):
    data = request.model_dump()
    return DriverHandler().create_driver(json.dumps(data).encode("utf-8"))

@app.get("/api/v1/drivers")
async def get_drivers(limit: int = 20, offset: int = 0, name: str | None = None, license_number: str | None = None):
    params = {"limit": limit, "offset": offset, "name": name, "license_number": license_number}
    return DriverHandler().get_drivers(params)

@app.get("/api/v1/drivers/{driver_id}")
async def get_driver_by_ID(driver_id: int):
    return DriverHandler().get_driver_by_id(driver_id)

@app.put("/api/v1/drivers/{driver_id}")
async def update_driver(driver_id: str, request: DriverUpdate):
    data = request.model_dump(exclude_unset=True)
    return DriverHandler().update_driver(driver_id, json.dumps(data).encode("utf-8"))

@app.delete("/api/v1/drivers/{driver_id}")
async def delete_driver(driver_id: str):
    return DriverHandler().delete_driver(driver_id)


# 5.7 Vehicle Assignment
@app.post("/api/v1/vehicle-assignments", status_code=201)
async def create_vehicle_assignment(request: VehicleAssignmentCreate):
    data = request.model_dump()
    return VehicleAssignmentHandler().create_assignment(json.dumps(data).encode("utf-8"))

@app.get("/api/v1/vehicle-assignments")
async def get_vehicle_assignments(limit: int = 20, offset: int = 0, vehicle_id: int | None = None, driver_id: int | None = None, active: bool | None = None):
    params = {"limit": limit, "offset": offset, "vehicle_id": vehicle_id, "driver_id": driver_id, "active": str(active).lower() if active is not None else None}
    return VehicleAssignmentHandler().get_assignments(params)

@app.get("/api/v1/vehicle-assignments/{assignment_id}")
async def get_vehicle_assignment_by_ID(assignment_id: str):
    return VehicleAssignmentHandler().get_assignment_by_id(assignment_id)

@app.put("/api/v1/vehicle-assignments/{assignment_id}")
async def update_vehicle_assignment(assignment_id: str, request: VehicleAssignmentUpdate):
    data = request.model_dump(exclude_unset=True)
    return VehicleAssignmentHandler().update_assignment(assignment_id, json.dumps(data).encode("utf-8"))

@app.delete("/api/v1/vehicle-assignments/{assignment_id}")
async def delete_vehicle_assignment(assignment_id: str):
    return VehicleAssignmentHandler().delete_assignment(assignment_id)

