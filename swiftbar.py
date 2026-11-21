#!/usr/bin/env python3
"""SwiftBar output for one device: `swiftbar.py mouse|headset`.

Runs the reader, caches the last good reading, and when the device is asleep/off shows the
cached value in gray (up to STALE_H hours old) instead of a blank.
"""
import json, os, subprocess, sys, time

D = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.expanduser("~/Library/Caches/peripheral-battery")
STALE_H = 12
LOW = 20
STATUS = {"discharging": "descargando", "charging": "cargando", "charging (slow)": "cargando (lento)",
          "full": "cargado", "error": "error de carga"}
DEV = {
    "mouse": {"icon": "computermouse.fill", "label": "Mouse"},
    "headset": {"icon": "headphones", "label": "Audífonos"},
}


def read(kind):
    try:
        p = subprocess.run([os.path.join(D, "run.sh"), kind, "--json"], capture_output=True, text=True, timeout=40)
    except subprocess.TimeoutExpired:
        return None, "sin respuesta (timeout)"
    if p.returncode != 0:
        return None, (p.stderr.strip().splitlines() or ["error"])[-1]
    return json.loads(p.stdout)[0], None


def ago(ts):
    m = int((time.time() - ts) / 60)
    return f"hace {m} min" if m < 60 else f"hace {m // 60} h {m % 60} min"


def main():
    kind = sys.argv[1]
    meta = DEV[kind]
    cache = os.path.join(CACHE, f"{kind}.json")
    os.makedirs(CACHE, exist_ok=True)

    d, err = read(kind)
    if d:
        d["ts"] = time.time()
        tmp = cache + ".tmp"
        with open(tmp, "w") as f:
            json.dump(d, f)
        os.replace(tmp, cache)
    else:
        try:
            with open(cache) as f:
                d = json.load(f)
            if time.time() - d["ts"] > STALE_H * 3600:
                d = None
        except (OSError, ValueError, KeyError):
            d = None

    live = err is None
    pct = d and d.get("percent")
    charging = bool(live and d and (d.get("status") or "").startswith("charging"))
    title = f"{pct}%" if pct is not None else "–"
    if charging:
        title = "⚡" + title
    color = ""
    if not live:
        color = " color=#8E8E93"
    elif pct is not None and pct <= LOW and not charging:
        color = " color=#FF3B30"
    print(f"{title} | sfimage={meta['icon']}{color}")

    print("---")
    if d:
        print(f"{d['name']} | size=12")
        print(f"Batería: {pct}%" if pct is not None else "Batería: ?")
        if d.get("status"):
            print(f"Estado: {STATUS.get(d['status'], d['status'])}")
        if d.get("mic_up") is not None:
            print("Micrófono: arriba (silenciado)" if d["mic_up"] else "Micrófono: abajo")
    if not live:
        print(f"{meta['label']}: {err} | color=#8E8E93")
        if d:
            print(f"Última lectura {ago(d['ts'])} | color=#8E8E93")
    print("---")
    print("Actualizar | refresh=true")


main()
