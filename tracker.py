# ==================== tracker.py ====================
# Turns a raw stream of (angle, distance) pings into persistent
# "tracked objects" with IDs, so the UI can show something closer
# to real radar contacts instead of disconnected dots.

import time
import config


class TrackedObject:
    def __init__(self, obj_id, angle, distance, speed):
        self.id = obj_id
        self.angle = angle
        self.distance = distance
        self.speed = speed
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.hit_count = 1

    def update(self, angle, distance, speed):
        self.angle = angle
        self.distance = distance
        self.speed = speed
        self.last_seen = time.time()
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

    def ingest(self, angle, distance, speed):
        """Feed one reading in; returns the TrackedObject it matched/created (or None if out of range)."""
        if distance == -1 or distance <= 0 or distance > config.MAX_RANGE_CM:
            return None

        match = self._find_match(angle, distance)
        if match:
            match.update(angle, distance, speed)
            return match

        obj = TrackedObject(self._next_id, angle, distance, speed)
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

    def closest_object(self):
        active = self.active_objects()
        if not active:
            return None
        return min(active, key=lambda o: o.distance)