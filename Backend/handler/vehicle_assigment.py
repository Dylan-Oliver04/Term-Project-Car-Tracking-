
import json
from datetime import datetime, timezone

from fastapi import HTTPException
from psycopg2 import errors

from dao.vehicle_assigment import UPDATABLE, VehicleAssignmentDAO


DEFAULT_LIMIT = 20


def bad_request(msg):
    return HTTPException(status_code=400, detail=msg)


def unprocessable(msg):
    return HTTPException(status_code=422, detail=msg)


def not_found(msg):
    return HTTPException(status_code=404, detail=msg)


def conflict(msg):
    return HTTPException(status_code=409, detail=msg)




def parse_json_object(raw: bytes) -> dict:

    if raw is None or not raw.strip():
        raise bad_request("Request body is empty.")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise bad_request("Malformed JSON.")
    if not isinstance(data, dict):
        raise bad_request("Request body must be a JSON object.")
    return data


def is_int(value) -> bool:

    return isinstance(value, int) and not isinstance(value, bool)




def parse_ts(value):

    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text[-1] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    if len(text) < 19 or text[10] not in ("T", "t", " "):
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def format_ts(dt):

    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat() + "Z"




def parse_path_id(value: str, name: str) -> int:

    try:
        n = int(value)
    except (TypeError, ValueError):
        raise not_found(f"{name} does not exist.")
    if n <= 0:
        raise not_found(f"{name} does not exist.")
    return n



def parse_pagination(params) -> tuple[int, int]:
    limit = parse_non_negative_int(params.get("limit"), "limit", DEFAULT_LIMIT)
    offset = parse_non_negative_int(params.get("offset"), "offset", 0)
    return limit, offset


def parse_non_negative_int(value, name, default):
    if value is None:
        return default
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise bad_request(f"{name} must be a non-negative integer.")
    if n < 0:
        raise bad_request(f"{name} must be a non-negative integer.")
    return n


def parse_positive_int_query(value, name):
    if value is None:
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise bad_request(f"{name} must be a positive integer.")
    if n <= 0:
        raise bad_request(f"{name} must be a positive integer.")
    return n


def parse_bool_query(value, name):
    if value is None:
        return None
    v = value.strip().lower()
    if v in ("true", "1"):
        return True
    if v in ("false", "0"):
        return False
    raise bad_request(f"{name} must be true or false.")


# ===== Handler =====
def to_json(row):
    return {
        "assignment_id": row["assignment_id"],
        "vehicle_id": row["vehicle_id"],
        "driver_id": row["driver_id"],
        "assigned_from": format_ts(row["assigned_from"]),
        "assigned_to": format_ts(row["assigned_to"]),
    }


def _clean_field(field, value):

    if field in ("vehicle_id", "driver_id"):
        if not is_int(value) or value <= 0:
            raise bad_request(f"{field} must be a positive integer.")
        return value
    if field == "assigned_from":
        ts = parse_ts(value)
        if ts is None:
            raise bad_request("assigned_from is required and must be a valid RFC 3339 timestamp.")
        return ts
    if field == "assigned_to":
        if value is None:
            return None  # null = asignacion activa
        ts = parse_ts(value)
        if ts is None:
            raise bad_request("assigned_to must be null or a valid RFC 3339 timestamp.")
        return ts
    return value


def _check_interval(assigned_from, assigned_to):
    if assigned_to is not None and assigned_to <= assigned_from:
        raise unprocessable("assigned_to must be later than assigned_from.")


def _check_references(dao, vehicle_id=None, driver_id=None):
    if vehicle_id is not None and not dao.vehicle_exists(vehicle_id):
        raise not_found("vehicle_id does not exist.")
    if driver_id is not None and not dao.driver_exists(driver_id):
        raise not_found("driver_id does not exist.")


class VehicleAssignmentHandler:

    def get_assignments(self, query_params):
        limit, offset = parse_pagination(query_params)
        vehicle_id = parse_positive_int_query(query_params.get("vehicle_id"), "vehicle_id")
        driver_id = parse_positive_int_query(query_params.get("driver_id"), "driver_id")
        active = parse_bool_query(query_params.get("active"), "active")

        rows, total = VehicleAssignmentDAO().get_assignments(vehicle_id, driver_id, active, limit, offset)
        return {
            "items": [to_json(r) for r in rows],
            "limit": limit,
            "offset": offset,
            "count": total,
        }

    def get_assignment_by_id(self, assignment_id_raw):
        assignment_id = parse_path_id(assignment_id_raw, "assignment_id")
        row = VehicleAssignmentDAO().get_assignment_by_id(assignment_id)
        if row is None:
            raise not_found("assignment_id does not exist.")
        return to_json(row)

    def create_assignment(self, raw_body):
        body = parse_json_object(raw_body)

        data = {}
        for field in ("vehicle_id", "driver_id", "assigned_from"):
            if field not in body or body[field] is None:
                raise bad_request(f"{field} is required.")
            data[field] = _clean_field(field, body[field])
        data["assigned_to"] = _clean_field("assigned_to", body.get("assigned_to"))

        dao = VehicleAssignmentDAO()
        _check_references(dao, data["vehicle_id"], data["driver_id"])
        _check_interval(data["assigned_from"], data["assigned_to"])

        try:
            row = dao.create_assignment(data)
        except errors.ForeignKeyViolation:
            raise not_found("Referenced vehicle_id or driver_id does not exist.")
        except errors.CheckViolation:
            raise unprocessable("The assignment time interval is invalid.")
        return to_json(row)

    def update_assignment(self, assignment_id_raw, raw_body):
        assignment_id = parse_path_id(assignment_id_raw, "assignment_id")
        body = parse_json_object(raw_body)
        if not body:
            raise bad_request("At least one updatable field must be supplied.")

        dao = VehicleAssignmentDAO()
        current = dao.get_assignment_by_id(assignment_id)
        if current is None:
            raise not_found("assignment_id does not exist.")

        fields = {}
        for field in UPDATABLE:
            if field in body:
                if field != "assigned_to" and body[field] is None:
                    raise bad_request(f"{field} cannot be null.")
                fields[field] = _clean_field(field, body[field])
        if not fields:
            raise bad_request("At least one updatable field must be supplied.")

        _check_references(dao, fields.get("vehicle_id"), fields.get("driver_id"))


        new_from = fields.get("assigned_from", current["assigned_from"])
        new_to = fields["assigned_to"] if "assigned_to" in fields else current["assigned_to"]
        _check_interval(new_from, new_to)

        try:
            row = dao.update_assignment(assignment_id, fields)
        except errors.ForeignKeyViolation:
            raise not_found("A referenced foreign key does not exist.")
        except errors.CheckViolation:
            raise unprocessable("The resulting assignment interval is invalid.")
        if row is None:
            raise not_found("assignment_id does not exist.")
        return to_json(row)

    def delete_assignment(self, assignment_id_raw):
        assignment_id = parse_path_id(assignment_id_raw, "assignment_id")
        if not VehicleAssignmentDAO().delete_assignment(assignment_id):
            raise not_found("assignment_id does not exist.")
        return {"message": "Vehicle assignment deleted successfully.", "assignment_id": assignment_id}
