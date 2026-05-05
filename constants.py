# ── Screen / Timing ────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60
FONT_PATH = "assets/font.ttf"   # LiberationMono Bold — crisp monospace for that café tycoon feel

WALK_SPEED      = 120.0   # pixels per second
ORDER_TIME_BASE = 18      # seconds before an order expires

# ── Pixel Palette ──────────────────────────────────────────────────────────────
C_BG      = (26,  18,   8)
C_BROWN   = (59,  37,  16)
C_GOLD    = (255, 224, 102)
C_CREAM   = (245, 230, 200)
C_GREEN   = (46,  204,  64)
C_RED     = (231,  76,  60)
C_DARK    = (20,  12,   4)
C_PANEL   = (45,  31,  10)
C_BORDER  = (139, 105,  20)
C_COUNTER = (139,  90,  32)
C_WHITE   = (255, 255, 255)
C_GRAY    = (120, 100,  70)

# ── Drink Definitions  {name: (price, rep_gain, color_hint)} ──────────────────
# Rep gains: Tea=1, Espresso=2, Latte=3, Cappuccino=3, Mocha=4, Caramel Latte=5
DRINKS = {
    "Tea":          (2, 1, (100, 180, 100)),
    "Espresso":     (3, 2, (80,  40,  10)),
    "Latte":        (4, 3, (210, 180, 130)),
    "Cappuccino":   (4, 3, (190, 140,  80)),
    "Mocha":        (5, 4, (60,  30,  10)),
    "Caramel Latte":(6, 5, (210, 155,  50)),
}
DRINK_NAMES = list(DRINKS.keys())

# ── Shop unlock requirements {name: (coin_cost, rep_required)} ─────────────────
# Tea starts available (0 rep). Each next drink needs +10 more rep.
SHOP_UNLOCK = {
    "Tea":          (10,  0),
    "Espresso":     (15, 10),
    "Latte":        (20, 20),
    "Cappuccino":   (20, 30),
    "Mocha":        (30, 40),
    "Caramel Latte":(35, 50),
}

# ── Visual Variety ─────────────────────────────────────────────────────────────
CUSTOMER_COLORS = [
    (230, 126,  34), (52, 152, 219), (155,  89, 182),
    (231,  76,  60), (26, 188, 156), (241, 196,  15),
]
SKIN_TONES = [(245, 203, 167), (212, 165, 116), (139,  98,  64)]