import datetime
import os
import zoneinfo
from typing import Literal, TypedDict

import duckdb


class Geofence(TypedDict):
    id: str
    status: Literal["on", "off", "schedule"]
    schedule_start: datetime.time | None
    schedule_end: datetime.time | None
    description: str
    timezone: zoneinfo.ZoneInfo


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
                timezone::VARCHAR as timezone,
            FROM read_csv('{self.url}')
            );
            -- convert a timestamp to a time in the given timezone
            CREATE OR REPLACE MACRO time_at(timestamp, timezone) AS (
                strftime((timestamp AT TIME ZONE timezone), '%H:%M:%S')::TIME
            );
            CREATE MACRO violations(lat, lon, timestamp) AS TABLE
                SELECT *, time_at(timestamp, timezone) AS time_at
                FROM geofences
                WHERE NOT ST_Contains(geometry, ST_Point(lon, lat))
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
                                time_at(timestamp, timezone) >= schedule_start AND time_at(timestamp, timezone) <= schedule_stop
                            ELSE
                                time_at(timestamp, timezone) >= schedule_start OR  time_at(timestamp, timezone) <= schedule_stop
                        END
                    )
                );
            """
        )

    def get_geofences(self) -> list[Geofence]:
        """get all geofences"""
        return self._to_dicts(self.conn.table("geofences"))

    def violations(
        self, *, lat: float, lon: float, timestamp: datetime.datetime
    ) -> list[Geofence]:
        """if the point is outside any geofence"""
        relation = self.conn.sql(
            "FROM violations($lat, $lon, $timestamp)",
            params={"lat": lat, "lon": lon, "timestamp": timestamp},
        )
        return self._to_dicts(relation)

    @staticmethod
    def _to_dicts(relation: duckdb.DuckDBPyRelation) -> list[Geofence]:
        cols = [
            "id",
            "status",
            "schedule_start",
            "schedule_stop",
            "description",
            "timezone",
        ]
        extra = [c for c in relation.columns if c not in cols]
        cols = [*cols, *extra]
        raw = [dict(zip(cols, row)) for row in relation.select(*cols).fetchall()]
        for row in raw:
            row["timezone"] = zoneinfo.ZoneInfo(row["timezone"])
        return [Geofence(**row) for row in raw]
