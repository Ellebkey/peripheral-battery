#!/usr/bin/env python3
"""SwiftBar output for one device: `swiftbar.py mouse|headset`.

Runs the reader; when the device does not answer (off, asleep, receiver unplugged) it prints
nothing, which makes SwiftBar hide the icon.
"""
import json, os, subprocess, sys

D = os.path.dirname(os.path.abspath(__file__))
LOW = 20
STATUS = {"discharging": "descargando", "charging": "cargando", "charging (slow)": "cargando (lento)",
          "full": "cargado", "error": "error de carga"}
ICON = {"mouse": "computermouse.fill", "headset": "headphones"}


def read(kind):
    try:
        p = subprocess.run([os.path.join(D, "run.sh"), kind, "--json"], capture_output=True, text=True, timeout=40)
    except subprocess.TimeoutExpired:
        return None
    if p.returncode != 0:
        return None
    return json.loads(p.stdout)[0]


def main():
    kind = sys.argv[1]
    d = read(kind)
    if not d:
        return

    pct = d.get("percent")
    charging = (d.get("status") or "").startswith("charging")
    title = f"{pct}%" if pct is not None else "?"
    if charging:
        title = "⚡" + title
    color = " color=#FF3B30" if pct is not None and pct <= LOW and not charging else ""
    print(f"{title} | sfimage={ICON[kind]}{color}")

    print("---")
    print(f"{d['name']} | size=12")
    print(f"Batería: {pct}%" if pct is not None else "Batería: ?")
    if d.get("status"):
        print(f"Estado: {STATUS.get(d['status'], d['status'])}")
    if d.get("mic_up") is not None:
        print("Micrófono: arriba (silenciado)" if d["mic_up"] else "Micrófono: abajo")
    print("---")
    print("Actualizar | refresh=true")


main()
