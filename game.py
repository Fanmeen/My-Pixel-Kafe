import random

import pygame

from constants import (
    SCREEN_W, SCREEN_H, FPS,
    C_BG, C_PANEL, C_BORDER, C_BROWN, C_GOLD, C_CREAM,
    C_GREEN, C_RED, C_DARK, C_COUNTER, C_GRAY, C_WHITE,
    DRINKS, DRINK_NAMES, SHOP_UNLOCK,
)
from assets import Fonts, load_all_assets
from ui import Button, OrderTicket, draw_pixel_rect, draw_text, draw_bar
from entities import Order, Customer
from brewing_ui import BrewingUI


class CafeTycoon:
    HUD_H      = 60
    SCENE_H    = 400
    ORDERS_Y   = HUD_H + SCENE_H + 6
    ORDERS_H   = 147
    TICKET_Y   = 495
    MENU_Y     = 621
    MENU_BTN_W = 148
    MENU_BTN_H = 23
    BOT_Y      = 663
    BOT_BTN_H  = 29

    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("☕My Pixel Kafé")
        self.clock  = pygame.time.Clock()
        self.fonts  = Fonts()
        self.assets = load_all_assets(self.SCENE_H)
        self.brewing_ui = BrewingUI(self.assets, self.fonts)
        self._pending_brew_drink = None   # set when brewing completes
        self._init_state()
        self._build_ui()
        self._init_audio()
        self.state = "menu"   # "menu" | "game"
        # Rects set by _draw_main_menu each frame
        self._menu_play_rect     = pygame.Rect(0, 0, 0, 0)
        self._menu_settings_rect = pygame.Rect(0, 0, 0, 0)
        self._settings_close_rect = pygame.Rect(0, 0, 0, 0)
        # GIF background for main menu
        self._gif_frames   = []   # list of scaled pygame.Surface
        self._gif_delays   = []   # ms per frame
        self._gif_frame    = 0
        self._gif_accum    = 0.0
        self._load_menu_gif()

    def _init_state(self):
        self.coins           = 10
        self.rep             = 0
        self.max_rep         = 100
        self.day             = 1
        self.hour            = 7
        self.minute          = 0
        self.game_hour_len   = 3.0
        self.hour_accum      = 0.0
        self._is_night       = False
        self.orders: list[Order]       = []
        self.customers: list[Customer] = []
        self.order_id_ctr    = 0
        self.cust_id_ctr     = 0
        self.spawn_timer     = 0.0
        self.spawn_interval  = 5.0
        self.max_orders      = 5
        self.day_coins_start = self.coins
        self.day_rep_start   = self.rep
        self.running         = True
        self.day_over        = False
        self.notifications   = []
        self.used_slots: set = set()
        self.settings_open   = False
        self.shop_open       = False
        # Audio
        self.music_vol       = 0.5
        self.sfx_vol         = 0.7
        self._dragging_slider = None   # None | "music" | "sfx"
        self._slider_rects    = {}     # key -> pygame.Rect (filled each draw)
        self.fan_frame_idx   = 0
        self.fan_frame_accum = 0.0
        self.unlocked_drinks: set = {"Tea"}   # Tea is always available from day 1
        self._shop_rects      = {}
        self._shop_close_rect = pygame.Rect(0, 0, 0, 0)
        self.recipe_book_open = False
        self.door_open_timer  = 0.0
        self.door_open_dur    = 1.8
        self._serve_cooldown  = 0.0

        self.seats = [
            {"x": 180, "y": 190, "cy_offset": 120, "occupied": False, "sit_timer": 0.0, "side": "left",  "drink": None},  # top-left
            {"x": 140, "y": 300, "cy_offset": 120, "occupied": False, "sit_timer": 0.0, "side": "right", "drink": None},  # bottom-left
            {"x": 900, "y": 200, "cy_offset": 120, "occupied": False, "sit_timer": 0.0, "side": "left",  "drink": None},  # top-right
            {"x": 900, "y": 300, "cy_offset": 120, "occupied": False, "sit_timer": 0.0, "side": "right", "drink": None},  # bottom-right
        ]

    def _build_ui(self):
        self._rebuild_menu_buttons()
        self._build_bot_buttons()

    # ── Audio ──────────────────────────────────────────────────────────────────
    def _init_audio(self):
        """Generate SFX procedurally. Place your music file at assets/music.ogg
        (also accepts .mp3 / .wav) and it will loop automatically."""
        import array, math
        self._sounds = {}
        self._music_channel = None
        try:
            pygame.mixer.init()
            sr = 44100

            def make_buf(gen_fn, duration):
                n = int(sr * duration)
                buf = array.array('h')
                for i in range(n):
                    s = max(-32767, min(32767, int(gen_fn(i, n, sr))))
                    buf.append(s); buf.append(s)
                return buf

            # ── Serve / coin earned: ascending ding ───────────────────────────
            def serve_gen(i, n, sr):
                t = i / sr
                env = math.exp(-t * 6)
                v = (math.sin(2*math.pi*523.25*t) +
                     math.sin(2*math.pi*659.25*t) * 0.7 +
                     math.sin(2*math.pi*783.99*t) * 0.5)
                return 0.28 * 32767 * v * env

            self._sounds["serve"] = pygame.mixer.Sound(buffer=make_buf(serve_gen, 0.5))

            # ── Button click ──────────────────────────────────────────────────
            def click_gen(i, n, sr):
                t = i / sr
                return 0.3 * 32767 * math.sin(2*math.pi*900*t) * math.exp(-t * 40)

            self._sounds["click"] = pygame.mixer.Sound(buffer=make_buf(click_gen, 0.08))

            # ── Error / fail: descending bloop ────────────────────────────────
            def fail_gen(i, n, sr):
                t = i / sr
                return 0.3 * 32767 * math.sin(2*math.pi*(440 - 200*(t/0.22))*t) * (1 - t/0.22)

            self._sounds["fail"] = pygame.mixer.Sound(buffer=make_buf(fail_gen, 0.22))

            # ── Slider drag tick ──────────────────────────────────────────────
            def tick_gen(i, n, sr):
                t = i / sr
                return 0.2 * 32767 * math.sin(2*math.pi*1200*t) * math.exp(-t * 80)

            self._sounds["tick"] = pygame.mixer.Sound(buffer=make_buf(tick_gen, 0.04))

            # ── Door bell sound effect ───────────────────────────────────────
            import os as _os
            if _os.path.exists("assets/door_bell.mp3"):
                self._sounds["door_bell"] = pygame.mixer.Sound("assets/door_bell.mp3")

            # ── Background music from file ────────────────────────────────────
            self._load_music()

        except Exception as e:
            print(f"[Audio] init failed: {e}")

    def _load_music(self):
        """Load and loop background music from assets/music.ogg/.mp3/.wav if present."""
        import os
        for ext in ("ogg", "mp3", "wav"):
            path = f"assets/music.{ext}"
            if os.path.exists(path):
                try:
                    pygame.mixer.music.load(path)
                    pygame.mixer.music.set_volume(self.music_vol)
                    pygame.mixer.music.play(loops=-1)
                    return
                except Exception as e:
                    print(f"[Audio] Could not load {path}: {e}")

    def _load_menu_gif(self):
        """Load GIF frames directly into pygame surfaces using imageio."""
        import os
        self._gif_raw = []

        path = None
        for candidate in ("assets/menu_bg.gif", "assets/menu_bg.png",
                          "assets/menu_bg.jpg", "assets/menu_bg.jpeg"):
            if os.path.exists(candidate):
                path = candidate
                break

        if path is None:
            print("[BG] No menu_bg file found in assets/")
            return

        self._gif_path = path   # save for _ensure_gif_surfaces

    def _ensure_gif_surfaces(self):
        """Build pygame surfaces from GIF — called on first menu draw when display is ready."""
        if self._gif_frames:
            return
        path = getattr(self, "_gif_path", None)
        if not path:
            return
        try:
            from PIL import Image
            img = Image.open(path)
            n = getattr(img, "n_frames", 1)
            print(f"[BG] Loading {n} frames from {path}...")

            # Maintain a composited RGBA canvas so disposal/transparency between
            # frames is handled correctly (prevents washed-out artefacts).
            canvas = Image.new("RGBA", img.size, (0, 0, 0, 255))
            out_w, out_h = SCREEN_W, SCREEN_H

            for i in range(n):
                img.seek(i)
                delay = max(40, img.info.get("duration", 80))

                # Convert palette + transparency to full RGBA before compositing.
                # This is the key step: working in RGBA from the start avoids the
                # colour-shift / blur that comes from palette→RGB conversion later.
                frame = img.convert("RGBA")

                disposal = img.disposal_method if hasattr(img, "disposal_method") else 0
                canvas.paste(frame, (0, 0), frame)

                # Always use LANCZOS (high-quality Sinc filter) for the resize —
                # it produces crisp, sharp results whether we're up- or down-scaling.
                # NEAREST was the old default for "large" GIFs and was the main
                # cause of the blurry/blocky appearance on screen.
                scaled_pil = canvas.resize((out_w, out_h), Image.LANCZOS)

                # Convert to RGB *after* scaling so the colour data is already
                # in the final resolution; avoids any double-conversion artefacts.
                scaled_rgb = scaled_pil.convert("RGB")
                surf = pygame.image.fromstring(scaled_rgb.tobytes(),
                                               scaled_rgb.size, "RGB")
                surf = surf.convert()   # optimise for fast blitting
                self._gif_frames.append(surf)
                self._gif_delays.append(delay)

                if disposal == 2:   # GIF disposal: restore to background colour
                    canvas = Image.new("RGBA", img.size, (0, 0, 0, 255))

            self._gif_frame = 0
            self._gif_accum = 0.0
            self._gif_last_ms = pygame.time.get_ticks()
            print(f"[BG] Ready — {len(self._gif_frames)} frames loaded")
        except Exception as e:
            print(f"[BG] Error loading gif surfaces: {e}")
            import traceback; traceback.print_exc()

    def _play_sfx(self, name):
        """Play a named SFX at the current sfx_vol."""
        snd = self._sounds.get(name)
        if not snd:
            return
        try:
            ch = pygame.mixer.find_channel()
            if ch:
                ch.set_volume(self.sfx_vol)
                ch.play(snd)
        except Exception:
            pass

    def _apply_volumes(self):
        """Push current volume values to the mixer."""
        try:
            pygame.mixer.music.set_volume(self.music_vol)
        except Exception:
            pass

    def _update_slider_from_mouse(self, key, mx):
        """Recalculate a volume from mouse x, clamped to slider track."""
        rect = self._slider_rects.get(key)
        if not rect:
            return
        ratio = (mx - rect.x) / max(1, rect.width)
        ratio = max(0.0, min(1.0, ratio))
        if key == "music":
            self.music_vol = ratio
        else:
            self.sfx_vol = ratio
        self._apply_volumes()
        self._play_sfx("tick")

    def _draw_slider(self, track_rect, value):
        """Render a volume slider bar with thumb."""
        pygame.draw.rect(self.screen, C_DARK,   track_rect, border_radius=6)
        pygame.draw.rect(self.screen, C_BORDER, track_rect, 2, border_radius=6)
        fill_w = int(track_rect.width * value)
        if fill_w > 4:
            fill_r = pygame.Rect(track_rect.x + 2, track_rect.y + 2,
                                 fill_w - 4, track_rect.height - 4)
            pygame.draw.rect(self.screen, C_GOLD, fill_r, border_radius=4)
        tx = track_rect.x + int(track_rect.width * value)
        tx = max(track_rect.x + 6, min(track_rect.right - 6, tx))
        pygame.draw.circle(self.screen, C_CREAM,  (tx, track_rect.centery), 8)
        pygame.draw.circle(self.screen, C_BORDER, (tx, track_rect.centery), 8, 2)

    # ── Main Menu ──────────────────────────────────────────────────────────────
    def _load_menu_textures(self):
        """Crop texture.png into wood, parchment and leather sub-surfaces."""
        import os
        if not os.path.exists("assets/texture.png"):
            self._tex_wood      = None
            self._tex_parchment = None
            self._tex_leather   = None
            return
        raw = pygame.image.load("assets/texture.png").convert_alpha()
        w, h = raw.get_size()
        # Top-left half  → wood
        self._tex_wood      = raw.subsurface(pygame.Rect(0,     0,     w//2, h//2))
        # Top-right half → parchment
        self._tex_parchment = raw.subsurface(pygame.Rect(w//2,  0,     w//2, h//2))
        # Bottom half    → leather
        self._tex_leather   = raw.subsurface(pygame.Rect(0,     h//2,  w,    h//2))

    def _draw_textured_box(self, tex, rect, alpha=200, border_color=None, radius=10):
        """Tile/scale a texture into rect with optional alpha and border."""
        if tex is None:
            s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            s.fill((30, 15, 0, alpha))
            self.screen.blit(s, rect.topleft)
        else:
            scaled = pygame.transform.scale(tex, (rect.width, rect.height))
            s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            s.blit(scaled, (0, 0))
            s.set_alpha(alpha)
            self.screen.blit(s, rect.topleft)
        if border_color:
            pygame.draw.rect(self.screen, border_color, rect, 2, border_radius=radius)

    def _draw_main_menu(self):
        """Full-screen main menu — cinematic layout."""
        self._ensure_gif_surfaces()

        # ── Background ────────────────────────────────────────────────────────
        if self._gif_frames:
            now = pygame.time.get_ticks()
            if not hasattr(self, "_gif_last_ms"):
                self._gif_last_ms = now
            self._gif_accum += now - self._gif_last_ms
            self._gif_last_ms = now
            delay = self._gif_delays[self._gif_frame] or 80
            while self._gif_accum >= delay:
                self._gif_accum -= delay
                self._gif_frame = (self._gif_frame + 1) % len(self._gif_frames)
                delay = self._gif_delays[self._gif_frame] or 80
            self.screen.blit(self._gif_frames[self._gif_frame], (0, 0))
        else:
            self._draw_scene()

        cx    = SCREEN_W // 2
        cy    = SCREEN_H // 2
        mouse = pygame.mouse.get_pos()

        # ── Subtle overall dark tint so text is always readable ───────────────
        tint = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        tint.fill((0, 0, 0, 45))
        self.screen.blit(tint, (0, 0))

        # ── Load logo once ────────────────────────────────────────────────────
        if not hasattr(self, "_menu_logo"):
            import os
            if os.path.exists("assets/logo.png"):
                raw = pygame.image.load("assets/logo.png").convert_alpha()
                raw.set_colorkey((0, 0, 0))
                self._menu_logo = raw
            else:
                self._menu_logo = None

        # ── TOP-LEFT logo ─────────────────────────────────────────────────────
        logo_w, logo_h = 320, 320
        lx, ly = 70, 20
        if self._menu_logo:
            logo_scaled = pygame.transform.smoothscale(self._menu_logo, (logo_w, logo_h))
            self.screen.blit(logo_scaled, (lx, ly))
        else:
            # Fallback text title if logo PNG missing
            draw_text(self.screen, self.fonts, "☕  My Pixel Kafé",
                      (lx, ly + 30), C_GOLD, "title", "topleft")
            draw_text(self.screen, self.fonts, "Your café, your rules.",
                      (lx, ly + 72), C_CREAM, "small", "topleft")

        # ── Load button PNGs once ─────────────────────────────────────────────
        if not hasattr(self, "_btn_play_img"):
            import os
            def _load_btn(path):
                if os.path.exists(path):
                    img = pygame.image.load(path).convert_alpha()
                    img.set_colorkey((0, 0, 0))
                    return img
                return None
            self._btn_play_img     = _load_btn("assets/play_btn.png")
            self._btn_settings_img = _load_btn("assets/setting_btn.png")

        # ── Buttons — centered-left, vertically middle of screen ─────────────
        bw, bh = 340, 100
        bx     = 60
        gap    = 16
        play_y = SCREEN_H // 2 + 20
        set_y  = play_y + bh + gap

        def draw_png_btn(img, x, y, w, h, hovered):
            rect = pygame.Rect(x, y, w, h)
            if img:
                scaled = pygame.transform.smoothscale(img, (w, h))
                if hovered:
                    bigger = pygame.transform.smoothscale(img, (w + 14, h + 10))
                    bright = bigger.copy()
                    bright.fill((55, 38, 8), special_flags=pygame.BLEND_RGB_ADD)
                    self.screen.blit(bright, (x - 7, y - 5))
                    rect = pygame.Rect(x - 7, y - 5, w + 14, h + 10)
                else:
                    self.screen.blit(scaled, (x, y))
            else:
                col = (180, 110, 50) if hovered else (130, 80, 30)
                pygame.draw.rect(self.screen, col, rect, border_radius=8)
                pygame.draw.rect(self.screen, C_GOLD, rect, 2, border_radius=8)
                lbl = "PLAY" if y < set_y else "SETTINGS"
                draw_text(self.screen, self.fonts, lbl,
                          (rect.centerx, rect.centery), C_CREAM, "large", "center")
            return rect

        hov_play = pygame.Rect(bx, play_y, bw, bh).collidepoint(mouse)
        self._menu_play_rect = draw_png_btn(
            self._btn_play_img, bx, play_y, bw, bh, hov_play)

        hov_set = pygame.Rect(bx, set_y, bw, bh).collidepoint(mouse)
        self._menu_settings_rect = draw_png_btn(
            self._btn_settings_img, bx, set_y, bw, bh, hov_set)

        # ── Footer ────────────────────────────────────────────────────────────
        draw_text(self.screen, self.fonts, "v1.0  ·  Press ESC to quit",
                  (cx, SCREEN_H - 14), C_GRAY, "tiny", "center")


    def _rebuild_menu_buttons(self):
        MENU_SLOTS = [
            (24,  202), (238, 167), (416, 174),
            (602, 191), (805, 180),
        ]
        self.menu_buttons = []
        unlocked_list = [n for n in DRINK_NAMES if n in self.unlocked_drinks]
        for i, name in enumerate(unlocked_list):
            if i >= len(MENU_SLOTS):
                break
            price, rep, _ = DRINKS[name]
            sx, sw = MENU_SLOTS[i]
            btn = Button(
                (sx, self.MENU_Y, sw, self.MENU_BTN_H),
                f"{name[:4].upper()} {price}c",
                color=(0, 0, 0, 0),
                hover_color=(255, 220, 100, 40),
                border_color=(0, 0, 0, 0),
                icon=self.assets.get(name.lower().replace(" ", "_")),
                tag=name,
            )
            self.menu_buttons.append(btn)

    def _build_bot_buttons(self):
        BOT_SLOTS  = [(34, 298), (344, 246), (602, 288), (902, 344)]
        BOT_CONFIG = [
            ("SHOP",     "shop",    C_CREAM),
            ("RECIPES",  "recipes", C_CREAM),
            ("UPGRADE",  "upgrade", C_CREAM),
            ("NEXT DAY", "nextday", C_GREEN),
        ]
        self.bot_buttons = []
        for (bx, bw), (label, tag, tcol) in zip(BOT_SLOTS, BOT_CONFIG):
            hov = (30, 130, 30, 80) if tag == "nextday" else (255, 220, 100, 40)
            self.bot_buttons.append(Button(
                (bx, self.BOT_Y, bw, self.BOT_BTN_H),
                label, color=(0, 0, 0, 0), hover_color=hov,
                border_color=(0, 0, 0, 0), text_color=tcol, tag=tag,
            ))

        self.order_tickets = []

        SCALE = SCREEN_W / 2928
        gx = int(2723 * SCALE)
        gw = int((2928 - 2723) * SCALE)
        self.settings_btn = Button(
            (gx, 4, gw, 52), "",
            color=(0, 0, 0, 0), hover_color=(255, 255, 255, 30),
            border_color=(0, 0, 0, 0), tag="settings",
        )

    def notify(self, text, color=C_GOLD, duration=2.0):
        self.notifications.append([text, color, duration])

    def spawn_order(self):
        # FIX: Check BOTH limits before creating anything to avoid orphan orders
        if len(self.orders) >= self.max_orders:
            return
        if len([c for c in self.customers if not c.seated]) >= 6:
            return
        available = [n for n in DRINK_NAMES if n in self.unlocked_drinks]
        if not available:
            return

        drink = random.choice(available)
        self.order_id_ctr += 1
        oid = self.order_id_ctr
        self.cust_id_ctr += 1

        # Create order and customer atomically — one always has the other
        self.orders.append(Order(oid, drink))
        # Only count queuing (non-seated) customers for slot assignment
        new_slot = len([c for c in self.customers if not c.seated])
        self.used_slots.add(new_slot)
        self.customers.append(
            Customer(self.cust_id_ctr, drink, new_slot, self.assets, order_id=oid)
        )
        self.door_open_timer = self.door_open_dur
        self._play_sfx("door_bell")

    def serve_order(self, order_id):
        for i, o in enumerate(self.orders):
            if o.id == order_id:
                price, rep_gain, _ = DRINKS[o.drink]
                self.coins += price
                old_rep     = self.rep
                self.rep    = min(self.max_rep, self.rep + rep_gain)
                self.orders.pop(i)
                self._seat_customer(order_id)
                self.notify(f"+{price} coins  +{rep_gain} rep", C_GREEN)
                self._play_sfx("serve")
                self._check_rep_unlocks(old_rep)
                return

    def _seat_customer(self, order_id):
        for c in self.customers:
            if c.order_id == order_id:
                free_seats = [s for s in self.seats if not s["occupied"]]
                free_seat = random.choice(free_seats) if free_seats else None
                if free_seat:
                    free_seat["occupied"] = True
                    free_seat["sit_timer"] = 8.0
                    free_seat["drink"]        = c.drink
                    free_seat["cust_variant"] = c.sprite_variant
                    free_seat["cust_side"]    = free_seat["side"]
                    free_seat["customer"]     = c   # keep reference for drawing
                    c.seated   = True
                    c.sit_side = free_seat["side"]
                    # Place customer on the correct stool (left stool = left side of table, right stool = right side)
                    side = free_seat["side"]
                    if side == "left":
                        # Left stool: roughly x+20 within the 200px wide table image
                        c.x = float(free_seat["x"] + 50)
                    else:
                        # Right stool: roughly x+160 within the 200px wide table image
                        c.x = float(free_seat["x"] + 150)
                    c.y = float(free_seat["y"] + free_seat.get("cy_offset", 115))
                    # Free their queue slot so new customers can fill in
                    self.used_slots.discard(c.slot)
                    c.slot = -1   # sentinel: not in queue
                    self._reorder_queue()
                else:
                    # No seat free — just remove normally
                    self._remove_customer_by_order_id(order_id)
                return
        self._remove_customer_by_order_id(order_id)

    def _check_rep_unlocks(self, old_rep):
        for name, (cost, rep_req) in SHOP_UNLOCK.items():
            if name not in self.unlocked_drinks and rep_req > 0:
                if old_rep < rep_req <= self.rep:
                    self.notify(f"{name} now available in Shop! (need {cost}c)", C_GOLD, 3.0)

    def _remove_customer_by_order_id(self, order_id):
        for i, c in enumerate(self.customers):
            if c.order_id == order_id and not c.seated:
                self.used_slots.discard(c.slot)
                self.customers.pop(i)
                self._reorder_queue()
                return

    def _reorder_queue(self):
        """Reassign slots 0..n-1 for queuing customers only (skip seated ones)."""
        self.used_slots.clear()
        queue = [c for c in self.customers if not c.seated]
        for i, c in enumerate(queue):
            old_slot = c.slot
            c.update_slot(i)
            self.used_slots.add(i)
            # Reset arrived_timer when promoted forward so they aren't
            # instantly servable from a leftover click in the same frame
            if old_slot != i:
                c.arrived_timer = 0.0

    def expire_order(self, order):
        if order in self.orders:
            self.orders.remove(order)
        self._remove_customer_by_order_id(order.id)
        self.rep = max(0, self.rep - 1)
        self.notify("Customer left! -1 rep", C_RED)

    def _shop_buy(self, name):
        coin_cost, rep_req = SHOP_UNLOCK[name]
        if name in self.unlocked_drinks:
            self.notify(f"{name} already on your menu!", C_GRAY)
            return
        if self.rep < rep_req:
            self._play_sfx("fail")
            self.notify(f"Need {rep_req} rep to unlock {name}!", C_RED)
            return
        if self.coins < coin_cost:
            self._play_sfx("fail")
            self.notify(f"Need {coin_cost} coins to buy {name}!", C_RED)
            return
        self.coins -= coin_cost
        self.unlocked_drinks.add(name)
        self._rebuild_menu_buttons()
        self._play_sfx("serve")
        self.notify(f"{name} added to menu & blackboard! ☕", C_GREEN, 3.0)

    def advance_time(self, dt):
        self.hour_accum += dt
        if self.hour_accum >= self.game_hour_len:
            self.hour_accum -= self.game_hour_len
            self.minute += 30
            if self.minute >= 60:
                self.minute = 0
                self.hour  += 1
        # ── Day/Night music switch ────────────────────────────────────────────
        now_night = self.hour >= 19
        if now_night != self._is_night:
            self._is_night = now_night
            try:
                import os as _os
                if now_night:
                    if _os.path.exists("assets/night.ogg"):
                        pygame.mixer.music.load("assets/night.ogg")
                        pygame.mixer.music.set_volume(self.music_vol)
                        pygame.mixer.music.play(loops=-1)
                else:
                    self._load_music()
            except Exception:
                pass
        if self.hour >= 22:
            self.end_day()

    def end_day(self):
        if self.day_over:
            return
        self.day_over         = True
        self.running          = False
        self.recipe_book_open = False   # close recipe book so day-over screen is clear

    def start_new_day(self):
        self.day        += 1
        self.hour        = 7
        self.minute      = 0
        self.hour_accum  = 0.0
        self.orders.clear()
        self.customers.clear()
        self.used_slots.clear()
        self.spawn_timer      = 0.0
        self.day_coins_start  = self.coins
        self.day_rep_start    = self.rep
        self.running          = True
        self.day_over         = False
        self.recipe_book_open = False
        for seat in self.seats:
            seat["occupied"] = False
            seat["sit_timer"] = 0.0
            seat["drink"] = None
        self.notify(f"Day {self.day} begins! ☕", C_GREEN)

    def update(self, dt):
        if self.state == "menu":
            # Don't run any game logic while on the main menu
            for btn in self.menu_buttons + self.bot_buttons:
                btn.update(dt)
            self.settings_btn.update(dt)
            return
        if self.running:
            self.fan_frame_accum += dt
            if self.fan_frame_accum >= 1 / 4:
                self.fan_frame_accum = 0.0
                self.fan_frame_idx = (self.fan_frame_idx + 1) % 4
            self.advance_time(dt)
            self.spawn_timer += dt
            if self.spawn_timer >= self.spawn_interval:
                self.spawn_timer = 0.0
                if random.random() < 0.75:
                    self.spawn_order()

            # Only count down order timers for orders whose customer has arrived.
            # This prevents an order from "expiring" while its customer is still
            # walking in, which used to cause the ticket count to mismatch.
            arrived_oids = {
                c.order_id for c in self.customers
                if not c.walking and not c.leaving and c.arrived_timer >= 0.4
            }
            for o in self.orders:
                if o.id in arrived_oids:
                    o.elapsed += dt

            expired = [o for o in self.orders if o.expired]
            for o in expired:
                self.expire_order(o)

            for c in self.customers:
                if not c.seated:
                    c.update(dt)

            if self.door_open_timer > 0:
                self.door_open_timer = max(0.0, self.door_open_timer - dt)

            if self._serve_cooldown > 0:
                self._serve_cooldown = max(0.0, self._serve_cooldown - dt)

            for seat in self.seats:
                if seat["occupied"]:
                    seat["sit_timer"] -= dt
                    if seat["sit_timer"] <= 0:
                        seat["occupied"] = False
                        seat["drink"] = None
                        # Remove the seated customer from the list now they leave
                        cust = seat.get("customer")
                        if cust and cust in self.customers:
                            self.customers.remove(cust)
                        seat["customer"] = None



        for n in self.notifications[:]:
            n[2] -= dt
            if n[2] <= 0:
                self.notifications.remove(n)

        self.brewing_ui.update(dt)

        # ── Brewing result (polled each frame so it fires even with no events) ─
        done, success = self.brewing_ui.poll()
        if done:
            if self._pending_brew_drink:
                _, order_id = self._pending_brew_drink
                if success:
                    self._serve_cooldown = 0.25
                    self.serve_order(order_id)
                elif self.brewing_ui.wrong_recipe:
                    # Player pressed COMPLETE without following the full recipe
                    self.rep = max(0, self.rep - 2)
                    # Cancel the order so the customer leaves
                    order = next((o for o in self.orders if o.id == order_id), None)
                    if order:
                        self.expire_order(order)
                    self.notify("Incomplete brew! -2 rep ☕", C_RED)
                else:
                    self.notify("Brew cancelled!", C_GRAY)
            self._pending_brew_drink = None

        for btn in self.menu_buttons + self.bot_buttons:
            btn.update(dt)
        self.settings_btn.update(dt)

        self._rebuild_tickets()

    def _rebuild_tickets(self):
        arrived_order_ids = {
            c.order_id for c in self.customers
            if not c.walking and not c.leaving and c.arrived_timer >= 0.4
        }
        visible_orders = [o for o in self.orders if o.id in arrived_order_ids]
        current_ids = [o.id for o in visible_orders]
        ticket_ids  = [t.order.id for t in self.order_tickets]
        if current_ids == ticket_ids:
            return
        self.order_tickets = []
        ticket_area_top = self.ORDERS_Y + 29
        ticket_area_h   = 118
        ty = ticket_area_top + (ticket_area_h - OrderTicket.H) // 2
        for i, o in enumerate(visible_orders):
            x = 26 + i * (OrderTicket.W + 8)
            self.order_tickets.append(OrderTicket(o, x, ty, self.assets, self.fonts))

    def draw(self):
        self.screen.fill(C_BG)

        if self.state == "menu":
            self._draw_main_menu()
            if self.settings_open:
                self._draw_settings()
            pygame.display.flip()
            return

        self._draw_hud()
        self._draw_scene()
        bottom_panel = self.assets.get("bottom_panel")
        if bottom_panel:
            self.screen.blit(bottom_panel, (0, self.ORDERS_Y))
        self._draw_orders_panel()
        self._draw_menu()
        self._draw_bottom_bar()
        if self.day_over:
            self._draw_day_over()
        if self.settings_open:
            self._draw_settings()
        if self.shop_open:
            self._draw_shop()
        if self.recipe_book_open and not self.day_over:
            self._draw_recipe_book()
        self._draw_notifications()
        self.brewing_ui.draw(self.screen)
        pygame.display.flip()

    def _draw_hud(self):
        hud_bg = self.assets.get("hud_bg")
        if hud_bg:
            self.screen.blit(hud_bg, (0, 0))
        else:
            draw_pixel_rect(self.screen, C_PANEL,
                            pygame.Rect(0, 0, SCREEN_W, self.HUD_H), C_BORDER, border=3)

        SCALE = SCREEN_W / 2928
        P1_L = int(40   * SCALE);  P1_R = int(907  * SCALE)
        P2_L = int(938  * SCALE);  P2_R = int(1812 * SCALE)
        P3_L = int(1842 * SCALE);  P3_R = int(2719 * SCALE)
        G_L  = int(2723 * SCALE);  G_R  = int(2928 * SCALE)
        CY   = self.HUD_H // 2

        hour12 = 12 if self.hour % 12 == 0 else self.hour % 12
        ampm   = "AM" if (self.hour % 24) < 12 else "PM"
        P1_CX  = (P1_L + P1_R) // 2
        draw_text(self.screen, self.fonts, f"Day {self.day}",
                  (P1_CX, CY - 14), C_GOLD, "small", "midtop")
        draw_text(self.screen, self.fonts, f"{hour12}:{self.minute:02d} {ampm}",
                  (P1_CX, CY + 2),  C_CREAM, "small", "midtop")

        coin_icon = self.assets.get("coin")
        P2_CX     = (P2_L + P2_R) // 2
        coin_surf  = self.fonts.large.render(f"{self.coins}", False, C_GOLD)
        label_surf = self.fonts.tiny.render("coins", False, C_CREAM)
        text_w     = max(coin_surf.get_width(), label_surf.get_width())
        icon_w     = 40 if coin_icon else 0
        gap        = 8  if coin_icon else 0
        total_w    = icon_w + gap + text_w
        gx         = P2_CX - total_w // 2
        if coin_icon:
            self.screen.blit(pygame.transform.scale(coin_icon, (40, 40)), (gx, CY - 20))
        tx2 = gx + icon_w + gap
        self.screen.blit(coin_surf,  (tx2, CY - 13))
        self.screen.blit(label_surf, (tx2, CY + 8))

        star_icon = self.assets.get("star")
        P3_CX     = (P3_L + P3_R) // 2
        rep_surf  = self.fonts.small.render(f"REP {self.rep}/{self.max_rep}", False, C_CREAM)
        star_size = 20
        gap       = 6
        group_w   = (star_size + gap if star_icon else 0) + rep_surf.get_width()
        gx        = P3_CX - group_w // 2
        if star_icon:
            self.screen.blit(pygame.transform.scale(star_icon, (star_size, star_size)),
                             (gx, CY - star_size // 2 - 6))
            gx += star_size + gap
        self.screen.blit(rep_surf, (gx, CY - 14))
        bar_w = group_w + 20
        draw_bar(self.screen,
                 pygame.Rect(P3_CX - bar_w // 2, CY + 6, bar_w, 10),
                 self.rep, self.max_rep, C_GREEN)

        if self.settings_btn.hovered:
            glow = pygame.Surface((G_R - G_L, self.HUD_H - 8), pygame.SRCALPHA)
            glow.fill((255, 255, 255, 35))
            self.screen.blit(glow, (G_L, 4))

    def _draw_scene(self):
        scene_rect = pygame.Rect(0, self.HUD_H, SCREEN_W, self.SCENE_H)
        bg_day   = self.assets.get("bg")
        bg_night = self.assets.get("bg_night")
        time_frac = self.hour + self.minute / 60.0

        if time_frac < 19:
            night_alpha = 0
        elif time_frac < 21:
            night_alpha = int(255 * (time_frac - 19) / 2.0)
        else:
            night_alpha = 255

        if bg_day:
            self.screen.blit(bg_day, (0, self.HUD_H))
        else:
            pygame.draw.rect(self.screen, (92, 58, 30), scene_rect)

        if bg_night and night_alpha > 0:
            night_copy = bg_night.copy()
            night_copy.set_alpha(night_alpha)
            self.screen.blit(night_copy, (0, self.HUD_H))

        self._draw_ceiling_fan()
        self._draw_door()

        counter_y = self.HUD_H + self.SCENE_H - 90

        LB_CX = 430; LB_Y = 120
        draw_text(self.screen, self.fonts, "── MENU ──",
                  (LB_CX, LB_Y), C_GOLD, "tiny", "midtop")
        if self.unlocked_drinks:
            LINE_H = 13
            for i, name in enumerate(n for n in DRINK_NAMES if n in self.unlocked_drinks):
                price, rep_gain, _ = DRINKS[name]
                draw_text(self.screen, self.fonts,
                          f"{name[:4].upper()}  {price}c (+{rep_gain}rep)",
                          (LB_CX, LB_Y + 14 + i * LINE_H), C_CREAM, "tiny", "midtop")
        else:
            draw_text(self.screen, self.fonts, "Go to SHOP to",
                      (LB_CX, LB_Y + 14), C_GRAY, "tiny", "midtop")
            draw_text(self.screen, self.fonts, "buy your first drink!",
                      (LB_CX, LB_Y + 27), C_GRAY, "tiny", "midtop")

        RB_CX = 780; RB_Y = 135
        next_locked = [(n, c, r) for n, (c, r) in SHOP_UNLOCK.items()
                       if n not in self.unlocked_drinks]
        if next_locked:
            next_name, next_cost, next_rep = next_locked[0]
            draw_text(self.screen, self.fonts, "NEXT UNLOCK",
                      (RB_CX, RB_Y), C_GOLD, "tiny", "midtop")
            draw_text(self.screen, self.fonts, next_name.upper(),
                      (RB_CX, RB_Y + 16), C_CREAM, "small", "midtop")
            if next_rep > self.rep:
                draw_text(self.screen, self.fonts, f"Need {next_rep} rep",
                          (RB_CX, RB_Y + 36), C_RED, "tiny", "midtop")
            else:
                draw_text(self.screen, self.fonts, f"Buy for {next_cost}c!",
                          (RB_CX, RB_Y + 36), C_GREEN, "tiny", "midtop")
        else:
            draw_text(self.screen, self.fonts, "ALL DRINKS",
                      (RB_CX, RB_Y), C_GOLD, "small", "midtop")
            draw_text(self.screen, self.fonts, "UNLOCKED!",
                      (RB_CX, RB_Y + 22), C_GREEN, "small", "midtop")

        barista = self.assets.get("barista")
        bx = int(SCREEN_W / 2.33) - 1
        by = counter_y - 189
        if barista:
            self.screen.blit(barista, (bx, by))
        else:
            self._draw_placeholder_barista(bx, by)

        for seat in self.seats:
            if seat["occupied"]:
                side = seat.get("side", "left")
                # Swap table image based on which side is occupied
                if side == "left":
                    img = self.assets.get("left_coffee_cup")
                else:
                    img = self.assets.get("right_coffee_cup")
            else:
                img = self.assets.get("table_empty")
            if img:
                self.screen.blit(img, (seat["x"], seat["y"]))

        # Build a unified draw list for all customers sorted by Y so that
        # customers lower on screen (higher Y) always render in front —
        # this prevents seated customers from floating over walkers.
        def _draw_customer_entry(c):
            """Return (y, draw_fn) so we can sort everything together."""
            if c.seated:
                seat = next((s for s in self.seats if s.get("customer") is c), None)
                y = c.y
                def _draw_seated(screen=self.screen, cust=c):
                    sprite = cust.assets.get(cust.sprite_key)
                    if sprite:
                        scaled = pygame.transform.scale(sprite, (110, 130))
                        scaled.set_colorkey((0, 0, 0))
                        screen.blit(scaled, (int(cust.x) - 55, int(cust.y) - 130))
                return (y, _draw_seated)
            else:
                def _draw_walking(screen=self.screen, fonts=self.fonts, cust=c):
                    cust.draw(screen, fonts, is_first=(cust.slot == 0))
                return (c.y, _draw_walking)

        draw_entries = [_draw_customer_entry(c) for c in self.customers]
        for _, draw_fn in sorted(draw_entries, key=lambda e: e[0]):
            draw_fn()

    def _draw_ceiling_fan(self):
        frames = self.assets.get("fan_frames", [])
        if not frames:
            return
        frame = frames[self.fan_frame_idx % len(frames)]
        fw, fh = frame.get_size()
        cx = SCREEN_W // 2
        cy = self.HUD_H - 30
        self.screen.blit(frame, (cx - fw // 2, cy))

    def _draw_door(self):
        DOOR_X    = 20
        DOOR_Y    = self.HUD_H + 125
        DOOR_W    = 250
        DOOR_H    = 250

        t = self.door_open_timer / self.door_open_dur if self.door_open_dur > 0 else 0

        if t > 0.55:
            frame_key = "door_open"
        elif t > 0.25:
            frame_key = "door_slight"
        else:
            frame_key = "door_close"

        door_img = self.assets.get(frame_key)
        if not door_img:
            return

        scaled = pygame.transform.scale(door_img, (DOOR_W, DOOR_H))
        self.screen.blit(scaled, (DOOR_X, DOOR_Y))

    def _draw_placeholder_barista(self, x, y):
        pygame.draw.rect(self.screen, (139, 94, 60), (x+12, y,    24, 22), border_radius=2)
        pygame.draw.rect(self.screen, (80,  50, 20), (x+12, y,    24,  8), border_radius=2)
        pygame.draw.rect(self.screen, (46, 139, 87), (x+ 8, y+22, 32, 26), border_radius=2)
        pygame.draw.rect(self.screen, (139, 94, 60), (x,    y+24, 10, 18), border_radius=1)
        pygame.draw.rect(self.screen, (139, 94, 60), (x+38, y+24, 10, 18), border_radius=1)
        pygame.draw.rect(self.screen, (30,  60,140), (x+10, y+48, 12, 16), border_radius=1)
        pygame.draw.rect(self.screen, (30,  60,140), (x+26, y+48, 12, 16), border_radius=1)

    def _draw_orders_panel(self):
        draw_text(self.screen, self.fonts, "PENDING ORDERS — waiting for your brew",
                  (12, self.ORDERS_Y + 6), C_WHITE, "tiny")
        if not self.orders:
            if not self.unlocked_drinks:
                draw_text(self.screen, self.fonts, "Open SHOP and buy Tea to start serving!",
                          (12, self.ORDERS_Y + 55), C_GRAY, "small")
            else:
                draw_text(self.screen, self.fonts, "Waiting for customers...",
                          (12, self.ORDERS_Y + 55), C_GRAY, "small")
        for t in self.order_tickets:
            t.draw(self.screen)

    def _draw_menu(self):
        if self.unlocked_drinks:
            draw_text(self.screen, self.fonts, "COFFEE MENU",
                      (12, self.MENU_Y - 14), C_WHITE, "tiny")
        else:
            draw_text(self.screen, self.fonts, "Buy a drink in SHOP to fill the menu!",
                      (12, self.MENU_Y - 14), C_GRAY, "tiny")

        hovered_drink = next((btn.tag for btn in self.menu_buttons if btn.hovered), None)
        if hovered_drink:
            for t in self.order_tickets:
                if t.order.drink == hovered_drink:
                    pygame.draw.rect(self.screen, C_GOLD,
                                     t.rect.inflate(6, 6), 3, border_radius=6)
        for btn in self.menu_buttons:
            btn.draw(self.screen, self.fonts)

    def _draw_bottom_bar(self):
        for btn in self.bot_buttons:
            btn.draw(self.screen, self.fonts)

    def _draw_shop(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        box_w = 612
        box_h = 408
        bx    = (SCREEN_W - box_w) // 2
        by    = (SCREEN_H - box_h) // 2

        shop_bg = self.assets.get("shop_bg")
        if shop_bg:
            self.screen.blit(shop_bg, (bx, by))
        else:
            draw_pixel_rect(self.screen, C_PANEL, (bx, by, box_w, box_h), C_GOLD, 4)

        draw_text(self.screen, self.fonts, "SHOP — Buy Drinks for your Menu",
                  (bx + box_w // 2, by + 25), C_GOLD, "medium", "midtop")
        draw_text(self.screen, self.fonts,
                  f"Coins: {self.coins}   Rep: {self.rep}/{self.max_rep}",
                  (bx + box_w // 2, by + 47), C_CREAM, "small", "midtop")

        ROW_CY    = [101, 152, 203, 254, 305]
        ICON_SIZE = 46
        ICON_X    = bx + 30
        NAME_X    = bx + 80
        BTN_X     = bx + 490
        BTN_W     = 88
        BTN_H     = 22

        self._shop_rects = {}
        for i, (name, (coin_cost, rep_req)) in enumerate(SHOP_UNLOCK.items()):
            if i >= len(ROW_CY):
                break
            cy         = by + ROW_CY[i]
            purchased  = name in self.unlocked_drinks
            can_rep    = self.rep >= rep_req
            can_afford = self.coins >= coin_cost

            if purchased:
                tint = pygame.Surface((BTN_X - NAME_X + BTN_W, 38), pygame.SRCALPHA)
                tint.fill((40, 120, 40, 55))
                self.screen.blit(tint, (NAME_X, cy - 19))

            icon = self.assets.get(name.lower().replace(" ", "_"))
            if icon:
                self.screen.blit(pygame.transform.scale(icon, (ICON_SIZE, ICON_SIZE)),
                                 (ICON_X, cy - ICON_SIZE // 2))

            _, rep_gain, _ = DRINKS[name]
            name_col = C_GRAY if (not can_rep and not purchased) else C_CREAM
            draw_text(self.screen, self.fonts, name,
                      (NAME_X, cy - 10), name_col, "small")
            draw_text(self.screen, self.fonts, f"+{rep_gain} rep per serve",
                      (NAME_X, cy + 6), C_GRAY, "tiny")

            btn_rect = pygame.Rect(BTN_X, cy - BTN_H // 2, BTN_W, BTN_H)
            btn_cx   = BTN_X + BTN_W // 2

            if purchased:
                s = pygame.Surface((BTN_W, BTN_H), pygame.SRCALPHA)
                pygame.draw.rect(s, (30, 110, 30, 160), (0, 0, BTN_W, BTN_H), border_radius=5)
                self.screen.blit(s, btn_rect.topleft)
                pygame.draw.rect(self.screen, C_GREEN, btn_rect, 2, border_radius=5)
                draw_text(self.screen, self.fonts, "ON MENU \u2713",
                          (btn_cx, cy), C_GREEN, "tiny", "center")
            elif not can_rep:
                s = pygame.Surface((BTN_W, BTN_H), pygame.SRCALPHA)
                pygame.draw.rect(s, (110, 30, 30, 140), (0, 0, BTN_W, BTN_H), border_radius=5)
                self.screen.blit(s, btn_rect.topleft)
                pygame.draw.rect(self.screen, C_RED, btn_rect, 2, border_radius=5)
                draw_text(self.screen, self.fonts, f"Need {rep_req} rep",
                          (btn_cx, cy), C_RED, "tiny", "center")
            else:
                btn_col = (30, 110, 30, 200) if can_afford else (110, 40, 40, 200)
                if btn_rect.collidepoint(pygame.mouse.get_pos()):
                    btn_col = (60, 160, 60, 240) if can_afford else (150, 60, 60, 240)
                s = pygame.Surface((BTN_W, BTN_H), pygame.SRCALPHA)
                pygame.draw.rect(s, btn_col, (0, 0, BTN_W, BTN_H), border_radius=5)
                self.screen.blit(s, btn_rect.topleft)
                pygame.draw.rect(self.screen,
                                 C_GREEN if can_afford else C_RED,
                                 btn_rect, 2, border_radius=5)
                lbl = f"Buy {coin_cost}c" if can_afford else f"Need {coin_cost}c"
                draw_text(self.screen, self.fonts, lbl,
                          (btn_cx, cy), C_CREAM, "tiny", "center")
                self._shop_rects[name] = btn_rect

        close_w, close_h = 169, 30
        close_rect = pygame.Rect(bx + 221, by + 350, close_w, close_h)
        if close_rect.collidepoint(pygame.mouse.get_pos()):
            s = pygame.Surface((close_w, close_h), pygame.SRCALPHA)
            pygame.draw.rect(s, (255, 200, 50, 80), (0, 0, close_w, close_h), border_radius=4)
            self.screen.blit(s, close_rect.topleft)
        draw_text(self.screen, self.fonts, "CLOSE",
                  (close_rect.centerx, close_rect.centery), C_GOLD, "small", "center")
        self._shop_close_rect = close_rect

    def _draw_recipe_book(self):
        """Overlay showing recipes for every unlocked drink."""
        from brewing_ui import RECIPES
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        unlocked = [n for n in DRINK_NAMES if n in self.unlocked_drinks]
        cols      = min(len(unlocked), 3)
        card_w, card_h = 220, 220
        pad       = 18
        total_w   = cols * card_w + (cols - 1) * pad
        bx        = (SCREEN_W - total_w) // 2
        by        = (SCREEN_H - card_h) // 2 - 30

        for idx, name in enumerate(unlocked):
            col  = idx % 3
            row  = idx // 3
            cx_  = bx + col * (card_w + pad)
            cy_  = by + row * (card_h + pad + 10)

            # Card background
            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            pygame.draw.rect(card_surf, (55, 35, 12, 230), (0, 0, card_w, card_h), border_radius=10)
            pygame.draw.rect(card_surf, C_BORDER, (0, 0, card_w, card_h), 2, border_radius=10)
            self.screen.blit(card_surf, (cx_, cy_))

            # Drink icon + name header
            icon = self.assets.get(name.lower().replace(" ", "_"))
            hx   = cx_ + 10
            if icon:
                self.screen.blit(pygame.transform.scale(icon, (28, 28)), (hx, cy_ + 8))
                hx += 34
            draw_text(self.screen, self.fonts, name, (hx, cy_ + 14), C_GOLD, "small")

            # Divider
            pygame.draw.line(self.screen, C_BORDER,
                             (cx_ + 8, cy_ + 42), (cx_ + card_w - 8, cy_ + 42), 1)

            # Ingredients list
            recipe = RECIPES.get(name, [])
            for i, (label, color, icon_char) in enumerate(recipe):
                iy = cy_ + 54 + i * 30
                pygame.draw.circle(self.screen, color, (cx_ + 22, iy + 8), 10)
                pygame.draw.circle(self.screen, C_BORDER, (cx_ + 22, iy + 8), 10, 1)
                draw_text(self.screen, self.fonts, f"{icon_char} {label}",
                          (cx_ + 34, iy + 2), C_CREAM, "small")

            _, rep_gain, _ = DRINKS[name]
            price, _, _    = DRINKS[name]
            draw_text(self.screen, self.fonts, f"${price}  +{rep_gain} rep",
                      (cx_ + card_w // 2, cy_ + card_h - 18), C_GOLD, "tiny", "center")

        # Close button
        close_rect = pygame.Rect(SCREEN_W // 2 - 80, by + (len(unlocked) // 3 + 1) * (card_h + pad + 10) + 10, 160, 34)
        hov = close_rect.collidepoint(pygame.mouse.get_pos())
        s   = pygame.Surface((160, 34), pygame.SRCALPHA)
        pygame.draw.rect(s, (80, 50, 15, 200) if not hov else (120, 80, 20, 240), (0, 0, 160, 34), border_radius=6)
        self.screen.blit(s, close_rect.topleft)
        pygame.draw.rect(self.screen, C_GOLD, close_rect, 2, border_radius=6)
        draw_text(self.screen, self.fonts, "CLOSE",
                  (close_rect.centerx, close_rect.centery), C_GOLD, "small", "center")
        self._recipe_book_close_rect = close_rect

    def _draw_day_over(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        earned = self.coins - self.day_coins_start
        rep_g  = self.rep   - self.day_rep_start
        box_w, box_h = 420, 240
        bx = (SCREEN_W - box_w) // 2
        by = (SCREEN_H - box_h) // 2
        day_bg = self.assets.get("day_complete_bg")
        if day_bg:
            self.screen.blit(pygame.transform.scale(day_bg, (box_w, box_h)), (bx, by))
        else:
            draw_pixel_rect(self.screen, C_PANEL, (bx, by, box_w, box_h), C_GOLD, 4)
        draw_text(self.screen, self.fonts, "DAY COMPLETE!",
                  (SCREEN_W//2, by+20), C_GOLD, "title", "midtop")
        draw_text(self.screen, self.fonts, f"+{earned} coins earned",
                  (SCREEN_W//2, by+76), C_CREAM, "medium", "midtop")
        draw_text(self.screen, self.fonts, f"+{rep_g} reputation gained",
                  (SCREEN_W//2, by+104), C_CREAM, "medium", "midtop")
        draw_text(self.screen, self.fonts,
                  f"Total: {self.coins} coins | Rep {self.rep}/{self.max_rep}",
                  (SCREEN_W//2, by+132), C_GOLD, "small", "midtop")

        next_locked = [(n, c, r) for n, (c, r) in SHOP_UNLOCK.items()
                       if n not in self.unlocked_drinks and r <= self.rep]
        if next_locked:
            n, c, r = next_locked[0]
            draw_text(self.screen, self.fonts, f"Tip: Visit SHOP — {n} is ready to buy! ({c}c)",
                      (SCREEN_W//2, by+158), C_GOLD, "tiny", "midtop")

        btn_rect  = pygame.Rect(SCREEN_W//2-80, by+200, 160, 26)
        draw_text(self.screen, self.fonts, "NEXT DAY  ▶",
                  (SCREEN_W//2, btn_rect.centery), C_GOLD, "medium", "center")
        return btn_rect

    def _draw_settings(self):
        """Full-screen settings panel using setting_bg.png as texture."""
        import math
        t     = pygame.time.get_ticks() / 1000.0
        mouse = pygame.mouse.get_pos()

        # ── 1. TEXTURE BACKGROUND ─────────────────────────────────────────────
        if not hasattr(self, "_setting_bg_tex"):
            import os
            path = "assets/setting_bg.png"
            if os.path.exists(path):
                raw = pygame.image.load(path).convert()
                self._setting_bg_tex = pygame.transform.smoothscale(raw, (SCREEN_W, SCREEN_H))
            else:
                self._setting_bg_tex = None

        if self._setting_bg_tex:
            self.screen.blit(self._setting_bg_tex, (0, 0))
        else:
            self.screen.fill((55, 32, 10))

        # ── 2. DARK VIGNETTE OVERLAY so panel text stays readable ─────────────
        vig = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for cx_v, cy_v in [(0,0),(SCREEN_W,0),(0,SCREEN_H),(SCREEN_W,SCREEN_H)]:
            for r in range(420, 0, -7):
                a = int(38 * (1 - r / 420))
                pygame.draw.circle(vig, (0, 0, 0, a), (cx_v, cy_v), r)
        # Subtle centre warm glow to keep it cozy
        for r in range(340, 0, -6):
            a = int(22 * (1 - r / 340))
            pygame.draw.circle(vig, (255, 180, 60, a), (SCREEN_W // 2, 0), r)
        self.screen.blit(vig, (0, 0))

        # ── 3. CENTRE PANEL ───────────────────────────────────────────────────
        panel_w, panel_h = 1080, 548
        px = (SCREEN_W - panel_w) // 2
        py = (SCREEN_H - panel_h) // 2

        # Drop shadow
        shad = pygame.Surface((panel_w + 20, panel_h + 20), pygame.SRCALPHA)
        pygame.draw.rect(shad, (0, 0, 0, 130),
                         (0, 0, panel_w + 20, panel_h + 20), border_radius=16)
        self.screen.blit(shad, (px - 10, py - 2))

        # Panel fill — semi-transparent dark brown so texture shows through edges
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (28, 15, 4, 232),
                         (0, 0, panel_w, panel_h), border_radius=12)
        self.screen.blit(panel_surf, (px, py))

        # Gold border + inner bevel
        pygame.draw.rect(self.screen, C_BORDER,
                         (px, py, panel_w, panel_h), 3, border_radius=12)
        pygame.draw.rect(self.screen, (110, 78, 24),
                         (px+2, py+2, panel_w-4, panel_h-4), 1, border_radius=11)

        # Corner rivets
        for rcx, rcy in [(px+16,py+16),(px+panel_w-16,py+16),
                          (px+16,py+panel_h-16),(px+panel_w-16,py+panel_h-16)]:
            pygame.draw.circle(self.screen, (50, 32, 8),   (rcx, rcy), 9)
            pygame.draw.circle(self.screen, (130, 95, 35), (rcx-1, rcy-1), 6)
            pygame.draw.circle(self.screen, (160,120, 50), (rcx-2, rcy-2), 3)

        # ── 4. HEADER BANNER ──────────────────────────────────────────────────
        ban_rect = pygame.Rect(px+28, py+10, panel_w-56, 60)
        ban_surf = pygame.Surface((ban_rect.width, ban_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(ban_surf, (55, 34, 8, 215),
                         (0, 0, ban_rect.width, ban_rect.height), border_radius=8)
        self.screen.blit(ban_surf, ban_rect.topleft)
        pygame.draw.rect(self.screen, C_BORDER, ban_rect, 2, border_radius=8)

        # Animated rotating gear
        gcx, gcy = px + 56, py + 40
        ga = t * 0.7
        pygame.draw.circle(self.screen, (75, 50, 16), (gcx, gcy), 13)
        pygame.draw.circle(self.screen, C_BORDER,     (gcx, gcy), 13, 2)
        pygame.draw.circle(self.screen, (30, 18, 5),  (gcx, gcy), 5)
        for i in range(8):
            ang = ga + i * math.pi / 4
            pygame.draw.circle(self.screen, (110, 78, 24),
                               (gcx + int(math.cos(ang)*17), gcy + int(math.sin(ang)*17)), 4)

        draw_text(self.screen, self.fonts, "SETTINGS",
                  (SCREEN_W // 2, py + 40), C_CREAM, "title", "center")

        # ── 5. DIVIDER + DIAMOND ──────────────────────────────────────────────
        div_y = py + 78
        pygame.draw.line(self.screen, C_BORDER,
                         (px+28, div_y), (px+panel_w-28, div_y), 2)
        dcx = SCREEN_W // 2
        pygame.draw.polygon(self.screen, C_WHITE,
                            [(dcx,div_y-5),(dcx+6,div_y),(dcx,div_y+5),(dcx-6,div_y)])

        # ── 6. COLUMN LAYOUT ──────────────────────────────────────────────────
        L       = px + panel_w // 4
        R       = px + panel_w * 3 // 4
        SLW     = panel_w // 2 - 110
        col_top = py + 92

        def _col_header(cx_h, label):
            draw_text(self.screen, self.fonts, label,
                      (cx_h, col_top), C_GOLD, "medium", "midtop")
            lw = 170
            pygame.draw.line(self.screen, (80,55,18),
                             (cx_h-lw//2, col_top+26), (cx_h+lw//2, col_top+26), 1)

        _col_header(L, "GAME INFO")
        _col_header(R, "AUDIO")

        # Vertical divider
        pygame.draw.line(self.screen, (60,40,12),
                         (SCREEN_W//2, py+84), (SCREEN_W//2, py+panel_h-70), 2)

        # ── 7. GAME STATS ─────────────────────────────────────────────────────
        stats = [
            ("Day",            str(self.day)),
            ("Coins",          str(self.coins)),
            ("Reputation",     f"{self.rep} / {self.max_rep}"),
            ("Max Orders",     str(self.max_orders)),
            ("Drinks on Menu", str(len(self.unlocked_drinks))),
        ]
        row_y = col_top + 42
        for label, value in stats:
            row_r = pygame.Rect(px+44, row_y-8, panel_w//2-70, 28)
            if row_r.collidepoint(mouse):
                hl = pygame.Surface((row_r.width, row_r.height), pygame.SRCALPHA)
                pygame.draw.rect(hl, (255,200,80,18),
                                 (0,0,row_r.width,row_r.height), border_radius=4)
                self.screen.blit(hl, row_r.topleft)
            draw_text(self.screen, self.fonts, label,
                      (px+58, row_y), C_GRAY, "small", "midleft")
            draw_text(self.screen, self.fonts, value,
                      (SCREEN_W//2-40, row_y), C_CREAM, "small", "midright")
            for dx in range(px+58+len(label)*7+8, SCREEN_W//2-80, 6):
                pygame.draw.circle(self.screen, (55,36,12), (dx, row_y+1), 1)
            pygame.draw.line(self.screen, (42,26,8),
                             (px+50, row_y+16), (SCREEN_W//2-42, row_y+16), 1)
            row_y += 42

        # ── 8. AUDIO SLIDERS ──────────────────────────────────────────────────
        SLX       = R - SLW // 2
        SLH       = 18
        audio_top = col_top + 42

        def _audio_row(icon, label, vol, key, ay):
            draw_text(self.screen, self.fonts, f"{icon}  {label}",
                      (SLX, ay), C_CREAM, "small", "midleft")
            draw_text(self.screen, self.fonts, f"{int(vol*100)}%",
                      (SLX+SLW, ay), C_GOLD, "small", "midright")
            track = pygame.Rect(SLX, ay+18, SLW, SLH)
            self._draw_slider(track, vol)
            self._slider_rects[key] = track
            bx0 = SLX + SLW + 12
            for bi, bh_d in enumerate([6,10,14,10]):
                filled = (bi/3) <= vol
                bcol = C_GOLD if filled else (50,36,10)
                pygame.draw.rect(self.screen, bcol,
                                 (bx0+bi*7, ay+18+(14-bh_d), 5, bh_d), border_radius=1)

        _audio_row("♪", "Music Volume", self.music_vol, "music", audio_top)
        _audio_row("◉", "SFX Volume",   self.sfx_vol,   "sfx",   audio_top + 68)

        draw_text(self.screen, self.fonts,
                  "Place assets/music.ogg to add background music",
                  (R, audio_top+144), C_GRAY, "tiny", "midtop")

        # ── 9. BUTTONS ────────────────────────────────────────────────────────
        if not hasattr(self, "_btn_back_menu_img"):
            import os
            def _lbtn(p):
                if os.path.exists(p):
                    i = pygame.image.load(p).convert_alpha()
                    i.set_colorkey((0,0,0)); return i
                return None
            self._btn_back_menu_img = _lbtn("assets/back_menu_btn.png")
            self._btn_close_img     = _lbtn("assets/close_btn.png")

        def _pixel_btn(rect, label, base_col, hov_col, bdr_col):
            hov = rect.collidepoint(mouse)
            col = hov_col if hov else base_col
            s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(s, col, (0,0,rect.width,rect.height), border_radius=10)
            self.screen.blit(s, rect.topleft)
            pygame.draw.rect(self.screen, bdr_col, rect, 2, border_radius=10)
            pygame.draw.line(self.screen,
                             (min(255,bdr_col[0]+40),min(255,bdr_col[1]+30),min(255,bdr_col[2]+10)),
                             (rect.x+4, rect.y+2),(rect.right-4, rect.y+2), 1)
            draw_text(self.screen, self.fonts, label,
                      (rect.centerx, rect.centery), bdr_col, "large", "center")

        btn_y = py + panel_h - 68
        self._settings_back_rect = None

        if self.state == "game":
            back_rect = pygame.Rect(SCREEN_W//2-290, btn_y, 255, 50)
            _pixel_btn(back_rect, "<  BACK TO MENU",
                       (60,20,10,180),(90,30,14,220), C_RED)
            self._settings_back_rect = back_rect
            close_rect = pygame.Rect(SCREEN_W//2+35, btn_y, 255, 50)
        else:
            close_rect = pygame.Rect(SCREEN_W//2-127, btn_y, 255, 50)

        _pixel_btn(close_rect, "X  CLOSE",
                   (55,38,10,180),(90,65,15,220), C_GOLD)
        self._settings_close_rect = close_rect


    def _draw_notifications(self):
        for i, (text, color, timer) in enumerate(self.notifications[-3:]):
            alpha = min(255, int(timer * 180))
            y     = 70 + i * 38
            surf  = self.fonts.medium.render(text, True, C_DARK)
            w = surf.get_width() + 24
            h = surf.get_height() + 10
            x = (SCREEN_W - w) // 2
            bg = pygame.Surface((w, h), pygame.SRCALPHA)
            bg.fill((*color, alpha))
            pygame.draw.rect(bg, C_DARK, (0, 0, w, h), 2, border_radius=4)
            self.screen.blit(bg, (x, y))
            self.screen.blit(surf, (x + 12, y + 5))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.settings_open:
                    self.settings_open = False
                elif self.state == "game":
                    self.state = "menu"
                else:
                    return False
                continue

            # ── Global: slider drag (works in any state) ───────────────────
            if self.settings_open:
                if event.type == pygame.MOUSEMOTION and self._dragging_slider:
                    self._update_slider_from_mouse(self._dragging_slider, event.pos[0])
                    continue
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self._dragging_slider = None
                    continue
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Back to Main Menu button
                    back_rect = getattr(self, "_settings_back_rect", None)
                    if back_rect and back_rect.collidepoint(event.pos):
                        self._play_sfx("click")
                        self.settings_open = False
                        self.state = "menu"
                        continue
                    # Close button
                    if self._settings_close_rect.collidepoint(event.pos):
                        self._play_sfx("click")
                        self.settings_open = False
                        continue
                    # Slider hit-test (expand track by ±10px for easier grab)
                    for key, rect in self._slider_rects.items():
                        grab = rect.inflate(0, 20)
                        if grab.collidepoint(event.pos):
                            self._dragging_slider = key
                            self._update_slider_from_mouse(key, event.pos[0])
                            break
                    continue

            # ── Main menu state ────────────────────────────────────────────
            if self.state == "menu":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self._menu_play_rect.collidepoint(event.pos):
                        self._play_sfx("click")
                        self.state = "game"
                    elif self._menu_settings_rect.collidepoint(event.pos):
                        self._play_sfx("click")
                        self.settings_open = True
                continue   # no game events while in menu

            # ── Game state ─────────────────────────────────────────────────
            # Brewing mini-game eats all events while open
            if self.brewing_ui.active:
                self.brewing_ui.handle_event(event)
                continue
            if self.day_over:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    btn = pygame.Rect(SCREEN_W//2-80, (SCREEN_H-240)//2+190, 160, 38)
                    if btn.collidepoint(event.pos):
                        self._play_sfx("click")
                        self.start_new_day()
                continue

            if self.shop_open:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self._shop_close_rect.collidepoint(event.pos):
                        self._play_sfx("click")
                        self.shop_open = False
                        continue
                    for name, rect in self._shop_rects.items():
                        if rect.collidepoint(event.pos):
                            self._shop_buy(name)
                            break
                continue

            if self.recipe_book_open:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    close_r = getattr(self, "_recipe_book_close_rect", None)
                    if close_r and close_r.collidepoint(event.pos):
                        self._play_sfx("click")
                        self.recipe_book_open = False
                continue

            click_handled = False

            for btn in self.menu_buttons:
                if not click_handled and btn.handle_event(event):
                    self._brew_drink(btn.tag)
                    click_handled = True
                    break

            if not click_handled:
                for btn in self.bot_buttons:
                    if btn.handle_event(event):
                        self._bot_action(btn.tag)
                        click_handled = True
                        break

            if not click_handled and self.settings_btn.handle_event(event):
                self.settings_open = not self.settings_open
                self._play_sfx("click")

        return True

    def _brew_drink(self, drink_name):
        if self._serve_cooldown > 0:
            return
        # Open brewing mini-game instead of instant serve
        front_customer = next((c for c in self.customers if c.slot == 0 and not c.seated), None)
        if not front_customer:
            self._play_sfx("fail")
            self.notify(f"No {drink_name} orders right now!", C_RED)
            return
        if front_customer.walking or front_customer.leaving or front_customer.arrived_timer < 0.4:
            if any(o.drink == drink_name for o in self.orders):
                self.notify("Customer still on their way!", C_GOLD)
            else:
                self._play_sfx("fail")
                self.notify(f"No {drink_name} orders right now!", C_RED)
            return
        front_order = next((o for o in self.orders if o.id == front_customer.order_id), None)
        if front_order and front_order.drink == drink_name:
            # Open brewing mini-game
            self._pending_brew_drink = (drink_name, front_order.id)
            self.brewing_ui.open(drink_name)
            return
        if front_order:
            self._play_sfx("fail")
            self.notify(f"Front customer wants {front_order.drink}!", C_RED)
        else:
            self._play_sfx("fail")
            self.notify(f"No {drink_name} orders right now!", C_RED)

    def _bot_action(self, tag):
        if tag == "nextday":
            self._play_sfx("click")
            self.end_day()
        elif tag == "upgrade":
            cost = 60
            if self.coins >= cost:
                self.coins -= cost
                self.max_orders     = min(8, self.max_orders + 1)
                self.spawn_interval = max(2.5, self.spawn_interval - 0.5)
                self._play_sfx("serve")
                self.notify(f"Upgraded! Max orders: {self.max_orders}", C_GREEN)
            else:
                self._play_sfx("fail")
                self.notify(f"Need {cost} coins to upgrade!", C_RED)
        elif tag == "shop":
            self._play_sfx("click")
            self.shop_open = not self.shop_open
        elif tag == "recipes":
            self._play_sfx("click")
            self.recipe_book_open = not getattr(self, "recipe_book_open", False)

    def run(self):
        running = True
        while running:
            dt      = self.clock.tick(FPS) / 1000.0
            running = self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()