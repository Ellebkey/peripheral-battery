#!/bin/sh
# usage: run.sh mouse|headset [--json ...]; bootstraps a local venv with hidapi on first run
D="$(cd "$(dirname "$0")" && pwd)"
case "$1" in
  mouse|headset) S="$1"; shift ;;
  *) echo "usage: $0 mouse|headset [--json]" >&2; exit 2 ;;
esac
[ -x "$D/.venv/bin/python" ] || { python3 -m venv "$D/.venv" && "$D/.venv/bin/python" -m pip install -q hidapi; }
exec "$D/.venv/bin/python" "$D/${S}_battery.py" "$@"
