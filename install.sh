#!/bin/sh
# Installs the menu bar icons on this Mac: venv with hidapi, SwiftBar, plugin folder, shell aliases.
# Safe to run again (e.g. after moving the repo).
set -eu
D="$(cd "$(dirname "$0")" && pwd)"

command -v python3 >/dev/null || { echo "python3 missing: run 'xcode-select --install' and retry" >&2; exit 1; }

if [ ! -d /Applications/SwiftBar.app ]; then
  command -v brew >/dev/null || { echo "Install SwiftBar (https://swiftbar.app) or Homebrew, then retry" >&2; exit 1; }
  brew install --cask swiftbar
fi

if [ ! -x "$D/.venv/bin/python" ]; then
  python3 -m venv "$D/.venv"
  "$D/.venv/bin/python" -m pip install -q hidapi
fi
chmod +x "$D/run.sh" "$D"/swiftbar/*.sh

defaults write com.ameba.SwiftBar PluginDirectory "$D/swiftbar"

RC="$HOME/.zshrc"
touch "$RC"
tmp="$(mktemp)"
sed '/# >>> peripheral-battery >>>/,/# <<< peripheral-battery <<</d' "$RC" > "$tmp"
cat >> "$tmp" <<EOF
# >>> peripheral-battery >>>
alias mouse-battery="$D/run.sh mouse"
alias headset-battery="$D/run.sh headset"
# <<< peripheral-battery <<<
EOF
cat "$tmp" > "$RC" && rm -f "$tmp"

osascript -e 'quit app "SwiftBar"' 2>/dev/null || true
sleep 1
open -a SwiftBar

echo "Installed. Plugins: $D/swiftbar"
for k in mouse headset; do
  printf '%s: ' "$k"; "$D/run.sh" "$k" 2>&1 | tail -1 || true
done
echo "Open a new terminal for the aliases. To hide a device you don't have: click its icon > Disable Plugin."
