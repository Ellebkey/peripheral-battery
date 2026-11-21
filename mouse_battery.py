#!/usr/bin/env python3
"""Battery of a Logitech wireless mouse via HID++ 2.0 (receiver or direct USB).

Usage: ./run.sh            -> "G502 X LIGHTSPEED  70%  (full, discharging)"
       ./run.sh --json     -> machine-readable
       ./run.sh --scan     -> also try receiver slots 2-6 and direct USB (slow)
"""
import json, sys, time
import hid

LOGITECH = 0x046D
SW_ID = 0x0A
UNIFIED_BATTERY, BATTERY_STATUS, BATTERY_VOLTAGE = 0x1004, 0x1000, 0x1001
DEVICE_NAME = 0x0005


def open_hidpp():
    """Open the vendor-defined (0xFF00) interface that carries HID++ long reports."""
    for d in hid.enumerate(LOGITECH):
        if d["usage_page"] == 0xFF00 and d["usage"] == 1:
            dev = hid.device()
            dev.open_path(d["path"])
            return dev
    sys.exit("no Logitech HID++ interface found (receiver unplugged?)")


class Hidpp:
    def __init__(self, dev):
        self.dev = dev

    def call(self, idx, feat, func, params=b"", tries=4):
        """Send a request; retry because a sleeping mouse drops the first packets while it wakes."""
        for _ in range(tries):
            r = self._call_once(idx, feat, func, params)
            if r is not None:
                return r
            time.sleep(0.4)  # the receiver answers "unreachable" instantly while the mouse wakes
        return None

    def _call_once(self, idx, feat, func, params, timeout=0.5):
        while self.dev.read(20, 1):  # drain stale packets (timeout 0 would block)
            pass
        msg = bytearray(20)
        msg[0], msg[1], msg[2], msg[3] = 0x11, idx, feat, (func << 4) | SW_ID
        msg[4:4 + len(params)] = params
        self.dev.write(bytes(msg))
        end = time.time() + timeout
        while time.time() < end:
            r = self.dev.read(20, 100)
            if not r or r[1] != idx:
                continue
            if r[2] in (0x8F, 0xFF):  # HID++ error / device offline
                return None
            if r[2] == feat and (r[3] & 0x0F) == SW_ID:
                return bytes(r[4:])
        return None

    def feature_index(self, idx, fid):
        r = self.call(idx, 0x00, 0, fid.to_bytes(2, "big"))
        return r[0] if r and r[0] else None

    def name(self, idx):
        f = self.feature_index(idx, DEVICE_NAME)
        if not f:
            return "?"
        n = self.call(idx, f, 0)[0]
        out = b""
        while len(out) < n:
            out += self.call(idx, f, 1, bytes([len(out)]))
        return out[:n].decode(errors="replace")

    def battery(self, idx):
        f = self.feature_index(idx, UNIFIED_BATTERY)
        if f:  # getStatus: soc, level bitmask, charging status, ext power
            r = self.call(idx, f, 1)
            if r is None:
                return None
            soc, level, chg, _ = r[:4]
            lv = next((n for b, n in ((8, "full"), (4, "good"), (2, "low"), (1, "critical")) if level & b), "?")
            st = {0: "discharging", 1: "charging", 2: "charging (slow)", 3: "full", 4: "error"}.get(chg, f"status {chg}")
            return {"percent": soc, "level": lv, "status": st}
        f = self.feature_index(idx, BATTERY_STATUS)
        if f:  # legacy: soc, next level, status
            soc, _, chg = self.call(idx, f, 0)[:3]
            return {"percent": soc, "level": None, "status": "charging" if chg in (1, 2, 3, 4) else "discharging"}
        f = self.feature_index(idx, BATTERY_VOLTAGE)
        if f:  # voltage only; map roughly to %
            mv = int.from_bytes(self.call(idx, f, 0)[:2], "big")
            return {"percent": None, "level": None, "status": f"{mv} mV"}
        return None

    def dpi(self, idx):
        """AdjustableDPI (0x2201): current/default DPI of sensor 0 and the selectable range."""
        f = self.feature_index(idx, 0x2201)
        if not f:
            return None
        cur = self.call(idx, f, 2, b"\x00")  # getSensorDpi: sensor, dpi, default dpi
        lst = self.call(idx, f, 1, b"\x00")  # getSensorDpiList: sensor, then u16s; 0xE000|step marks a range
        if cur is None or lst is None:
            return None
        vals = [int.from_bytes(lst[i:i + 2], "big") for i in range(1, 15, 2)]
        vals = [v for v in vals if v]
        rng = None
        if len(vals) >= 3 and vals[1] & 0xE000 == 0xE000:
            rng = {"min": vals[0], "max": vals[2], "step": vals[1] & 0x1FFF}
        return {"current": int.from_bytes(cur[1:3], "big"), "default": int.from_bytes(cur[3:5], "big"), "range": rng}

    def report_rate(self, idx):
        """ReportRate (0x8060): current polling rate in Hz and the supported ones."""
        f = self.feature_index(idx, 0x8060)
        if not f:
            return None
        sup = self.call(idx, f, 0)  # bitmask: bit n = 1000/(n+1) Hz
        cur = self.call(idx, f, 1)  # interval in ms
        if sup is None or cur is None or not cur[0]:
            return None
        return {"hz": 1000 // cur[0], "supported_hz": [1000 // (n + 1) for n in range(8) if sup[0] >> n & 1]}

    def firmware(self, idx):
        """DeviceFwVersion (0x0003): version of each firmware entity (main app, bootloader, hardware)."""
        f = self.feature_index(idx, 0x0003)
        if not f:
            return None
        out = []
        for e in range(self.call(idx, f, 0)[0]):
            r = self.call(idx, f, 1, bytes([e]))
            if r and r[0] & 0x0F in (0, 1):
                out.append(f"{'app' if r[0] & 0x0F == 0 else 'boot'} {r[4]:02X}.{r[5]:02X}.B{int.from_bytes(r[6:8], 'big'):04X}")
        return out


def main():
    h = Hidpp(open_hidpp())
    found = []
    slots = (1, 2, 3, 4, 5, 6, 0xFF) if "--scan" in sys.argv else (1,)  # Lightspeed receivers pair one mouse, in slot 1
    for idx in slots:
        if h.call(idx, 0x00, 1, b"\x00\x00\x5A", tries=12) is None:  # pings wake a sleeping mouse
            continue
        b = h.battery(idx)
        if b:
            d = {"name": h.name(idx), **b}
            if "--all" in sys.argv:
                d.update(dpi=h.dpi(idx), report_rate=h.report_rate(idx), firmware=h.firmware(idx))
            found.append(d)
    if not found:
        sys.exit("mouse asleep or off (wake it by moving it) — no battery reply")
    if "--json" in sys.argv:
        print(json.dumps(found))
    else:
        for d in found:
            pct = f"{d['percent']}%" if d["percent"] is not None else "n/a"
            extra = ", ".join(x for x in (d["level"], d["status"]) if x)
            print(f"{d['name']}  {pct}  ({extra})")
            if d.get("dpi"):
                rng = d["dpi"]["range"]
                print(f"  DPI          {d['dpi']['current']} (default {d['dpi']['default']}"
                      + (f", range {rng['min']}-{rng['max']} step {rng['step']}" if rng else "") + ")")
            if d.get("report_rate"):
                print(f"  Polling      {d['report_rate']['hz']} Hz (supported {d['report_rate']['supported_hz']})")
            if d.get("firmware"):
                print(f"  Firmware     {', '.join(d['firmware'])}")


main()
