#!/usr/bin/env python3
"""Battery of a Corsair VOID WIRELESS v2 headset through its USB receiver (1b1c:2a08).

Protocol taken from HeadsetControl 4.1.0 (lib/devices/corsair_void_v2w.hpp), read-only subset:
receiver heartbeat -> headset heartbeat (answers only if the headset is on) -> battery query.
It never switches the receiver to "software mode", so it does not pop the audio.

Usage: ./run.sh headset          -> "VOID WIRELESS v2  80%  (mic down)"
       ./run.sh headset --json   -> machine-readable
"""
import json, sys
import hid

CORSAIR = 0x1B1C
RECEIVERS = {0x2A08: "VOID WIRELESS v2", 0x2A02: "VIRTUOSO MAX WIRELESS", 0x0A97: "HS80 MAX WIRELESS"}
RECEIVER, HEADSET = 0x08, 0x09
TIMEOUT_MS = 1000


def open_receiver():
    """Interface 4 (vendor page 0xFF42) carries the command channel."""
    for d in hid.enumerate(CORSAIR):
        if d["product_id"] in RECEIVERS and d["interface_number"] == 4:
            dev = hid.device()
            dev.open_path(d["path"])
            return dev, RECEIVERS[d["product_id"]]
    sys.exit("no Corsair wireless receiver found (unplugged?)")


class Receiver:
    def __init__(self, dev):
        self.dev = dev

    def send(self, endpoint, *cmd):
        msg = bytearray(65)  # report id 0 + 64 bytes
        msg[1], msg[2] = 0x02, endpoint
        msg[3:3 + len(cmd)] = bytes(cmd)
        self.dev.write(bytes(msg))

    def read(self, timeout=TIMEOUT_MS):
        return self.dev.read(64, timeout)

    def flush(self):
        while self.dev.read(64, 5):  # timeout 0 would block forever in hidapi
            pass

    def headset_online(self):
        self.send(RECEIVER, 0x02, 0x13)  # receiver firmware: required before anything else
        self.send(RECEIVER, 0x02, 0x12)  # receiver heartbeat
        self.flush()
        self.send(HEADSET, 0x02, 0x12)  # headset heartbeat: no reply = headset off or out of range
        return bool(self.read())

    def battery(self):
        """Raw value is 1-1000; the receiver sometimes answers with the paired headset id instead, so retry."""
        self.flush()
        for _ in range(4):
            self.send(HEADSET, 0x02, 0x0F)
            r = self.read()
            if not r:
                return None
            raw = r[4] | r[5] << 8
            if 0 < raw <= 1000:
                return raw // 10
        return None

    def mic_up(self):
        """The boom mic mutes by flipping up."""
        self.send(HEADSET, 0x02, 0xA6)
        r = self.read()
        return None if not r else r[4] == 0x01


def main():
    dev, name = open_receiver()
    try:
        rx = Receiver(dev)
        if not rx.headset_online():
            sys.exit("headset off or out of range — no heartbeat reply")
        pct = rx.battery()
        if pct is None:
            sys.exit("headset online but no plausible battery reading")
        d = {"name": name, "percent": pct, "mic_up": rx.mic_up()}
    finally:
        dev.close()
    if "--json" in sys.argv:
        print(json.dumps([d]))
    else:
        mic = {True: "mic up / muted", False: "mic down", None: "mic ?"}[d["mic_up"]]
        print(f"{d['name']}  {pct}%  ({mic})")


main()
