import datetime
import logging
import os
import typing

from findmy import FindMyAccessory
from findmy.reports.reports import LocationReport

from findmydad.config import load_config
from findmydad.fetch_reports import fetch_reports
from findmydad.geofences import Geofence, GeofenceManager
from findmydad.logger import setup_logging
from findmydad.notify import send_sms

logger = logging.getLogger(__name__)


class Violation(typing.TypedDict):
    lat: float
    lon: float
    timestamp: datetime.datetime
    geofence: Geofence


def get_violations(report: LocationReport, fences: GeofenceManager) -> list[Violation]:
    violated_fences = fences.violations(
        lat=report.latitude,
        lon=report.longitude,
        timestamp=report.timestamp,
    )
    return [
        {
            "lat": report.latitude,
            "lon": report.longitude,
            "timestamp": report.timestamp,
            "geofence": fence,
        }
        for fence in violated_fences
    ]


def _google_maps_info(lat: float, lon: float) -> str:
    # can't send URLs with textbelt :(
    # return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    return f"{lat},{lon}"


def summarize_violations(violations: list[Violation]) -> str:
    # there could be multiple violations that tie as the latest,
    # but here it doesn't matter which one we pick
    latest_violation = max(violations, key=lambda x: x["timestamp"])
    geofence_timezone = latest_violation["geofence"]["timezone"]
    # print the timestamp without the timezone info
    violation_timestamp_in_localtime = (
        latest_violation["timestamp"]
        .astimezone(geofence_timezone)
        .strftime("%Y-%m-%d %H:%M:%S")
    )
    return f"At {violation_timestamp_in_localtime} ({geofence_timezone}), Dad was at {_google_maps_info(latest_violation['lat'], latest_violation['lon'])} "


def main():
    setup_logging()
    config = load_config(os.getenv("FINDMYDAD_CONFIG"))
    for key, value in config.items():
        logger.debug(
            f"{key}: {value[:10] if isinstance(value, (str, bytes)) else value}..."
        )
    fence_manager = GeofenceManager(config["GEOFENCES_URL"])
    device = FindMyAccessory.from_json(config["ACCESSORY_JSON"])
    reports = fetch_reports(
        device,
        anisette_url=config["ANISETTE_URL"],
        account_json=config["ACCOUNT_JSON"],
    )
    latest_report = max(reports, key=lambda x: x.timestamp, default=None)
    violations = get_violations(latest_report, fence_manager)
    logger.info(f"Found {len(violations)} violations")
    if violations:
        message = summarize_violations(violations)
        logger.info("message: %s", message)
        if not os.getenv("TEST"):
            for phone in config["PHONE_NUMBERS"]:
                logger.debug(f"Sending SMS to {phone}")
                send_sms(
                    phone_number=phone,
                    message=message,
                    api_key=config["TEXTBELT_API_KEY"],
                )


if __name__ == "__main__":
    main()
