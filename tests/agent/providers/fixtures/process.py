"""An explicit protocol process double, used to test actual pipes and termination."""

import json
import sys
import time
from pathlib import Path

import yaml

case = sys.argv[1]
sys.stdin.read()
if case == "silent":
    time.sleep(30)
else:
    rows = yaml.safe_load(Path(__file__).with_name("events.yaml").read_text(encoding="utf-8"))[case]
    for row in rows:
        sys.stdout.write(json.dumps(row, ensure_ascii=False) + "\n")
        sys.stdout.flush()
