
import json
from datetime import datetime, timezone

from fastapi import HTTPException
from psycopg2 import errors

from dao.driver import UPDATABLE, DriverDAO


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
    # En Python, True/False son int; no los aceptamos como enteros.
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
    """El id debe ser entero positivo; si no, no puede existir -> 404."""
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



TEXT_FIELDS = ("first_name", "last_name", "license_number")


def to_json(row):
    return {
        "driver_id": row["driver_id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "license_number": row["license_number"],
        "hired_at": format_ts(row["hired_at"]),
    }


def _clean_field(field, value):
    """Valida un campo ya presente en el body. null / tipo malo / vacio -> 422."""
    if value is None:
        raise unprocessable(f"{field} cannot be null.")
    if field in TEXT_FIELDS:
        if not isinstance(value, str) or not value.strip():
            raise unprocessable(f"{field} must be a non-empty string.")
        return value.strip()
    if field == "hired_at":
        ts = parse_ts(value)
        if ts is None:
            raise unprocessable("hired_at must be a valid RFC 3339 timestamp.")
        return ts
    return value


class DriverHandler:

    def get_drivers(self, query_params):
        limit, offset = parse_pagination(query_params)
        name = query_params.get("name")
        license_number = query_params.get("license_number")
        name = name.strip() if name and name.strip() else None
        license_number = license_number.strip() if license_number and license_number.strip() else None

        rows, total = DriverDAO().get_drivers(name, license_number, limit, offset)
        return {
            "items": [to_json(r) for r in rows],
            "limit": limit,
            "offset": offset,
            "count": total,
        }

    def get_driver_by_id(self, driver_id_raw):
        driver_id = parse_path_id(driver_id_raw, "driver_id")
        row = DriverDAO().get_driver_by_id(driver_id)
        if row is None:
            raise not_found("driver_id does not exist.")
        return to_json(row)

    def create_driver(self, raw_body):
        body = parse_json_object(raw_body)

        data = {}
        for field in ("first_name", "last_name", "license_number", "hired_at"):
            if field not in body:
                raise bad_request(f"{field} is required.")
            data[field] = _clean_field(field, body[field])

        dao = DriverDAO()
        if dao.license_exists(data["license_number"]):
            raise conflict("license_number already exists.")
        try:
            row = dao.create_driver(data)
        except errors.UniqueViolation:
            raise conflict("license_number already exists.")
        return to_json(row)

    def update_driver(self, driver_id_raw, raw_body):
        driver_id = parse_path_id(driver_id_raw, "driver_id")
        body = parse_json_object(raw_body)
        if not body:
            raise bad_request("At least one updatable field must be supplied.")

        dao = DriverDAO()
        if dao.get_driver_by_id(driver_id) is None:
            raise not_found("driver_id does not exist.")

        fields = {f: _clean_field(f, body[f]) for f in UPDATABLE if f in body}
        if not fields:
            raise bad_request("At least one updatable field must be supplied.")

        if "license_number" in fields and dao.license_exists(fields["license_number"], driver_id):
            raise conflict("license_number already belongs to another driver.")
        try:
            row = dao.update_driver(driver_id, fields)
        except errors.UniqueViolation:
            raise conflict("license_number already belongs to another driver.")
        if row is None:
            raise not_found("driver_id does not exist.")
        return to_json(row)

    def delete_driver(self, driver_id_raw):
        driver_id = parse_path_id(driver_id_raw, "driver_id")
        dao = DriverDAO()
        if dao.get_driver_by_id(driver_id) is None:
            raise not_found("driver_id does not exist.")
        if dao.has_assignments(driver_id):
            raise conflict("The driver is referenced by a vehicle assignment. Delete those assignments first.")
        try:
            deleted = dao.delete_driver(driver_id)
        except errors.ForeignKeyViolation:
            raise conflict("The driver is referenced by another record.")
        if not deleted:
            raise not_found("driver_id does not exist.")
        return {"message": "Driver deleted successfully.", "driver_id": driver_id}
