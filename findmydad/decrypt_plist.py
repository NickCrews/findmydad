import os
import plistlib
import shlex
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Author: Shane B. <shane@wander.dev>
#
# Based on: https://gist.github.com/airy10/5205dc851fbd0715fcd7a5cdde25e7c8
#
# Tested on MacOS:
#
#   ProductName:            macOS
#   ProductVersion:         14.7.4
#   BuildVersion:           23H420
#
# With python version: 3.13.2

INPUT_PATH = Path.home() / "Library" / "com.apple.icloud.searchpartyd"

# NOTE FROM AUTHOR: For my purposes these are sufficient.
# You can add more if you need more, or remove the filter entirely below
ALLOWLISTED_DIRS = {"OwnedBeacons", "BeaconNamingRecord"}


def _get_key() -> bytearray:
    """
    TODO: consider switching to this library https://github.com/microsoft/keyper/blob/main/keyper
    once they publish a version of it that includes my MR with the changes to make it compatible
    with keys that are non-utf-8 encoded (like the BeaconStore one)
    """
    # TODO: if I contribute this, properly escape the label argument here...
    # label = "BeaconStore"
    # This thing will pop up 2 Password Input windows...
    key_in_hex = subprocess.getoutput(
        "security find-generic-password -l 'BeaconStore' -w"
    )
    return bytearray.fromhex(key_in_hex)


def decrypt_plist(in_file_path: str, key: bytearray) -> dict:
    """
    Given an encrypted plist file at path `in_file_path`, decrypt it using `key` and AES-GMC and return the decrypted plist `dict`

    :param in_file_path:    Source path of the encrypted plist file.

                            Generally something like `/Users/<username>/Library/com.apple.icloud.searchpartyd/OwnedBeacons/<UUID>.record`

    :param key:             Raw key to decrypt plist file with.

                            Get it from the system shell command:

                            `security find-generic-password -l '<LABEL>' -w`

                            See: `get_key(label: str)`


    :returns:               The decoded plist dict
    :rtype: dict

    :raises Exception:      On failure to decrypt the encrypted plist
    """
    with open(in_file_path, "rb") as f:
        encrypted_data: bytes = f.read()

    try:
        plist = plistlib.loads(encrypted_data)
    except Exception:
        raise Exception("Invalid file format")

    if not isinstance(plist, list) or len(plist) < 3:
        raise Exception("Invalid plist format")

    nonce, tag, ciphertext = plist[0], plist[1], plist[2]
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag))
    decryptor = cipher.decryptor()
    decrypted_plist = decryptor.update(ciphertext) + decryptor.finalize()

    try:
        decrypted_plist = plistlib.loads(decrypted_plist)
    except Exception:
        raise Exception("Invalid decrypted data")

    if not isinstance(decrypted_plist, dict):
        raise Exception(
            f"Expected plist to be a dictionary, but it was a {type(decrypted_plist)}"
        )

    return decrypted_plist


def output_path(output_root: str, input_file_path: str, input_root_folder: str) -> Path:
    """
    Transforms `input_file_path` into a dumping `output_file_path` along the lines of this idea (but it works generically for any level of nesting):

    Given:
    - `input_file_path` = `/Users/<user>/Library/com.apple.icloud.searchpartyd/SomeFolder/.../<UUID>.record`
    - `output_root` = `/Users/<user>/my-target-folder`
    - `input_root_folder` = `/Users/<user>/Library/com.apple.icloud.searchpartyd`

    This will create the path:
    `/Users/<user>/my-target-folder/SomeFolder/.../<UUID>.plist`
    """
    rel_path: str = os.path.relpath(input_file_path, input_root_folder)
    replace_file_ext: str = os.path.splitext(rel_path)[0] + ".plist"
    return Path(output_root) / replace_file_ext


def decrypt_folder(
    input_base_path: str, folder_name: str, key: bytearray, output_to: str
):
    """
    Decrypt contents of folder `<input_base_path>/<folder_name>` to file path `output_to` recursively using `key`
    """
    search_path = Path(input_base_path) / folder_name
    for path, folders, files in os.walk(search_path):
        for filename in files:
            try:
                file_fullpath = Path(path) / filename
                print(f"Trying to decrypt plist file at: {file_fullpath}...")
                plist = decrypt_plist(file_fullpath, key)
                file_dumpath = output_path(output_to, file_fullpath, input_base_path)
                print(f"Now trying to dump decrypted plist file to: {file_dumpath}")
                file_dumpath.parent.mkdir(parents=True, exist_ok=True)
                with open(file_dumpath, "wb") as out_f:
                    plistlib.dump(plist, out_f)
                print("Success!")
            except Exception as e:
                print(f"ERROR decrypting plist file: {e}")


def main(out_dir: str | Path):
    key = _get_key()
    for path, folders, _ in os.walk(INPUT_PATH):
        for foldername in folders:
            if foldername not in ALLOWLISTED_DIRS:
                continue
            decrypt_folder(path, foldername, key, out_dir)
        break


def cli():
    if len(sys.argv) > 1:
        out_dir = Path(sys.argv[1])
    else:
        out_dir = Path.cwd() / "plists"
    main(out_dir)
    os.system(f"open {shlex.quote(str(out_dir))}")


if __name__ == "__main__":
    cli()
