"""Explicit subprocess protocol fixture; never a production provider."""

import json
import sys
from time import sleep

import yaml


def main():
    with open(sys.argv[1], encoding="utf-8") as stream:
        values = yaml.safe_load(stream)["protocols"][sys.argv[2]]
    sys.stdin.read()
    for event in values["events"]:
        sys.stdout.write(json.dumps(event) + "\n")
        sys.stdout.flush()
    sleep(values.get("wait_seconds", 0))


if __name__ == "__main__":
    main()
