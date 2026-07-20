# ==================== renderer.py ====================
# Everything that draws pixels lives here. main.py just calls
# Renderer.draw_frame(...) once per loop.

import math
import time
import pygame

import config


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.width, self.height = screen.get_size()

        self.center_x = self.width // 2
        self.center_y = self.height - config.HUD_HEIGHT - 20
        self.radius = min(self.width, self.height - config.HUD_HEIGHT - 60) // 2 - 20

        self.font_hud_big = pygame.font.SysFont("consolas", 28, bold=True)
        self.font_hud_small = pygame.font.SysFont("consolas", 17)
        self.font_label = pygame.font.SysFont("consolas", 14)
        self.font_title = pygame.font.SysFont("consolas", 20, bold=True)

        self.sweep_trail = []   # list of (angle, timestamp)
        self._scanline_offset = 0

    # ---------------- coordinate helpers ----------------

    def polar_to_screen(self, angle_deg, distance_cm):
        dist_px = min(distance_cm / config.MAX_RANGE_CM, 1.0) * self.radius
        rad = math.radians(angle_deg)
        x = self.center_x + dist_px * math.cos(rad)
        y = self.center_y - dist_px * math.sin(rad)
        return x, y

    # ---------------- background grid ----------------

    def draw_grid(self):
        for frac in (0.25, 0.5, 0.75, 1.0):
            r = int(self.radius * frac)
            rect = pygame.Rect(self.center_x - r, self.center_y - r, r * 2, r * 2)
            pygame.draw.arc(self.screen, config.COLOR_GRID, rect, math.radians(0), math.radians(180), 1)
            # range label on the horizontal
            label_val = int(config.MAX_RANGE_CM * frac)
            label = self.font_label.render(f"{label_val}cm", True, config.COLOR_TEXT_DIM)
            self.screen.blit(label, (self.center_x + r - 18, self.center_y - 16))

        for a in range(0, 181, 30):
            rad = math.radians(a)
            x = self.center_x + self.radius * math.cos(rad)
            y = self.center_y - self.radius * math.sin(rad)
            pygame.draw.line(self.screen, config.COLOR_GRID, (self.center_x, self.center_y), (x, y), 1)
            lx = self.center_x + (self.radius + 22) * math.cos(rad)
            ly = self.center_y - (self.radius + 22) * math.sin(rad)
            label = self.font_label.render(f"{a}°", True, config.COLOR_TEXT_DIM)
            lbl_rect = label.get_rect(center=(lx, ly))
            self.screen.blit(label, lbl_rect)

        pygame.draw.line(
            self.screen, config.COLOR_GRID_BRIGHT,
            (self.center_x - self.radius, self.center_y),
            (self.center_x + self.radius, self.center_y), 2
        )

    def draw_scanline_effect(self):
        """Subtle horizontal scanlines for a CRT-radar feel."""
        self._scanline_offset = (self._scanline_offset + 1) % 4
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for y in range(self._scanline_offset, self.height, 4):
            pygame.draw.line(overlay, (0, 0, 0, 18), (0, y), (self.width, y))
        self.screen.blit(overlay, (0, 0))

    # ---------------- sweep line + trail ----------------

    def update_sweep_trail(self, current_angle):
        now = time.time()
        self.sweep_trail.append((current_angle, now))
        cutoff = now - 0.4
        self.sweep_trail = [(a, t) for (a, t) in self.sweep_trail if t >= cutoff][-config.SWEEP_TRAIL_LENGTH:]

    def draw_sweep(self, current_angle):
        now = time.time()
        for angle, t in self.sweep_trail:
            age = now - t
            alpha_frac = max(0.0, 1.0 - age / 0.4)
            rad = math.radians(angle)
            x = self.center_x + self.radius * math.cos(rad)
            y = self.center_y - self.radius * math.sin(rad)
            surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            color = (*config.COLOR_SWEEP_TRAIL, int(120 * alpha_frac))
            pygame.draw.line(surf, color, (self.center_x, self.center_y), (x, y), 2)
            self.screen.blit(surf, (0, 0))

        rad = math.radians(current_angle)
        x = self.center_x + self.radius * math.cos(rad)
        y = self.center_y - self.radius * math.sin(rad)
        pygame.draw.line(self.screen, config.COLOR_SWEEP, (self.center_x, self.center_y), (x, y), 3)
        pygame.draw.circle(self.screen, config.COLOR_SWEEP, (int(x), int(y)), 4)

    # ---------------- tracked objects ----------------

    def draw_objects(self, active_objects):
        now = time.time()
        for obj in active_objects:
            age = obj.age()
            alpha_frac = max(0.0, 1.0 - age / config.BLIP_FADE_TIME)
            x, y = self.polar_to_screen(obj.angle, obj.distance)

            label = obj.motion_label()
            if label == "approaching":
                color = config.COLOR_APPROACH
            elif label == "receding":
                color = config.COLOR_RECEDE
            else:
                color = config.COLOR_STATIONARY

            base_radius = 5 + min(obj.hit_count, 6)
            radius = int(base_radius * (0.5 + 0.5 * alpha_frac))

            # pulsing ring for very fresh/strong contacts
            if age < 0.3:
                ring_r = radius + int(6 * (age / 0.3))
                ring_alpha = int(180 * (1 - age / 0.3))
                surf = pygame.Surface((ring_r * 4, ring_r * 4), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*color, ring_alpha), (ring_r * 2, ring_r * 2), ring_r, 2)
                self.screen.blit(surf, (x - ring_r * 2, y - ring_r * 2))

            surf = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*color, int(255 * alpha_frac)), (radius * 2, radius * 2), radius)
            self.screen.blit(surf, (x - radius * 2, y - radius * 2))

            if obj.hit_count > 3 and age < 1.0:
                id_label = self.font_label.render(f"#{obj.id}", True, color)
                self.screen.blit(id_label, (x + radius + 3, y - radius - 3))

    # ---------------- HUD ----------------

    def draw_hud(self, current_angle, current_distance, current_speed, connected, closest, fps, paused, tracked_count=0):
        panel_y = self.height - config.HUD_HEIGHT
        pygame.draw.rect(self.screen, config.COLOR_HUD_BG, (0, panel_y, self.width, config.HUD_HEIGHT))
        pygame.draw.line(self.screen, config.COLOR_GRID_BRIGHT, (0, panel_y), (self.width, panel_y), 2)

        title = self.font_title.render("ULTRASONIC RADAR", True, config.COLOR_TEXT)
        self.screen.blit(title, (20, panel_y + 8))

        angle_text = self.font_hud_big.render(f"Angle: {current_angle}°", True, config.COLOR_TEXT)
        self.screen.blit(angle_text, (20, panel_y + 38))

        if current_distance == -1 or current_distance > config.MAX_RANGE_CM:
            dist_str, dist_color = "Distance: -- ", config.COLOR_TEXT_DIM
        else:
            dist_str, dist_color = f"Distance: {current_distance} cm", config.COLOR_TEXT
        dist_text = self.font_hud_big.render(dist_str, True, dist_color)
        self.screen.blit(dist_text, (280, panel_y + 38))

        if current_speed > config.APPROACH_THRESHOLD:
            speed_str, speed_color = f"{abs(current_speed):.1f} cm/s IN", config.COLOR_APPROACH
        elif current_speed < config.RECEDE_THRESHOLD:
            speed_str, speed_color = f"{abs(current_speed):.1f} cm/s OUT", config.COLOR_RECEDE
        else:
            speed_str, speed_color = "steady", config.COLOR_STATIONARY
        speed_text = self.font_hud_big.render(f"Speed: {speed_str}", True, speed_color)
        self.screen.blit(speed_text, (600, panel_y + 38))

        # closest object callout
        if closest:
            closest_str = f"Nearest contact: #{closest.id} @ {closest.distance}cm, {closest.angle}°"
        else:
            closest_str = "Nearest contact: none"
        closest_text = self.font_hud_small.render(closest_str, True, config.COLOR_TEXT_DIM)
        self.screen.blit(closest_text, (20, panel_y + 72))

        # live count of currently tracked objects
        count_str = f"Tracked objects: {tracked_count}"
        count_text = self.font_hud_small.render(count_str, True, config.COLOR_TEXT)
        self.screen.blit(count_text, (480, panel_y + 72))

        # right-side status block
        conn_str = "● LIVE" if connected else "● NO SIGNAL"
        conn_color = config.COLOR_TEXT if connected else config.COLOR_WARN
        conn_text = self.font_hud_small.render(conn_str, True, conn_color)
        self.screen.blit(conn_text, (self.width - 260, panel_y + 8))

        fps_text = self.font_hud_small.render(f"{fps:.0f} FPS", True, config.COLOR_TEXT_DIM)
        self.screen.blit(fps_text, (self.width - 260, panel_y + 30))

        if paused:
            pause_text = self.font_hud_small.render("PAUSED (space to resume)", True, config.COLOR_WARN)
            self.screen.blit(pause_text, (self.width - 260, panel_y + 52))

        hint_text = self.font_label.render("ESC quit  |  SPACE pause  |  S screenshot", True, config.COLOR_TEXT_DIM)
        self.screen.blit(hint_text, (self.width - 260, panel_y + 74))

    def clear(self):
        self.screen.fill(config.COLOR_BG)