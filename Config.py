# ==================== config.py ====================
# All tunable settings live here so nothing else needs editing
# when you change hardware setup or want a different look/feel.

# ---- Serial ----
SERIAL_PORT = '/dev/ttyUSB0'   # change to your port (e.g. COM4 on Windows)
BAUD_RATE = 9600
RECONNECT_DELAY = 2.0          # seconds between reconnect attempts if port drops

# ---- Sweep geometry (must match the Arduino sketch) ----
MIN_ANGLE = 15
MAX_ANGLE = 165
MAX_RANGE_CM = 400

# ---- Motion / speed ----
SPEED_SMOOTHING_SAMPLES = 4     # moving-average window per angle
APPROACH_THRESHOLD = 2.0        # cm/s above this = "approaching"
RECEDE_THRESHOLD = -2.0         # cm/s below this = "receding"

# ---- Blip / trail behavior ----
BLIP_FADE_TIME = 2.5            # seconds before a blip fully disappears
SWEEP_TRAIL_LENGTH = 25         # how many past sweep-line positions to fade out
TRACK_MATCH_ANGLE_TOLERANCE = 6 # degrees; used to keep the same "object id" across sweeps
TRACK_MATCH_DIST_TOLERANCE = 25 # cm

# ---- Display ----
FULLSCREEN = True
WINDOW_SIZE = (1100, 700)       # used only if FULLSCREEN = False
FPS = 60
HUD_HEIGHT = 100

# ---- Colors (R, G, B) ----
COLOR_BG = (4, 12, 6)
COLOR_GRID = (12, 90, 24)
COLOR_GRID_BRIGHT = (25, 160, 45)
COLOR_SWEEP = (40, 255, 90)
COLOR_SWEEP_TRAIL = (20, 120, 45)
COLOR_APPROACH = (255, 70, 70)
COLOR_RECEDE = (80, 170, 255)
COLOR_STATIONARY = (230, 230, 230)
COLOR_TEXT = (60, 255, 110)
COLOR_TEXT_DIM = (20, 110, 45)
COLOR_HUD_BG = (0, 0, 0)
COLOR_WARN = (255, 60, 60)