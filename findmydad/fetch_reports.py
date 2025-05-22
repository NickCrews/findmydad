import asyncio
import datetime
import io
import json
import logging
import typing

from findmy import KeyPair
from findmy.keys import KeyType

import findmydad.gen_keys as gen_keys
from findmydad.account import get_account

logger = logging.getLogger(__name__)


class Report(typing.TypedDict):
    timestamp: datetime.datetime
    lat: float
    lon: float
    published_at: datetime.datetime
    description: str
    confidence: int
    status: str
    key: KeyPair


def _to_key_pairs(
    plist_or_keys: str | bytes | typing.IO[bytes] | list[KeyPair],
) -> list[KeyPair]:
    if isinstance(plist_or_keys, (str, bytes, io.BytesIO)):
        # plist_or_keys is a plist file or bytes
        keys = gen_keys.gen_keys(plist_or_keys)
        key_pairs = [KeyPair.from_b64(key_info["private_key_b64"]) for key_info in keys]
    return key_pairs


def fetch_reports(
    plist_or_keys: str | bytes | typing.IO[bytes] | list[KeyPair],
    *,
    anisette_url: str | None = None,
    account_json: str | bytes | typing.IO[bytes] | None = None,
) -> list[Report]:
    keys = _to_key_pairs(plist_or_keys)

    def do():
        return asyncio.run(
            _fetch_reports(
                keys=keys, anisette_url=anisette_url, account_json=account_json
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
    keys: list[KeyPair],
    anisette_url: str | None = None,
    account_json: str | bytes | typing.IO[bytes] | None = None,
) -> list[Report]:
    acc = await get_account(anisette_url=anisette_url, account_json=account_json)
    dump_list = []
    try:
        reports = await acc.fetch_last_reports(keys)
        for keypair in reports:
            report_raw = reports[keypair]
            for r in report_raw:
                rep = Report(
                    timestamp=r.timestamp,
                    lat=r.latitude,
                    lon=r.longitude,
                    published_at=r.published_at,
                    description=r.description,
                    confidence=r.confidence,
                    status=r.status,
                    key=r.key.private_key_b64,
                )
                dump_list.append(rep)
        return dump_list
    finally:
        await acc.close()


def default_serialize(obj):
    if isinstance(obj, KeyType):
        return obj.name
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    plist_path = "./plist.plist"
    # print(key_pairs[:5])
    reports = _to_key_pairs(plist_path)
    logger.info(f"Fetched {len(reports)} reports")
    print(json.dumps(reports, indent=4, default=default_serialize))
