from dao.road_segment import RoadSegmentDao, RoadSegmentCreate, RoadSegmentUpdate
from fastapi import HTTPException
import math

class RoadSegmentHandler:
    def create_road_segment(self, segment):

        data = segment.model_dump()

        if not data["name"].strip():
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON")
        data["name"] = data["name"].strip()

        if data["speed_limit_kph"] is not None and data["speed_limit_kph"] < 0:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON")

        if data["direction"] is not None and data["direction"] not in ("both", "forward"):
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON")

        if data["geom"].get("type") != "LineString":
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON")

        dao = RoadSegmentDao()
        if not dao.check_geometry(data["geom"]):
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON")

        return dao.create_road_segment(RoadSegmentCreate(**data))

    def get_road_segments(self, limit, offset, name, min_speed_kph, max_speed_kph, bbox):
        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="limit and offset must be non-negative.")

        if min_speed_kph is not None and min_speed_kph < 0:
            raise HTTPException(status_code=400, detail="min_speed_kph cannot be negative.")
        if max_speed_kph is not None and max_speed_kph < 0:
            raise HTTPException(status_code=400, detail="max_speed_kph cannot be negative.")
        if min_speed_kph is not None and max_speed_kph is not None:
            if min_speed_kph > max_speed_kph:
                raise HTTPException(status_code=400, detail="Minimum speed cannot exceed maximum speed.")

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

        dao = RoadSegmentDao()
        segments, count = dao.get_road_segments(limit, offset, name,
                                                  min_speed_kph, max_speed_kph, bbox_values)
        return {"items": segments, "limit": limit, "offset": offset, "count": count}

    def get_road_segment_by_ID(self, road_id):
        if road_id <= 0:
            raise HTTPException(status_code=400, detail="road_id must be positive.")

        dao = RoadSegmentDao()
        result = dao.get_road_segment_by_ID(road_id)
        if result is None:
            raise HTTPException(status_code=404, detail="road_id does not exist.")
        return result

    def update_road_segment(self, road_id, segment):
        if road_id <= 0:
            raise HTTPException(status_code=400, detail="road_id must be positive.")

        updates = segment.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="Empty update payload.")

        if "name" in updates:
            if updates["name"] is None or not updates["name"].strip():
                raise HTTPException(status_code=400, detail="name cannot be empty.")
            updates["name"] = updates["name"].strip()
        if "speed_limit_kph" in updates:
            if updates["speed_limit_kph"] is not None and updates["speed_limit_kph"] < 0:
                raise HTTPException(status_code=400, detail="speed_limit_kph cannot be negative.")
        if "direction" in updates:
            if updates["direction"] is not None and updates["direction"] not in ("both", "forward"):
                raise HTTPException(status_code=400, detail="direction must be 'both' or 'forward'.")
        if "geom" in updates:
            if updates["geom"] is None or updates["geom"].get("type") != "LineString":
                raise HTTPException(status_code=400, detail="geom must be a LineString.")

        dao = RoadSegmentDao()
        existing = dao.get_road_segment_by_ID(road_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="road_id does not exist.")

        if "geom" in updates and not dao.check_geometry(updates["geom"]):
            raise HTTPException(status_code=400, detail="Invalid LineString geometry.")

        return dao.update_road_segment(road_id, RoadSegmentUpdate(**updates))

    def delete_road_segment(self, road_id):
        if road_id <= 0:
            raise HTTPException(status_code=400, detail="road_id must be positive.")

        dao = RoadSegmentDao()
        result = dao.delete_road_segment(road_id)
        if result is None:
            raise HTTPException(status_code=404, detail="road_id does not exist.")
        return {"message": "Road segment deleted successfully.", "road_id": result["road_id"]}

    def get_road_segments_geojson(self, limit, offset, name, min_speed_kph, max_speed_kph):
        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="limit and offset must be non-negative.")
        if min_speed_kph is not None and min_speed_kph < 0:
            raise HTTPException(status_code=400, detail="min_speed_kph cannot be negative.")
        if max_speed_kph is not None and max_speed_kph < 0:
            raise HTTPException(status_code=400, detail="max_speed_kph cannot be negative.")
        if min_speed_kph is not None and max_speed_kph is not None:
            if min_speed_kph > max_speed_kph:
                raise HTTPException(status_code=400, detail="Minimum speed cannot exceed maximum speed.")

        dao = RoadSegmentDao()
        return dao.get_road_segments_geojson(limit, offset, name, min_speed_kph, max_speed_kph)