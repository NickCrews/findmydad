"""
Example showing how to retrieve the primary key of your own AirTag, or any other FindMy-accessory.

This key can be used to retrieve the device's location for a single day.

FRom https://github.com/hajekj/OfflineFindRecovery/blob/master/src/python/findmy-keygeneration.py
"""

import io
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import IO

from findmy import FindMyAccessory
from findmy.keys import KeyType

import findmydad.fetch_reports as fetch_reports

logger = logging.getLogger(__name__)


def gen_keys(plist: str | bytes | IO[bytes]) -> None:
    if isinstance(plist, str):
        with open(plist, "rb") as f:
            plist = io.BytesIO(f.read())
    elif isinstance(plist, bytes):
        plist = io.BytesIO(plist)
    airtag = FindMyAccessory.from_plist(plist)

    start = datetime.now(tz=timezone.utc) - timedelta(hours=48)
    end = datetime.now(tz=timezone.utc) + timedelta(hours=48)
    infos = []
    lookup_time = start
    while lookup_time < end:
        keys = airtag.keys_at(lookup_time)
        for key in keys:
            if key.key_type == KeyType.PRIMARY:
                infos.append(
                    dict(
                        lookup_time=lookup_time,
                        adv_key_b64=key.adv_key_b64,
                        private_key_b64=key.private_key_b64,
                        key_type=key.key_type,
                        hashed_adv_key_b64=key.hashed_adv_key_b64,
                    )
                )

        lookup_time += timedelta(minutes=15)
    logger.info(f"Generated {len(infos)} keys")
    return infos


if __name__ == "__main__":
    # plist_path = sys.argv[1]
    plist_path = "./plists/OwnedBeacons/997C2375-7C18-4FC9-B136-C43F68E2B060.plist"
    keys = gen_keys(plist_path)
    print(json.dumps(keys, indent=4, default=fetch_reports.default_serialize))
