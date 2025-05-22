import datetime
import os
from typing import Literal, TypedDict

import duckdb


class Geofence(TypedDict):
    id: str
    status: Literal["on", "off", "schedule"]
    schedule_start: datetime.time | None
    schedule_end: datetime.time | None
    description: str


class GeofenceManager:
    def __init__(self, url: str | None = None):
        self.conn = duckdb.connect()
        self.url = url or os.environ["GEOFENCES_URL"]
        self.refresh_geofences()

    def refresh_geofences(self):
        self.conn.execute(
            f"""
            INSTALL spatial; LOAD spatial;
            CREATE OR REPLACE TABLE geofences as (SELECT
                id,
                status,
                schedule_start::TIME as schedule_start,
                schedule_stop::TIME as schedule_stop,
                description,
                ST_GeomFromGeoJSON(geojson) as geometry,
            FROM read_csv('{self.url}')
            )"""
        )

    def get_geofences(self) -> list[Geofence]:
        """get all geofences"""
        return self._to_dicts(self.conn.table("geofences"))

    def violations(
        self, *, lat: float, lon: float, timestamp: datetime.datetime
    ) -> list[Geofence]:
        """if the point is outside any geofence"""
        relation = self.conn.sql(
            """
            FROM geofences
            WHERE NOT ST_Contains(geometry, ST_Point($lat, $lon))
            AND (
                status = 'on'
                OR 
                (
                    status = 'schedule'
                    AND 
                    CASE
                        WHEN schedule_start IS NULL THEN TRUE
                        WHEN schedule_stop IS NULL THEN TRUE
                        WHEN schedule_start <= schedule_stop THEN
                            schedule_start <= $localtime AND $localtime <= schedule_stop
                        ELSE
                            schedule_start <= $localtime OR $localtime <= schedule_stop
                    END
                )
            )
            """,
            params={"lat": lat, "lon": lon, "localtime": timestamp.time()},
        )
        return self._to_dicts(relation)

    def _to_dicts(self, relation: duckdb.DuckDBPyRelation) -> list[Geofence]:
        cols = ["id", "status", "schedule_start", "schedule_stop", "description"]
        selection = relation.select(*cols)
        return [Geofence(zip(cols, row)) for row in selection.fetchall()]
