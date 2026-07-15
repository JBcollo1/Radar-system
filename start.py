

import time
import pygame

import config
from serial_reader import SerialReader
from tracker import Tracker
from renderer import Renderer


def main():
    pygame.init()

    if config.FULLSCREEN:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode(config.WINDOW_SIZE)
    pygame.display.set_caption("Ultrasonic Radar")

    clock = pygame.time.Clock()
    renderer = Renderer(screen)
    reader = SerialReader()
    tracker = Tracker()

    current_angle = config.MIN_ANGLE
    current_distance = -1
    current_speed = 0.0
    paused = False

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_s:
                    fname = f"radar_capture_{int(time.time())}.png"
                    pygame.image.save(screen, fname)
                    print(f"Saved {fname}")

        if not paused:
            new_readings = reader.drain_new_readings()
            for r in new_readings:
                current_angle = r.angle
                current_distance = r.distance
                current_speed = r.speed
                tracker.ingest(r.angle, r.distance, r.speed)

        renderer.clear()
        renderer.draw_grid()

        if not paused:
            renderer.update_sweep_trail(current_angle)
        renderer.draw_sweep(current_angle)
        renderer.draw_objects(tracker.active_objects())
        renderer.draw_scanline_effect()
        renderer.draw_hud(
            current_angle, current_distance, current_speed,
            reader.is_connected(), tracker.closest_object(),
            clock.get_fps(), paused
        )

        pygame.display.flip()
        clock.tick(config.FPS)

    reader.stop()
    pygame.quit()


if __name__ == "__main__":
    main()