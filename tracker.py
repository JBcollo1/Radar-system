# ==================== tracker.py ====================
# Turns a raw stream of (angle, distance) pings into persistent
# "tracked objects" with IDs, so the UI can show something closer
# to real radar contacts instead of disconnected dots.
#
# Speed is computed HERE, per matched object, instead of on the Arduino
# per fixed angle-slot. The old approach compared "the reading at angle
# X now" to "the reading at angle X last time the servo pointed there" --
# which silently breaks (reports 0 or garbage) for anything that moves
# across angles between sweep passes, since it lands in a different slot
# with no relevant history. Because ingest() already re-identifies the
# same physical object across sweeps via _find_match (angle+distance
# proximity), reusing that same match for speed means "how has *this
# object's* distance changed since I last saw *it*" -- correct regardless
# of which angle it currently shows up at.

import time
from collections import deque

import config


class TrackedObject:
    def __init__(self, obj_id, angle, distance):
        self.id = obj_id
        self.angle = angle
        self.distance = distance
        self.speed = 0.0
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.hit_count = 1
        # per-object speed history, used to smooth out ultrasonic jitter
        self._speed_history = deque(maxlen=config.SPEED_SMOOTHING_SAMPLES)

    def update(self, angle, distance):
        now = time.time()
        dt = now - self.last_seen

        # Guard against divide-by-zero and against stale matches (e.g. an
        # object that disappeared and reappeared much later) reporting a
        # misleadingly large instantaneous speed.
        if dt > 0 and dt < config.BLIP_FADE_TIME:
            raw_speed = (self.distance - distance) / dt   # +ve = approaching
            self._speed_history.append(raw_speed)
            self.speed = sum(self._speed_history) / len(self._speed_history)
        else:
            self._speed_history.clear()
            self.speed = 0.0

        self.angle = angle
        self.distance = distance
        self.last_seen = now
        self.hit_count += 1

    def age(self):
        return time.time() - self.last_seen

    def motion_label(self):
        if self.speed > config.APPROACH_THRESHOLD:
            return "approaching"
        if self.speed < config.RECEDE_THRESHOLD:
            return "receding"
        return "stationary"


class Tracker:
    def __init__(self):
        self._objects = {}
        self._next_id = 1

    def ingest(self, angle, distance):
        """Feed one reading in; returns the TrackedObject it matched/created (or None if out of range)."""
        if distance == -1 or distance <= 0 or distance > config.MAX_RANGE_CM:
            return None

        match = self._find_match(angle, distance)
        if match:
            match.update(angle, distance)
            return match

        obj = TrackedObject(self._next_id, angle, distance)
        self._next_id += 1
        self._objects[obj.id] = obj
        return obj

    def _find_match(self, angle, distance):
        best = None
        best_score = None
        for obj in self._objects.values():
            if obj.age() > config.BLIP_FADE_TIME:
                continue
            d_angle = abs(obj.angle - angle)
            d_dist = abs(obj.distance - distance)
            if d_angle <= config.TRACK_MATCH_ANGLE_TOLERANCE and d_dist <= config.TRACK_MATCH_DIST_TOLERANCE:
                score = d_angle + d_dist * 0.2
                if best_score is None or score < best_score:
                    best = obj
                    best_score = score
        return best

    def active_objects(self):
        """Objects still within their fade window, freshest first."""
        self._objects = {
            oid: obj for oid, obj in self._objects.items()
            if obj.age() <= config.BLIP_FADE_TIME
        }
        return sorted(self._objects.values(), key=lambda o: o.age())

    def active_count(self):
        """Convenience helper for the HUD -- number of currently tracked objects."""
        return len(self.active_objects())

    def closest_object(self):
        active = self.active_objects()
        if not active:
            return None
        return min(active, key=lambda o: o.distance)