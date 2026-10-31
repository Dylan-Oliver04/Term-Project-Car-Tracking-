from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

# Import DAO Api Specifications from dao folder
from dao.vehicle import Vehicle, VehicleUpdate, VehicleCreate
from dao.road_segment import RoadSegmentCreate, RoadSegmentUpdate
from dao.parking_area import ParkingAreaCreate, ParkingAreaUpdate

# Import Handler Api Specifications from handler folder
from handler.vehicle import VehicleHandler
from handler.road_segment import RoadSegmentHandler
from handler.parking_area import ParkingAreaHandler

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


