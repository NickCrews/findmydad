## Find My Dad

Experimenting with geofencing for apple airtags.
My father in law has dementia and is prone to wandering off (especially at night, oh joy!).
The idea is that this sends me a text when the airtag in his shoe leaves the area around our house.

FOLLOWUP:
It turns out this doesn't work consistently enough that I would actually recommend it
as a reliable alerting mechanism for others.
The FindMy network just doesn't seem to update frequently enough where I live,
even though it is a fairly dense neighborhood near downtown Boulder, CO.
But still, hopefuly someone can steal a few ideas from this.

A github action runs a script every 15 minutes. The script:
- Fetches the location of his airtag using https://github.com/malmeloo/FindMy.py
- Fetches geofence policies from a google sheet with a public CSV url using duckdb.
- Looks for violations in the policies using duckdb, eg if the airtag is outside
  the geofence during the scheduled time frame.
- If a violation is found, it sends a text to me and my partner's phones using https://textbelt.com/.
- Our phones have lightweight automation apps on them ("Shortcuts" on iOS and "[Message Alarm](https://play.google.com/store/apps/details?id=com.app.messagealarm&hl=en_US)" on Android) that
  look for a text with a specfic keyword, and then trigger an alarm.

## How to fork and use

This requires python development knowledge and isn't for the feint of heart.
You need a macOS machine with the airtag paired on it.

- Copy `.env.sample` to `.env`.
- run `uv run python -m findmy decrypt` to go through the encypted files that
  apple's FindMy app stores on your mac,
  decrypt them, and print the JSON to stdout.
  There will be one for every Find My accessory you have paired.
  Find the one for the airtag you want to track, store this in eg `dad.json`
  and write down this path in `ACCESSORY_JSON_PATH` in `.env`.
- Set up a permanent anisette server that will serve as the middleman to authenticate with
  apple's servers. Follow the instructions in [this issue thread](https://github.com/malmeloo/FindMy.py/issues/48#issuecomment-2901848737) to do this with a container for free on google cloud run.
  Hopefully this step won't be needed in the future
  once https://github.com/malmeloo/FindMy.py/issues/2 lands, and the FindMy.py
  can run a local anisette server.
  Fill in the `ANISSETTE_SERVER` variable in `.env` with the URL of your anisette server.
- run `uv run findmydad/account.py > account.json` to log into you apple account and generate
  a json file of credentials.
- Make a google sheet that's a duplicate of [this template](https://docs.google.com/spreadsheets/d/1C09ana124zMZPIfaXOytVwqdWKTPMIF7fb2j8o0JLDc/edit?gid=0#gid=0) and fill it in.
  This sets the policies for the geofences.
  Go to `File > Share > Publish to web` and publish the sheet as a CSV.
  Write down the URL of this csv in `GEOFENCES_URL` in `.env`.
- sign up for textbelt, pay a few dollars, and write down the api keys and phone numbers
  in `.env` as well.
- run `uv run python -m findmydad` to start the script.
- run `uv run findmydad/config.py` to bundle all the config into a single `config.json` file.
  Set this as a secret in your github repo for the action to use.