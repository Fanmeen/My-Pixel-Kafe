# wag 

import math
import pygame

# ── Palette re-used from constants (safe to import directly) ──────────────────
C_DARK   = (20,  12,   4)
C_GOLD   = (255, 224, 102)
C_CREAM  = (245, 230, 200)
C_GREEN  = (46,  204,  64)
C_RED    = (231,  76,  60)
C_BORDER = (139, 105,  20)
C_PANEL  = (45,   31,  10)
C_BROWN  = (59,   37,  16)
C_GRAY   = (120, 100,  70)
C_WHITE  = (255, 255, 255)

# ── Recipes ───────────────────────────────────────────────────────────────────
# Each ingredient: (label, colour, icon_char)
RECIPES = {
    "Tea": [
        ("Water",    (80,  160, 220), "💧"),
        ("Tea Leaf", (60,  140,  60), "🍃"),
        ("Honey",    (255, 200,  50), "🍯"),
    ],
    "Espresso": [
        ("Water",   (80,  160, 220), "💧"),
        ("Grounds", (50,   25,   5), "☕"),
    ],
    "Latte": [
        ("Espresso",  (50,  25,   5), "☕"),
        ("Milk",     (240, 230, 210), "🥛"),
    ],
    "Cappuccino": [
        ("Espresso", (50,  25,   5), "☕"),
        ("Milk",    (240, 230, 210), "🥛"),
        ("Foam",    (255, 255, 255), "☁"),
    ],
    "Mocha": [
        ("Espresso", (50,  25,   5), "☕"),
        ("Milk",    (240, 230, 210), "🥛"),
        ("Choco",   (80,  40,   5), "🍫"),
        ("Cream",   (255, 240, 220), "🍦"),
    ],
    "Caramel Latte": [
        ("Espresso", (50,  25,   5), "☕"),
        ("Milk",    (240, 230, 210), "🥛"),
        ("Caramel", (210, 130,  15), "🍮"),
        ("Cream",   (255, 240, 220), "🍦"),
    ],
}

# Colours for the liquid layers inside the cup
LIQUID_COLORS = {
    "Water":    (100, 185, 255),
    "Tea Leaf": (80,  155,  60),
    "Honey":    (245, 190,  40),
    "Grounds":  (70,   35,  10),
    "Espresso": (70,   35,  10),
    "Milk":     (245, 235, 215),
    "Foam":     (250, 248, 245),
    "Choco":    (100,  50,  10),
    "Cream":    (255, 245, 225),
    "Caramel":  (210, 130,  15),
}

# Maps ingredient label → assets key for the 64×64 token sprite
_INGREDIENT_SPRITE = {
    "Water":    "ing_water",
    "Tea Leaf": "ing_tea_leaf",
    "Honey":    "ing_honey",
    "Grounds":  "ing_grounds",
    "Espresso": "ing_espresso_shot",
    "Milk":     "ing_milk",
    "Foam":     "ing_foam",
    "Choco":    "ing_choco",
    "Cream":    "ing_cream",
    "Caramel":  "ing_caramel",
}


