import os
import pygame

from constants import (
    FONT_PATH, SCREEN_W, C_COUNTER, CUSTOMER_COLORS,
)


# ── Asset Loader ───────────────────────────────────────────────────────────────
def load_img(path, size=None, fallback_color=(100, 80, 60), fallback_size=(32, 32)):
    """Load an image if it exists, otherwise return a coloured placeholder surface."""
    if os.path.exists(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            if size:
                img = pygame.transform.smoothscale(img, size)
            return img
        except Exception:
            pass
    # bg.png gets None so the caller draws its own plain-colour fallback.
    # bg_night.png gets a dark semi-transparent surface so night blending works
    # even without a real asset file.
    basename = os.path.basename(path)
    if basename in ("bg.png", "bg.jpeg"):
        return None
    if basename == "bg_night.png":
        sz = size or fallback_size
        night_surf = pygame.Surface(sz, pygame.SRCALPHA)
        night_surf.fill((10, 5, 30, 200))   # deep dark-blue tint
        # Add a few pixel "stars"
        import random
        rng = random.Random(42)             # fixed seed so stars don't flicker
        for _ in range(60):
            sx = rng.randint(0, sz[0] - 1)
            sy = rng.randint(0, sz[1] - 1)
            brightness = rng.randint(160, 255)
            pygame.draw.circle(night_surf, (brightness, brightness, brightness, 200), (sx, sy), 1)
        return night_surf
    sz = size or fallback_size
    surf = pygame.Surface(sz, pygame.SRCALPHA)
    surf.fill(fallback_color)
    return surf


def load_all_assets(scene_h: int) -> dict:
    """Load (or generate placeholder for) every asset the game needs."""
    os.makedirs("assets", exist_ok=True)
    a = {}

    # Support both bg.png and bg.jpeg
    _bg_path = "assets/bg.png" if os.path.exists("assets/bg.png") else "assets/bg.jpeg"
    a["bg"]       = load_img(_bg_path,               (SCREEN_W, scene_h), (59, 37, 16))
    a["bg_night"] = load_img("assets/bg_night.png", (SCREEN_W, scene_h), (30, 18,  8))
    a["hud_bg"]   = load_img("assets/hud_bg.png",   (SCREEN_W, 60),      (61, 37, 16))
    a["counter"]  = load_img("assets/counter.png",  (SCREEN_W, 80),      C_COUNTER)
    a["barista"]  = load_img("assets/barista.png",  (97, 95),            (46, 145, 87))

    for i in range(1, 4):
        col = CUSTOMER_COLORS[i - 1]
        a[f"customer_{i}"]           = load_img(f"assets/customer{i}.png",            (120, 150), col)
        a[f"customer_right_{i}"]     = load_img(f"assets/customer_right_{i}.png",     (120, 150), col)
        a[f"customer_back_{i}"]      = load_img(f"assets/customer_back_{i}.png",      (120, 150), col)
        a[f"customer_sit_right_{i}"] = load_img(f"assets/customer_sit_right_{i}.png", (120, 150), col)
        a[f"customer_sit_left_{i}"]  = load_img(f"assets/customer_sit_left_{i}.png",  (120, 150), col)
        # Left-walking sprite: load directly (no flip needed)
        a[f"customer_left_{i}"] = load_img(f"assets/customer_left_{i}.png", (120, 150), col)

    drink_colors = {
        "espresso":      (70,  35,  10),
        "latte":         (210, 180, 130),
        "cappuccino":    (190, 140,  80),
        "mocha":         (60,  30,  10),
        "tea":           (100, 180, 100),
        "caramel_latte": (210, 155,  50),
    }
    for key, col in drink_colors.items():
        a[key] = load_img(f"assets/{key}.png", (32, 32), col)

    # ── Completed brew pop-out textures (128×128) ──────────────────────────────
    complete_colors = {
        "tea":           (100, 180, 100),
        "espresso":      (70,  35,  10),
        "latte":         (210, 180, 130),
        "cappuccino":    (190, 140,  80),
        "mocha":         (60,  30,  10),
        "caramel_latte": (210, 155,  50),
    }
    for key, col in complete_colors.items():
        a[f"{key}_complete"] = load_img(f"assets/{key}_complete.png", (128, 128), col)

    # ── Ingredient tokens (64×64, for brewing UI drag tokens) ─────────────────
    ingredient_colors = {
        "water":        (100, 185, 255),
        "tea_leaf":     (60,  140,  60),
        "honey":        (255, 184,   0),
        "grounds":      (50,   25,   5),
        "espresso_shot":(70,   35,  10),
        "milk":         (240, 230, 210),
        "foam":         (250, 248, 245),
        "choco":        (80,   40,   5),
        "cream":        (255, 245, 225),
        "caramel":      (210, 130,  15),
    }
    for key, col in ingredient_colors.items():
        a[f"ing_{key}"] = load_img(f"assets/{key}.png", (64, 64), col)

    # Door animation frames
    a["door_close"]  = load_img("assets/door_close.png",  (2000, 2000), (90, 55, 22))
    a["door_slight"] = load_img("assets/door_slight.png", (120, 160), (90, 55, 22))
    a["door_open"]   = load_img("assets/door_open.png",   (120, 160), (90, 55, 22))

    _brew_bg_path = "assets/brewing_bg.png" if os.path.exists("assets/brewing_bg.png") else "assets/brewing_bg.jpeg"
    a["brewing_bg"] = load_img(_brew_bg_path, None, (55, 35, 12))
    _shelf_path = "assets/brewing_shelf.png" if os.path.exists("assets/brewing_shelf.png") else "assets/brewing_shelf.jpeg"
    a["brewing_shelf"] = load_img(_shelf_path, None, (90, 55, 22))
    a["complete_btn"]   = load_img("assets/complete_btn.png",  None, (80, 40, 10))
    a["notif_normal"]   = load_img("assets/notif_normal.png",  None, (180, 140, 20))
    a["notif_danger"]   = load_img("assets/notif_danger.png",  None, (160,  30, 20))
    a["shop_bg"] = load_img("assets/shop_bg.png",      (612, 408),      (45, 31, 10))
    a["day_complete_bg"] = load_img("assets/day_complete_bg.png", (420, 240), (45, 31, 10))
    a["bot_bg"]       = load_img("assets/bot_bg.png",       (SCREEN_W,  46), (45, 31, 10))
    a["bottom_panel"] = load_img("assets/bottom_panel.png", (SCREEN_W, 254), (35, 22,  8))
    a["coin"] = load_img("assets/coin.png", (98, 98), (255, 224, 102))

    # ── brew_cup_empty: pre-processed PNG (transparent BG + interior) ────────
    # The PNG in assets/ already has black BG and white interior removed —
    # only the dark-brown outline + white handle remain. Load it directly.
    a["brew_cup_empty"] = load_img("assets/brew_cup_empty.png", None, (80, 40, 10))

    # ── Completed brew textures (pixel-art finished drinks) ───────────────────
    brew_complete_colors = {
        "tea":           (100, 180, 100),
        "espresso":      (70,   35,  10),
        "latte":         (210, 180, 130),
        "cappuccino":    (190, 140,  80),
        "mocha":         (60,   30,  10),
        "caramel_latte": (210, 155,  50),
    }
    for key, col in brew_complete_colors.items():
        a[f"{key}_complete"] = load_img(f"assets/{key}_complete.png", (200, 180), col)
    a["star"] = load_img("assets/star.png", (20, 20), (255, 224, 102))

    # Table/chair assets — chair1 = occupied (with cups), chair2 = empty
    a["table_occupied"]     = load_img("assets/chair1.png",           (200, 180), (90, 55, 22))
    a["table_empty"]        = load_img("assets/chair2.png",           (200, 180), (90, 55, 22))
    a["left_coffee_cup"]    = load_img("assets/left_coffee_cup.png",  (200, 180), (90, 55, 22))
    a["right_coffee_cup"]   = load_img("assets/right_coffee_cup.png", (200, 180), (90, 55, 22))
    # Make black background transparent
    for key in ("table_occupied", "table_empty", "left_coffee_cup", "right_coffee_cup"):
        if a.get(key):
            a[key].set_colorkey((0, 0, 0))

    # Ceiling fan animation frames (4.png – 7.png, placed in assets/)
    fan_frames = []
    for fname in ("4.png", "5.png", "6.png", "7.png"):
        frame = load_img(f"assets/{fname}", (220, 160), (60, 40, 20))
        fan_frames.append(frame)
    a["fan_frames"] = fan_frames

    return a


# ── Font Helper ────────────────────────────────────────────────────────────────
class Fonts:
    def __init__(self):
        pygame.font.init()
        if FONT_PATH and os.path.exists(FONT_PATH):
            self.tiny   = pygame.font.Font(FONT_PATH, 11)
            self.small  = pygame.font.Font(FONT_PATH, 13)
            self.medium = pygame.font.Font(FONT_PATH, 17)
            self.large  = pygame.font.Font(FONT_PATH, 23)
            self.title  = pygame.font.Font(FONT_PATH, 32)
        else:
            self.tiny   = pygame.font.SysFont("monospace", 11, bold=True)
            self.small  = pygame.font.SysFont("monospace", 13, bold=True)
            self.medium = pygame.font.SysFont("monospace", 16, bold=True)
            self.large  = pygame.font.SysFont("monospace", 22, bold=True)
            self.title  = pygame.font.SysFont("monospace", 30, bold=True)