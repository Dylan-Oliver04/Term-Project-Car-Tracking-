create table vehicle_kind (vehicle_kind_id bigint primary key, name text);

create table fuel_type (fuel_type_id bigint primary key, name text);

create table vehicle_status (vehicle_status_id bigint primary key, name text);

create table vehicle_type (
    vehicle_type_id bigint primary key, 
    vehicle_kind_id bigint references vehicle_kind(vehicle_kind_id),
    fuel_type_id bigint references fuel_type(fuel_type_id),
    emissions_rating double precision,
    created_at timestamp
);

create table parking_area (
    parking_area_id bigint primary key,
    name text,
    capacity bigint,
    geom geometry(polygon,4326),
    created_at timestamp
);

create table vehicle (
    vehicle_id bigint primary key,
    vehicle_type_id bigint references vehicle_type(vehicle_type_id),
    vehicle_status_id bigint references vehicle_status(vehicle_status_id),
    plate_number text, 
    make text, 
    model text, 
    year bigint, 
    created_at timestamp
);

create table road_segment (
    road_id bigint primary key,
    name text,
    speed_limit_kph bigint,
    geom geometry(linestring,4326),
    created_at timestamp,
    is_oneway boolean,
    direction text
);

create table driver (
    driver_id bigint primary key,
    first_name text,
    last_name text,
    license_number text,
    hired_at timestamp
);

create table location_ping (
    ping_id bigint primary key,
    vehicle_id bigint references vehicle(vehicle_id),
    ts timestamp,
    geom geometry(point,4326),
    speed_kph double precision,
    heading_deg double precision
);

create table vehicle_assignment (
    assignment_id bigint primary key,
    vehicle_id bigint references vehicle(vehicle_id),
    driver_id bigint references driver(driver_id),
    assigned_from timestamp,
    assigned_to timestamp
);

create table trip (
    trip_id bigint primary key,
    vehicle_id bigint references vehicle(vehicle_id),
    start_ts timestamp,
    end_ts timestamp,
    start_geom geometry(point,4326),
    end_geom geometry(point,4326),
    distance_km double precision
);