class _Ingredient:
    """A draggable ingredient token."""
    R = 32   # radius

    def __init__(self, label, color, icon, home_x, home_y, assets=None):
        self.label  = label
        self.color  = color
        self.icon   = icon
        self.home   = (home_x, home_y)
        self.x      = float(home_x)
        self.y      = float(home_y)
        self.dragging   = False
        self.dropped    = False   # permanently placed in cup
        self.drag_off   = (0, 0)
        self._pulse     = 0.0    # animation timer
        # Optional PNG sprite (64×64 token from assets/)
        self._sprite = None
        if assets:
            key = _INGREDIENT_SPRITE.get(label)
            if key:
                self._sprite = assets.get(key)

    def rect(self):
        return pygame.Rect(int(self.x) - self.R, int(self.y) - self.R,
                           self.R * 2, self.R * 2)

    def start_drag(self, mx, my):
        self.dragging = True
        self.drag_off = (self.x - mx, self.y - my)

    def drag_to(self, mx, my):
        if self.dragging:
            self.x = mx + self.drag_off[0]
            self.y = my + self.drag_off[1]

    def snap_home(self):
        self.x = float(self.home[0])
        self.y = float(self.home[1])
        self.dragging = False

    def update(self, dt):
        self._pulse += dt * 3.0

    def draw(self, surf, fonts, faded=False):
        cx, cy = int(self.x), int(self.y)
        alpha = 90 if faded else 255
        pulse = 1.0 + 0.06 * math.sin(self._pulse) if not faded else 1.0
        r = int(self.R * pulse)

        # Shadow
        shadow = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(shadow, (0, 0, 0, 60), (r + 4, r + 6), r)
        surf.blit(shadow, (cx - r - 4 + 2, cy - r - 4 + 2))

        if self._sprite:
            # ── PNG token sprite path ─────────────────────────────────────────
            size = r * 2
            scaled = pygame.transform.smoothscale(self._sprite, (size, size))
            if faded:
                scaled = scaled.copy()
                scaled.set_alpha(90)
            surf.blit(scaled, (cx - r, cy - r))
            # Label below sprite
            lbl_surf = fonts.tiny.render(self.label, True, C_CREAM)
            surf.blit(lbl_surf, lbl_surf.get_rect(center=(cx, cy + r + 8)))
        else:
            # ── Coloured circle fallback ──────────────────────────────────────
            body = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            col  = (*self.color, alpha)
            pygame.draw.circle(body, col, (r, r), r)
            # Highlight sheen
            pygame.draw.circle(body, (255, 255, 255, 60), (r - r//3, r - r//3), r // 3)
            # Border
            pygame.draw.circle(body, (*C_BORDER, alpha), (r, r), r, 2)
            surf.blit(body, (cx - r, cy - r))

            # Icon / label
            icon_surf = fonts.small.render(self.icon, True, C_DARK)
            surf.blit(icon_surf, icon_surf.get_rect(center=(cx, cy - 4)))
            lbl_surf = fonts.tiny.render(self.label, True, C_CREAM)
            surf.blit(lbl_surf, lbl_surf.get_rect(center=(cx, cy + 14)))


class _Cup:
    """The target cup in the centre of the brewing panel."""

    # ── Cup sprite size ───────────────────────────────────────────────────────
    W, H           = 300, 300    # empty cup display size (px)
    W_DONE, H_DONE = 200, 180   # completed drink display size (px)

    # ── Liquid fill area — tune to match your cup sprite ─────────────────────
    LIQ_X = 58    # px from left edge of cup rect to left wall of liquid
    LIQ_Y = 43    # px from top  of cup rect to top  of liquid
    LIQ_W = 155   # width  of the liquid area (px)
    LIQ_H = 178   # height of the liquid area (px)

    # ── Per-layer sizes (px) — bottom and middle are fully independent ──────────
    LIQ_BOTTOM_H = 60   # height of the bottom layer
    LIQ_BOTTOM_X = 87   # left offset of the bottom layer (matches LIQ_X by default)
    LIQ_BOTTOM_W = 111  # width of the bottom layer

    LIQ_MIDDLE_H = 60   # height of the middle layer(s)
    LIQ_MIDDLE_X = 75   # left offset of the middle layer
    LIQ_MIDDLE_W = 135  # width of the middle layer

    def __init__(self, cx, cy):
        self.cx = cx
        self.cy = cy
        self.layers: list[str] = []   # label of each dropped ingredient
        self._done_alpha = 0          # 0-255 crossfade to completed texture
        self._done_drink = ""         # e.g. "cappuccino" → asset "cappuccino_complete"

    @property
    def rect(self):
        return pygame.Rect(self.cx - self.W // 2, self.cy - self.H // 2,
                           self.W, self.H)

    @property
    def done_rect(self):
        return pygame.Rect(self.cx - self.W_DONE // 2, self.cy - self.H_DONE // 2,
                           self.W_DONE, self.H_DONE)

    def contains(self, ix, iy):
        return self.rect.collidepoint(ix, iy)

    def mark_complete(self, drink_name):
        """Trigger crossfade to the finished-drink texture."""
        self._done_drink = drink_name.lower().replace(" ", "_")
        self._done_alpha = 0

    def update(self, dt):
        """Animate the crossfade."""
        if self._done_drink and self._done_alpha < 255:
            self._done_alpha = min(255, self._done_alpha + int(dt * 500))

    def draw(self, surf, fonts, recipe_len, assets=None, drink_name=""):
        r = self.rect
        n = len(self.layers)
        done = bool(self._done_drink) and self._done_alpha > 0

        if not done:
            # ── Phase 1: empty/filling cup ────────────────────────────────────
            # STEP 1: Draw liquid layers FIRST (underneath the cup outline)
            if n > 0:
                # Inner liquid area — adjust _Cup.LIQ_* constants at the top of _Cup
                inner_x      = r.x + self.LIQ_X
                inner_w      = self.LIQ_W
                inner_top    = r.y + self.LIQ_Y
                inner_bottom = inner_top + self.LIQ_H
                inner_h      = max(1, inner_bottom - inner_top)

                liq_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
                # Build per-layer heights: bottom gets LIQ_BOTTOM_H,
                # middle layers get LIQ_MIDDLE_H, top fills remaining space.
                def _layer_h(idx, total):
                    # Divide inner_h evenly so 4-ingredient drinks (Mocha,
                    # Caramel Latte) never produce a negative top-layer height.
                    if total <= 0:
                        return inner_h
                    base = inner_h // total
                    if idx == total - 1:          # top layer gets the remainder
                        return max(4, inner_h - base * (total - 1))
                    return max(4, base)
                y_cursor = inner_bottom  # start at base, stack upward
                for i, label in enumerate(self.layers):
                    liq_col = LIQUID_COLORS.get(label, (180, 120, 60))
                    lh      = max(4, _layer_h(i, max(n, recipe_len)))
                    y_cursor -= lh
                    ly_local = int(y_cursor - r.y)
                    # Per-layer X/W overrides (local coords inside liq_surf)
                    if i == 0:
                        lx = self.LIQ_BOTTOM_X
                        lw = self.LIQ_BOTTOM_W
                    else:
                        lx = self.LIQ_MIDDLE_X
                        lw = self.LIQ_MIDDLE_W
                    pygame.draw.rect(liq_surf, (*liq_col, 245),
                                     (lx, ly_local, lw, lh + 2))
                # Clip so liquid never bleeds outside the inner area
                clip = pygame.Rect(inner_x - r.x, inner_top - r.y, inner_w, inner_h)
                liq_surf.set_clip(clip)
                surf.blit(liq_surf, r.topleft)
                liq_surf.set_clip(None)

            # STEP 2: Cup outline texture ON TOP — PNG has transparent BG+interior,
            # only the dark-brown border pixels are opaque, so liquid shows through.
            if assets:
                cup_tex = assets.get("brew_cup_empty")
                if cup_tex:
                    scaled = pygame.transform.smoothscale(cup_tex, (r.width, r.height))
                    surf.blit(scaled, r.topleft)
                else:
                    pygame.draw.rect(surf, C_BORDER, r, 3, border_radius=4)
            else:
                pygame.draw.rect(surf, C_BORDER, r, 3, border_radius=4)

            if n == 0:
                hint = fonts.tiny.render("drop here", True, C_GRAY)
                surf.blit(hint, hint.get_rect(center=(self.cx, self.cy)))

        else:
            # ── Phase 2: crossfade to completed drink texture ─────────────────
            # Fade out the empty cup
            if assets and self._done_alpha < 255:
                cup_tex = assets.get("brew_cup_empty")
                if cup_tex:
                    scaled = pygame.transform.smoothscale(cup_tex, (r.width, r.height))
                    scaled = scaled.copy()
                    scaled.set_alpha(255 - self._done_alpha)
                    surf.blit(scaled, r.topleft)

            # Fade in + pop-in scale for the completed drink art
            if assets:
                dr       = self.done_rect
                key      = f"{self._done_drink}_complete"
                done_tex = assets.get(key)
                if done_tex:
                    # ── Convert SRCALPHA → plain surface so set_colorkey and
                    # set_alpha actually work (both are silently ignored on
                    # per-pixel-alpha surfaces produced by convert_alpha()).
                    flat = pygame.Surface(done_tex.get_size())   # no SRCALPHA flag
                    flat.fill((0, 0, 0))
                    flat.blit(done_tex, (0, 0))
                    flat.set_colorkey((0, 0, 0))   # strips the black PNG background
                    # Scale 80% → 100% as alpha goes 0 → 255 (pop-in effect)
                    scale_t = self._done_alpha / 255
                    pop     = 0.80 + 0.20 * scale_t
                    pw      = int(dr.width  * pop)
                    ph      = int(dr.height * pop)
                    # Use integer scale to keep pixel art crisp and avoid AA fringe
                    popped  = pygame.transform.scale(flat, (pw, ph))
                    popped.set_colorkey((0, 0, 0))   # re-apply; scale() doesn't carry it
                    popped.set_alpha(self._done_alpha)
                    surf.blit(popped, (self.cx - pw // 2, self.cy - ph // 2))
                else:
                    # Fallback golden glow if asset is missing
                    glow = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
                    pygame.draw.rect(glow, (*C_GOLD, self._done_alpha),
                                     (0, 0, r.width, r.height), border_radius=8)
                    surf.blit(glow, r.topleft)

        # Ingredient count badge (shift down a bit when done art is larger)
        badge_y = r.bottom + (32 if done else 14)
        badge   = fonts.small.render(f"{n}/{recipe_len}", True, C_WHITE)
        surf.blit(badge, badge.get_rect(center=(self.cx, badge_y)))


class BrewingUI:
    """Full brewing mini-game overlay."""

    # ── Panel size ────────────────────────────────────────────────────────────
    W, H   = 680, 420
    ANIM_T = 0.18   # seconds to open/close

    # ── COMPLETE button size & position ───────────────────────────────────────
    BTN_W        = 200   # button width  (px)
    BTN_H        = 48    # button height (px)
    BTN_Y_OFFSET = 54    # px down from the top of the panel

    # ── Cup vertical position (relative to screen centre) ────────────────────
    CUP_Y_OFFSET = -10   # negative = above centre, positive = below centre

    # ── Title bar ─────────────────────────────────────────────────────────────
    TITLE_H      = 44    # height of the top title bar (px)

    def __init__(self, assets, fonts):
        self.assets      = assets
        self.fonts       = fonts
        self.active      = False
        self.drink_name  = ""
        self._ingredients: list[_Ingredient] = []
        self._cup        = None
        self._recipe     = []
        self._complete   = False
        self._cancel     = False
        self._open_t     = 0.0     # 0..ANIM_T open animation
        self._closing    = False
        self._close_cb   = None    # called with (success) when animation ends
        self._dragged    = None    # currently dragged ingredient
        self._wobble     = {}      # label -> wobble_timer for drop effect
        self._confetti   = []      # list of (x,y,vx,vy,col,life)
        self._completed_flash = 0.0
        # Completion signalling (polled by game.py each frame via poll())
        self._result_pending = False
        self._result_success = False
        self.wrong_recipe    = False  # True when player pressed COMPLETE too early
        # Initialise rects so handle_event never crashes before first draw()
        self._close_btn_rect    = pygame.Rect(0, 0, 0, 0)
        self._complete_btn_rect = pygame.Rect(0, 0, 0, 0)

    # ── Public API ─────────────────────────────────────────────────────────────
    def poll(self):
        """Call every frame from game.update().  Returns (done, success) exactly
        once when the close animation finishes, then resets to (False, False)."""
        if self._result_pending:
            self._result_pending = False
            return True, self._result_success
        return False, False

    def open(self, drink_name):
        self.drink_name = drink_name
        self._recipe    = RECIPES.get(drink_name, [])
        self.active     = True
        self._complete  = False
        self._cancel    = False
        self._closing   = False
        self._open_t    = 0.0
        self._dragged        = None
        self._confetti.clear()
        self._completed_flash = 0.0
        self._result_pending  = False
        self._result_success  = False
        self.wrong_recipe     = False
        self._build_layout()

    def handle_event(self, event):
        """Handle input events.  Completion is signalled via poll(), not here."""
        if not self.active or self._closing:
            return False, False

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._start_close(success=False)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Cancel X button
            if self._close_btn_rect.collidepoint(mx, my):
                self._start_close(success=False)
                return False, False
            # Complete button — ALWAYS clickable so players can rush and be penalised
            if self._complete_btn_rect.collidepoint(mx, my):
                if self._ready():
                    # Correct brew ✔
                    self._spawn_confetti()
                    self._completed_flash = 0.6
                    self._start_close(success=True)
                else:
                    # Incomplete recipe — penalise player
                    self.wrong_recipe = True
                    self._start_close(success=False)
                return False, False
            # Ingredient pick-up
            for ing in self._ingredients:
                if not ing.dropped and ing.rect().collidepoint(mx, my):
                    ing.start_drag(mx, my)
                    self._dragged = ing
                    break

        if event.type == pygame.MOUSEMOTION and self._dragged:
            self._dragged.drag_to(*event.pos)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragged:
                ing = self._dragged
                self._dragged = None
                # Check if dropped inside cup
                if self._cup and self._cup.contains(ing.x, ing.y):
                    if ing.label not in [i.label for i in self._ingredients if i.dropped]:
                        ing.dropped = True
                        ing.x = ing.home[0]
                        ing.y = ing.home[1]
                        self._cup.layers.append(ing.label)
                        self._wobble[ing.label] = 0.3
                        # Trigger completed texture crossfade when last ingredient added
                        if all(i.dropped for i in self._ingredients):
                            self._cup.mark_complete(self.drink_name)
                else:
                    ing.snap_home()

        return False, False

    def update(self, dt):
        if not self.active:
            return
        # Open animation
        if not self._closing:
            self._open_t = min(self.ANIM_T, self._open_t + dt)
        else:
            self._open_t = max(0.0, self._open_t - dt)
            if self._open_t <= 0:
                self.active          = False
                self._result_pending = True        # game.py picks this up via poll()
                self._result_success = self._complete

        self._cup.update(dt)
        for ing in self._ingredients:
            ing.update(dt)
        for k in list(self._wobble):
            self._wobble[k] -= dt
            if self._wobble[k] <= 0:
                del self._wobble[k]
        # Confetti
        for p in self._confetti:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 400 * dt   # gravity
            p[5] -= dt
        self._confetti = [p for p in self._confetti if p[5] > 0]
        if self._completed_flash > 0:
            self._completed_flash -= dt

    def draw(self, surf):
        if not self.active:
            return
        t = self._open_t / self.ANIM_T
        t = t * t * (3 - 2 * t)   # smoothstep

        sw, sh = surf.get_size()
        cx, cy = sw // 2, sh // 2

        # Dim overlay
        dim = pygame.Surface((sw, sh), pygame.SRCALPHA)
        dim.fill((0, 0, 0, int(160 * t)))
        surf.blit(dim, (0, 0))

        pw, ph = int(self.W * t), int(self.H * t)
        if pw < 16 or ph < 16:
            return

        px, py = cx - pw // 2, cy - ph // 2

        # ── Clipboard panel (fully opaque — no see-through) ──────────────────
        # Colours
        BOARD_COL   = (118,  72,  28)   # dark wood backing (fallback)
        PAPER_COL   = (240, 224, 185)   # warm parchment
        RULE_COL    = (210, 192, 150)   # faint ruled lines
        MARGIN_COL  = (210, 120, 110)   # red margin line
        CLIP_COL    = ( 72,  68,  62)   # metal clip body
        CLIP_SHINE  = (155, 148, 138)   # metal highlight

        # Solid board surface (NO SRCALPHA → 100 % opaque)
        panel = pygame.Surface((pw, ph))
        # Use the brewing_bg wood texture as the full background
        _brew_bg = self.assets.get("brewing_bg") if self.assets else None
        if _brew_bg:
            _scaled_bg = pygame.transform.smoothscale(_brew_bg, (pw, ph))
            panel.blit(_scaled_bg, (0, 0))
        else:
            panel.fill(BOARD_COL)

        # Subtle dark vignette overlay so edges look framed
        vign = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(vign, (0, 0, 0, 0), (0, 0, pw, ph))
        for edge_w in range(18, 0, -2):
            a = int(80 * (1 - edge_w / 18))
            pygame.draw.rect(vign, (0, 0, 0, a), (edge_w, edge_w, pw - edge_w*2, ph - edge_w*2), 1)
        panel.blit(vign, (0, 0))

        # Clipboard metal clip — centred at the top
        clip_w, clip_h = 88, 24
        clip_x = (pw - clip_w) // 2
        pygame.draw.rect(panel, CLIP_COL,   (clip_x,     0,       clip_w,     clip_h),     border_radius=5)
        pygame.draw.rect(panel, CLIP_SHINE, (clip_x + 5, 3,       clip_w - 10, clip_h - 9), border_radius=3)
        # Clip hole
        hole_w = 24
        pygame.draw.rect(panel, (45, 42, 38),
                         (clip_x + (clip_w - hole_w) // 2, 5, hole_w, clip_h - 8),
                         border_radius=3)

        # Outer border
        pygame.draw.rect(panel, (60, 30, 8), (0, 0, pw, ph), 4, border_radius=10)

        surf.blit(panel, (px, py))

        # ── Title — drawn directly on wood texture ────────────────────────────
        title_h = self.TITLE_H
        # Semi-transparent dark strip behind title text for readability
        title_bg = pygame.Surface((pw - 12, title_h), pygame.SRCALPHA)
        pygame.draw.rect(title_bg, (0, 0, 0, 100), (0, 0, pw - 12, title_h), border_radius=6)
        surf.blit(title_bg, (px + 6, py + 26))
        tb_rect = pygame.Rect(px + 6, py + 26, pw - 12, title_h)
        drink_icon = self.assets.get(self.drink_name.lower().replace(" ", "_"))
        icon_x = tb_rect.x + 10
        if drink_icon:
            icon_s = pygame.transform.scale(drink_icon, (28, 28))
            surf.blit(icon_s, (icon_x, tb_rect.y + (title_h - 28) // 2))
            icon_x += 36
        title_txt = self.fonts.large.render(f"Brew  {self.drink_name}", True, C_GOLD)
        surf.blit(title_txt, (icon_x, tb_rect.y + (title_h - title_txt.get_height()) // 2))

        # ── X close button — big, red, top-right corner ───────────────────────
        xbw, xbh = 36, 36
        self._close_btn_rect = pygame.Rect(
            cx + self.W // 2 - xbw - 6, cy - self.H // 2 + 6, xbw, xbh)
        mx_now, my_now = pygame.mouse.get_pos()
        x_hovered = self._close_btn_rect.collidepoint(mx_now, my_now)
        x_bg_col  = (220, 50, 30) if x_hovered else (170, 35, 20)
        pygame.draw.rect(surf, x_bg_col,     self._close_btn_rect, border_radius=8)
        pygame.draw.rect(surf, (255, 100, 80), self._close_btn_rect, 2, border_radius=8)
        x_txt = self.fonts.large.render("X", True, C_WHITE)
        surf.blit(x_txt, x_txt.get_rect(center=self._close_btn_rect.center))

        if t < 0.5:
            return   # don't draw internals until panel is mostly open

        # ── Cup ───────────────────────────────────────────────────────────────
        self._cup.cx = cx
        self._cup.cy = cy + self.CUP_Y_OFFSET
        self._cup.draw(surf, self.fonts, len(self._recipe), self.assets, self.drink_name)

        # ── Ingredient shelf ──────────────────────────────────────────────────
        shelf_y = cy + self.H // 2 - 68
        shelf_rect = pygame.Rect(px + 16, shelf_y - 8, pw - 32, 56)
        shelf_bg = self.assets.get("brewing_shelf")
        if shelf_bg:
            scaled_shelf = pygame.transform.smoothscale(shelf_bg, (shelf_rect.width, shelf_rect.height))
            surf.blit(scaled_shelf, shelf_rect.topleft)
            pygame.draw.rect(surf, C_BORDER, shelf_rect, 2, border_radius=8)
        else:
            pygame.draw.rect(surf, (160, 100, 40), shelf_rect, border_radius=8)
            pygame.draw.rect(surf, C_BORDER, shelf_rect, 2, border_radius=8)
        shelf_lbl = self.fonts.tiny.render("── Drag ingredients into the cup ──",
                                            True, C_CREAM)
        surf.blit(shelf_lbl, shelf_lbl.get_rect(
            center=(cx, shelf_y - 20)))

        for ing in self._ingredients:
            # Reposition home to actual screen coords each frame
            idx = [i.label for i in self._ingredients].index(ing.label)
            n   = len(self._ingredients)
            spacing = min(100, (pw - 60) // max(n, 1))
            hx  = px + 30 + spacing // 2 + idx * spacing
            hy  = shelf_y + 20
            if not ing.dragging:
                ing.home = (hx, hy)
                if not ing.dropped:
                    ing.x = float(hx)
                    ing.y = float(hy)
            ing.draw(surf, self.fonts, faded=ing.dropped)

        # ── COMPLETE button — adjust BTN_W / BTN_H / BTN_Y_OFFSET at top of class ─
        ready = self._ready()
        cbw, cbh = self.BTN_W, self.BTN_H
        cbx = cx - cbw // 2
        cby = cy - self.H // 2 + self.BTN_Y_OFFSET
        self._complete_btn_rect = pygame.Rect(cbx, cby, cbw, cbh)

        if ready:
            pulse  = 1.0 + 0.05 * math.sin(pygame.time.get_ticks() / 200)
            bw2    = int(cbw * pulse)
            bh2    = int(cbh * pulse)
            btn_r  = pygame.Rect(cx - bw2 // 2, cby - (bh2 - cbh) // 2, bw2, bh2)
            flash  = self._completed_flash > 0
            bcol   = (255, 255, 180) if flash else (20, 160, 50)
            bglow  = pygame.Surface((bw2 + 20, bh2 + 20), pygame.SRCALPHA)
            pygame.draw.rect(bglow, (*bcol, 80),
                             (0, 0, bw2 + 20, bh2 + 20), border_radius=12)
            surf.blit(bglow, (btn_r.x - 10, btn_r.y - 10))
            pygame.draw.rect(surf, bcol, btn_r, border_radius=10)
            pygame.draw.rect(surf, C_GOLD, btn_r, 3, border_radius=10)
            btn_txt = self.fonts.large.render("COMPLETE", True, C_DARK)
        else:
            # Incomplete — orange with warning so player knows this will cost rep
            btn_r  = self._complete_btn_rect
            pygame.draw.rect(surf, (120, 60, 10), btn_r, border_radius=10)
            pygame.draw.rect(surf, (220, 110, 20), btn_r, 2, border_radius=10)
            btn_txt = self.fonts.large.render("COMPLETE", True, (255, 180, 60))

        surf.blit(btn_txt, btn_txt.get_rect(center=btn_r.center))

        # Remaining ingredient hint below complete button
        missing = [ing.label for ing in self._ingredients if not ing.dropped]
        if missing:
            hint = self.fonts.tiny.render(
                "Missing: " + ", ".join(missing) + "   -2 rep if incomplete!", True, (255, 160, 80))
            surf.blit(hint, hint.get_rect(center=(cx, cby + cbh + 14)))

        # ── Confetti ──────────────────────────────────────────────────────────
        for p in self._confetti:
            alpha = int(255 * min(1.0, p[5] / 0.5))
            col   = (*p[4], alpha)
            cs    = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.rect(cs, col, (0, 0, 8, 8))
            surf.blit(cs, (int(p[0]), int(p[1])))

    # ── Internals ──────────────────────────────────────────────────────────────
    def _build_layout(self):
        sw, sh = pygame.display.get_surface().get_size()
        cx, cy = sw // 2, sh // 2
        self._cup = _Cup(cx, cy - 10)
        self._ingredients = []
        n = len(self._recipe)
        for idx, (label, color, icon) in enumerate(self._recipe):
            spacing = min(100, (self.W - 60) // max(n, 1))
            hx = cx - (n - 1) * spacing // 2 + idx * spacing
            hy = cy + self.H // 2 - 48
            self._ingredients.append(
                _Ingredient(label, color, icon, hx, hy, assets=self.assets)
            )

    def _ready(self):
        return all(ing.dropped for ing in self._ingredients)

    def _start_close(self, success):
        self._complete = success
        self._closing  = True

    def _spawn_confetti(self):
        import random
        sw, sh = pygame.display.get_surface().get_size()
        cx, cy = sw // 2, sh // 2
        colors  = [C_GOLD, C_GREEN, (255, 100, 100), (100, 200, 255), C_CREAM]
        for _ in range(60):
            self._confetti.append([
                cx + random.randint(-100, 100),
                cy,
                random.uniform(-200, 200),
                random.uniform(-400, -100),
                random.choice(colors),
                random.uniform(0.6, 1.2),
            ])