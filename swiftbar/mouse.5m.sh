#!/bin/sh
# <swiftbar.hideAbout>true</swiftbar.hideAbout><swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal><swiftbar.hideLastUpdated>false</swiftbar.hideLastUpdated><swiftbar.hideDisablePlugin>false</swiftbar.hideDisablePlugin><swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>
D="$(cd "$(dirname "$0")/.." && pwd)"
exec "$D/.venv/bin/python" "$D/swiftbar.py" mouse
