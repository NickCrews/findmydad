import asyncio
import io
import json
import logging
import os
from pathlib import Path

from findmy.reports import (
    AsyncAppleAccount,
    LoginState,
    RemoteAnisetteProvider,
    SmsSecondFactorMethod,
    TrustedDeviceSecondFactorMethod,
)

logger = logging.getLogger(__name__)


async def login(account: AsyncAppleAccount) -> dict:
    account_id = os.environ.get("APPLE_ID") or input("Apple ID (email or phone)? > ")
    apple_pass = os.environ.get("APPLE_PASSWORD") or input("Password? > ")
    state = await account.login(account_id, apple_pass)

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
    string_io = io.StringIO()
    account.export(string_io)
    return json.loads(string_io.getvalue())


async def get_account(
    *, anisette_url: str | None = None, account_json: Path | str | dict | None = None
) -> AsyncAppleAccount:
    annisette_url = anisette_url or os.environ.get("ANISETTE_URL")
    anisette = RemoteAnisetteProvider(annisette_url)
    acc = AsyncAppleAccount(anisette)
    if account_json is None:
        account_json = Path("account.json")

    if isinstance(account_json, str):
        account_dict = json.loads(account_json)
    elif isinstance(account_json, Path):
        try:
            account_dict = json.loads(account_json.read_text())
        except FileNotFoundError:
            account_dict = None
    elif isinstance(account_json, dict):
        account_dict = account_json
    else:
        raise ValueError("account_json must be a Path, str, or dict")

    if account_dict is None:
        account_dict = await login(acc)
    else:
        acc.restore(account_dict)

    # try:
    #     with acc_store.open() as f:
    #         acc.restore(json.load(f))
    # except FileNotFoundError:
    #     await login(acc)
    #     with acc_store.open("w+") as f:
    #         json.dump(acc.export(), f)
    logger.info(f"Logged in as: {acc.account_name} ({acc.first_name} {acc.last_name})")
    return acc


def login_cli() -> None:
    login_dict = asyncio.run(login())
    print(json.dumps(login_dict, indent=4))


if __name__ == "__main__":
    login_cli()
