import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values


#Get path of parquet file
driver_parquet = r'parquet_files\driver.parquet'
fuel_type_parquet = r'parquet_files\fuel_type.parquet'
location_ping_parquet = r'parquet_files\location_ping.parquet'
parking_area_parquet = r'parquet_files\parking_area.parquet'
road_segment_parquet = r'parquet_files\road_segment.parquet'
trip_parquet = r'parquet_files\trip.parquet'
vehicle_assignment_parquet = r'parquet_files\vehicle_assignment.parquet'
vehicle_kind_parquet = r'parquet_files\vehicle_kind.parquet'
vehicle_status_parquet = r'parquet_files\vehicle_status.parquet'
vehicle_type_parquet = r'parquet_files\vehicle_type.parquet'
vehicle_parquet = r'parquet_files\vehicle.parquet'

#Get data from parquet file
driver_data = pd.read_parquet(driver_parquet, engine="auto")
fuel_type_data = pd.read_parquet(fuel_type_parquet, engine="auto")
location_ping_data = pd.read_parquet(location_ping_parquet, engine="auto")
parking_area_data = pd.read_parquet(parking_area_parquet, engine="auto")
road_segment_data = pd.read_parquet(road_segment_parquet, engine="auto")
trip_data = pd.read_parquet(trip_parquet, engine="auto")
vehicle_assignment_data = pd.read_parquet(vehicle_assignment_parquet, engine="auto")
vehicle_kind_data = pd.read_parquet(vehicle_kind_parquet, engine="auto")
vehicle_status_data = pd.read_parquet(vehicle_status_parquet, engine="auto")
vehicle_type_data = pd.read_parquet(vehicle_type_parquet, engine="auto")
vehicle_data = pd.read_parquet(vehicle_parquet, engine="auto")

#List of data
data = [vehicle_kind_data, fuel_type_data, vehicle_status_data, vehicle_type_data, parking_area_data, vehicle_data, road_segment_data, driver_data, location_ping_data, vehicle_assignment_data, trip_data]
table_names =["vehicle_kind", "fuel_type", "vehicle_status", "vehicle_type", "parking_area","vehicle", "road_segment", "driver","location_ping", "vehicle_assignment","trip"]

#Dictionary of data
tables = {
    "vehicle_kind" : vehicle_kind_data,
    "fuel_type" : fuel_type_data ,
    "vehicle_status": vehicle_status_data,
    "vehicle_type": vehicle_type_data, 
    "parking_area": parking_area_data,
    "vehicle": vehicle_data ,
    "road_segment": road_segment_data, 
    "driver": driver_data,
    "location_ping": location_ping_data, 
    "vehicle_assignment": vehicle_assignment_data,
    "trip": trip_data
}


#Get database
DB_CONFIG = {
    "dbname": "dbclass_u0pc",
    "user": "yaniel",
    "password": "ocDOdtffbb27f0NFErKdoEr92gHJCKL6",
    "host": "dpg-davf56uk1f9s73a3cq3g-a.virginia-postgres.render.com",
    "port": 5432,
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

for table in table_names:
    df = tables[table]

    #Skip if table already has data
    if df.empty:
        continue
    #Turn parquet's NaT into NULL
    df = df.astype(object).where(df.notna(), None)
    rows = list(df.itertuples(index=False, name=None))

    #Insert data into table
    query = sql.SQL("insert into {table} ({cols}) values %s on conflict do nothing").format(
        table=sql.Identifier(table),
        cols=sql.SQL(", ").join(sql.Identifier(c) for c in df.columns),
    )
    execute_values(cur, query, rows, page_size=5000)
    
conn.commit()
cur.close()
conn.close()