import asyncio
import datetime
import json
import logging
from pathlib import Path

from findmy import KeyPair
from findmy.keys import KeyType
from findmy.reports import (
    AsyncAppleAccount,
    LoginState,
    RemoteAnisetteProvider,
    SmsSecondFactorMethod,
    TrustedDeviceSecondFactorMethod,
)

from gen_keys import gen_keys

logger = logging.getLogger(__name__)

# ANISETTE_SERVER = "http://localhost:6969"
ANISETTE_SERVER = "https://ani.sidestore.io"


async def login(account: AsyncAppleAccount) -> None:
    apple_id = input("Apple ID (email or phone)? > ")
    apple_password = input("Password? > ")
    state = await account.login(apple_id, apple_password)

    if state == LoginState.REQUIRE_2FA:
        methods = await account.get_2fa_methods()
        for i, method in enumerate(methods):
            if isinstance(method, TrustedDeviceSecondFactorMethod):
                print(f"{i} - Trusted Device")
            elif isinstance(method, SmsSecondFactorMethod):
                # Print the (masked) phone numbers
                print(f"{i} - SMS ({method.phone_number})")

        ind = int(input("Method? > "))
        method = methods[ind]
        await method.request()
        code = input("Code? > ")
        await method.submit(code)


async def get_account() -> AsyncAppleAccount:
    anisette = RemoteAnisetteProvider(ANISETTE_SERVER)
    acc = AsyncAppleAccount(anisette)
    acc_store = Path("account.json")
    try:
        with acc_store.open() as f:
            acc.restore(json.load(f))
    except FileNotFoundError:
        await login(acc)
        with acc_store.open("w+") as f:
            json.dump(acc.export(), f)
    logger.info(f"Logged in as: {acc.account_name} ({acc.first_name} {acc.last_name})")
    return acc


async def fetch_reports(keys: list[KeyPair]) -> list[dict]:
    acc = await get_account()
    dump_list = []
    try:
        reports = await acc.fetch_last_reports(keys)
        for keypair in reports:
            report = reports[keypair]
            for r in report:
                obj = {
                    "time": r.timestamp,
                    "lat": r.latitude,
                    "lon": r.longitude,
                    "published_at": r.published_at,
                    "description": r.description,
                    "confidence": r.confidence,
                    "status": r.status,
                    "key": r.key.private_key_b64,
                }
                dump_list.append(obj)
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
    plist_path = "./plists/OwnedBeacons/997C2375-7C18-4FC9-B136-C43F68E2B060.plist"
    keys = gen_keys(plist_path)
    key_pairs = [KeyPair.from_b64(key_info["private_key_b64"]) for key_info in keys]
    # print(key_pairs[:5])
    reports = asyncio.run(fetch_reports(key_pairs))
    logger.info(f"Fetched {len(reports)} reports")
    json.dumps(reports, indent=4, default=default_serialize)
