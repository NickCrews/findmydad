import asyncio
import datetime
import json
import logging
import sys
import typing
from pathlib import Path

from findmy import FindMyAccessory
from findmy.keys import KeyType
from findmy.reports.reports import LocationReport

from findmydad.account import get_account

logger = logging.getLogger(__name__)


def fetch_reports(
    device: FindMyAccessory | str | Path,
    *,
    anisette_url: str | None = None,
    account_json: str | bytes | typing.IO[bytes] | None = None,
) -> list[LocationReport]:
    device = get_device(device)

    def do():
        return asyncio.run(
            _fetch_reports(
                device=device, anisette_url=anisette_url, account_json=account_json
            )
        )

    try:
        return do()
    except asyncio.TimeoutError:
        # the anisette server, hosted on google cloud run, sometimes needs a second to boot up
        logger.warning(
            "Timeout error, retrying. This is usually caused by the anisette server not being ready yet."
        )
        return do()


async def _fetch_reports(
    *,
    device: FindMyAccessory,
    anisette_url: str | None = None,
    account_json: str | bytes | typing.IO[bytes] | None = None,
) -> list[LocationReport]:
    acc = await get_account(anisette_url=anisette_url, account_json=account_json)
    date_from = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(
        hours=48
    )
    date_to = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(
        hours=48
    )
    try:
        return await acc.fetch_reports(device, date_from, date_to)
    finally:
        await acc.close()


def default_serialize(obj):
    if isinstance(obj, KeyType):
        return obj.name
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")


def get_device(x: FindMyAccessory | str | Path) -> FindMyAccessory:
    if isinstance(x, FindMyAccessory):
        return x
    elif isinstance(x, Path):
        if x.suffix == ".plist":
            return FindMyAccessory.from_plist(x)
        elif x.suffix == ".json":
            return FindMyAccessory.from_json(x)
    elif isinstance(x, str):
        if x.endswith(".plist"):
            return FindMyAccessory.from_plist(Path(x))
        elif x.endswith(".json"):
            return FindMyAccessory.from_json(Path(x))
        else:
            raise ValueError("String must be a path to a .plist or .json file")
    else:
        raise ValueError("x must be a FindMyAccessory or str")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    reports = fetch_reports(sys.argv[1])
    logger.info(f"Fetched {len(reports)} reports")
    print(json.dumps(reports, indent=4, default=default_serialize))
