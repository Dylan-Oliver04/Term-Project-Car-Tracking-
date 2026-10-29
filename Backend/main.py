from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware 

# Import DAO Api Specifications from dao folder
from dao.vehicle import Vehicle, VehicleUpdate, VehicleCreate

# Import Handler Api Specifications from handler folder
from handler.vehicle import VehicleHandler

app = FastAPI()

origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Purpose: Create a new vehicle record.
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