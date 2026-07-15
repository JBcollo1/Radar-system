# ==================== serial_reader.py ====================
# Runs serial reading on its own background thread so a slow or
# dropped connection never freezes the radar animation.

import serial
import threading
import time
from collections import deque

import config


class Reading:
    """One parsed line of data from the Arduino."""
    __slots__ = ("angle", "distance", "speed", "timestamp")

    def __init__(self, angle, distance, speed):
        self.angle = angle
        self.distance = distance      # -1 means out of range
        self.speed = speed
        self.timestamp = time.time()


class SerialReader:
    def __init__(self, port=config.SERIAL_PORT, baud=config.BAUD_RATE):
        self.port = port
        self.baud = baud
        self.ser = None
        self.connected = False

        self._lock = threading.Lock()
        self._latest = None
        self._new_readings = deque()   # readings since last UI poll

        # per-angle raw distance history, used for speed smoothing
        self._speed_history = {}

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    # ---------------- public API (called from main thread) ----------------

    def get_latest(self):
        """Most recent single reading, or None."""
        with self._lock:
            return self._latest

    def drain_new_readings(self):
        """Pop off all readings collected since the last call."""
        with self._lock:
            items = list(self._new_readings)
            self._new_readings.clear()
            return items

    def is_connected(self):
        return self.connected

    def stop(self):
        self._running = False
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass

    # ---------------- background thread ----------------

    def _run(self):
        while self._running:
            if self.ser is None:
                self._try_connect()
                if self.ser is None:
                    time.sleep(config.RECONNECT_DELAY)
                    continue

            try:
                raw = self.ser.readline()
                if not raw:
                    continue
                line = raw.decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                reading = self._parse(line)
                if reading:
                    with self._lock:
                        self._latest = reading
                        self._new_readings.append(reading)
            except (serial.SerialException, OSError):
                self.connected = False
                try:
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None
                time.sleep(config.RECONNECT_DELAY)

    def _try_connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            time.sleep(2)  # let Arduino reset after opening the port
            self.connected = True
        except serial.SerialException:
            self.ser = None
            self.connected = False

    def _parse(self, line):
        parts = line.split(',')
        if len(parts) != 3:
            return None
        try:
            angle = int(parts[0])
            distance = int(parts[1])
            raw_speed = float(parts[2])
        except ValueError:
            return None

        smoothed_speed = self._smooth_speed(angle, raw_speed)
        return Reading(angle, distance, smoothed_speed)

    def _smooth_speed(self, angle, raw_speed):
        """Moving average of speed per-angle-bucket to reduce ultrasonic jitter."""
        bucket = angle  # could round to nearest 2 deg if sweep step differs
        hist = self._speed_history.setdefault(bucket, deque(maxlen=config.SPEED_SMOOTHING_SAMPLES))
        hist.append(raw_speed)
        return sum(hist) / len(hist)