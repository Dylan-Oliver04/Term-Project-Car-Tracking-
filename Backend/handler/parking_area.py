from dao.parking_area import ParkingAreaDao, ParkingAreaCreate, ParkingAreaUpdate
from fastapi import HTTPException
import math


class ParkingAreaHandler:
    def create_parking_area(self, area):
        data = area.model_dump()

        if not data["name"].strip():
            raise HTTPException(status_code=400, detail="name cannot be empty.")
        data["name"] = data["name"].strip()

        if data["capacity"] is not None and data["capacity"] < 0:
            raise HTTPException(status_code=400, detail="capacity cannot be negative.")

        if data["geom"].get("type") != "Polygon":
            raise HTTPException(status_code=400, detail="geom must be a Polygon.")

        dao = ParkingAreaDao()
        if not dao.check_geometry(data["geom"]):
            raise HTTPException(status_code=400, detail="Invalid Polygon geometry.")

        return dao.create_parking_area(ParkingAreaCreate(**data))

    def get_parking_areas(self, limit, offset, name, bbox):
        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="limit and offset must be non-negative.")

        bbox_values = None
        if bbox is not None:
            try:
                bbox_values = [float(value) for value in bbox.split(",")]
            except ValueError:
                raise HTTPException(status_code=400, detail="bbox must contain four numbers.")

            if len(bbox_values) != 4:
                raise HTTPException(status_code=400, detail="bbox must contain four numbers.")
            if not all(math.isfinite(value) for value in bbox_values):
                raise HTTPException(status_code=400, detail="bbox values must be finite.")

            min_lon, min_lat, max_lon, max_lat = bbox_values
            if not (-180 <= min_lon < max_lon <= 180 and -90 <= min_lat < max_lat <= 90):
                raise HTTPException(status_code=400, detail="Invalid bbox coordinates.")

        dao = ParkingAreaDao()
        areas, count = dao.get_parking_areas(limit, offset, name, bbox_values)
        return {"items": areas, "limit": limit, "offset": offset, "count": count}

    def get_parking_area_by_ID(self, parking_area_id):
        if parking_area_id <= 0:
            raise HTTPException(status_code=400, detail="parking_area_id must be positive.")

        dao = ParkingAreaDao()
        result = dao.get_parking_area_by_ID(parking_area_id)
        if result is None:
            raise HTTPException(status_code=404, detail="parking_area_id does not exist.")
        return result

    def update_parking_area(self, parking_area_id, area):
        if parking_area_id <= 0:
            raise HTTPException(status_code=400, detail="parking_area_id must be positive.")

        updates = area.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="Empty update payload.")

        if "name" in updates:
            if updates["name"] is None or not updates["name"].strip():
                raise HTTPException(status_code=400, detail="name cannot be empty.")
            updates["name"] = updates["name"].strip()
        if "capacity" in updates:
            if updates["capacity"] is not None and updates["capacity"] < 0:
                raise HTTPException(status_code=400, detail="capacity cannot be negative.")
        if "geom" in updates:
            if updates["geom"] is None or updates["geom"].get("type") != "Polygon":
                raise HTTPException(status_code=400, detail="geom must be a Polygon.")

        dao = ParkingAreaDao()
        existing = dao.get_parking_area_by_ID(parking_area_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="parking_area_id does not exist.")

        if "geom" in updates and not dao.check_geometry(updates["geom"]):
            raise HTTPException(status_code=400, detail="Invalid Polygon geometry.")

        return dao.update_parking_area(parking_area_id, ParkingAreaUpdate(**updates))

    def delete_parking_area(self, parking_area_id):
        if parking_area_id <= 0:
            raise HTTPException(status_code=400, detail="parking_area_id must be positive.")

        dao = ParkingAreaDao()
        result = dao.delete_parking_area(parking_area_id)
        if result is None:
            raise HTTPException(status_code=404, detail="parking_area_id does not exist.")
        return {"message": "Parking area deleted successfully.",
                "parking_area_id": result["parking_area_id"]}
