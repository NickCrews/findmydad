import json
import os
from pathlib import Path
from typing import TypedDict

import dotenv


class Config(TypedDict):
    TEXTBELT_API_KEY: str
    GEOFENCES_URL: str
    ANISETTE_URL: str
    ACCOUNT_JSON: str
    ACCESSORY_JSON: str
    PHONE_NUMBERS: list[str]


def save_config():
    dotenv.load_dotenv()
    accessory_path = Path(os.getenv("ACCESSORY_JSON_PATH", "accessory.json"))
    account_json_path = Path(os.getenv("ACCOUNT_JSON_PATH", "account.json"))
    config = Config(
        TEXTBELT_API_KEY=os.environ["TEXTBELT_API_KEY"],
        GEOFENCES_URL=os.environ["GEOFENCES_URL"],
        ANISETTE_URL=os.environ["ANISETTE_URL"],
        PHONE_NUMBERS=json.loads(os.environ["PHONE_NUMBERS"]),
        ACCOUNT_JSON=account_json_path.read_text(),
        ACCESSORY_JSON=accessory_path.read_text(),
    )
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)


def load_config(path_or_contents: Path | str | None = None) -> Config:
    if path_or_contents is None:
        path_or_contents = Path("config.json")
    if isinstance(path_or_contents, Path):
        contents = path_or_contents.read_text()
    elif isinstance(path_or_contents, str):
        contents = path_or_contents
    else:
        raise ValueError("path_or_contents must be a Path or str")
    config = json.loads(contents)
    return Config(
        TEXTBELT_API_KEY=config["TEXTBELT_API_KEY"],
        PHONE_NUMBERS=config["PHONE_NUMBERS"],
        GEOFENCES_URL=config["GEOFENCES_URL"],
        ANISETTE_URL=config["ANISETTE_URL"],
        ACCOUNT_JSON=config["ACCOUNT_JSON"],
        ACCESSORY_JSON=config["ACCESSORY_JSON"],
    )


if __name__ == "__main__":
    save_config()
    config = load_config()
    print(config)
