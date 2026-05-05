import pygame

from constants import (
    C_PANEL, C_BORDER, C_CREAM, C_BROWN, C_GOLD, C_GREEN,
    C_RED, C_DARK, C_GRAY,
)


# ── Drawing Helpers ────────────────────────────────────────────────────────────
def draw_pixel_rect(surf, color, rect, border_color=None, border=3, radius=4):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border_color:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)


def draw_text(surf, fonts, text, pos, color=C_CREAM, font="small", anchor="topleft"):
    f = getattr(fonts, font)
    rendered = f.render(text, True, color)   # True = antialiased for crisp font rendering
    r = rendered.get_rect(**{anchor: pos})
    surf.blit(rendered, r)
    return r


def draw_bar(surf, rect, value, max_value,
             fg_color=C_GREEN, bg_color=C_DARK, border_color=C_BORDER):
    pygame.draw.rect(surf, bg_color,     rect, border_radius=3)
    pygame.draw.rect(surf, border_color, rect, 2, border_radius=3)
    if max_value > 0:
        fill_w = int(rect.width * min(1.0, value / max_value))
        if fill_w > 4:
            fill_rect = pygame.Rect(rect.x + 2, rect.y + 2,
                                    fill_w - 4, rect.height - 4)
            pygame.draw.rect(surf, fg_color, fill_rect, border_radius=2)


# ── Button ─────────────────────────────────────────────────────────────────────
class Button:
    def __init__(self, rect, label, color=(0,0,0,0), hover_color=(255,220,100,40),
                 border_color=(0,0,0,0), text_color=C_CREAM, icon=None, tag=None):
        self.rect         = pygame.Rect(rect)
        self.label        = label
        self.color        = color
        self.hover_color  = hover_color
        self.border_color = border_color
        self.text_color   = text_color
        self.icon         = icon
        self.tag          = tag
        self.hovered      = False
        self.pressed_timer = 0.0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed_timer = 0.1
                return True
        return False

    def update(self, dt):
        self.hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        if self.pressed_timer > 0:
            self.pressed_timer -= dt

    def draw(self, surf, fonts):
        color = self.hover_color if self.hovered else self.color
        r = self.rect.inflate(-4, -4) if self.pressed_timer > 0 else self.rect

        # Only draw fill/border if not fully transparent
        if len(color) == 3 or color[3] > 0:
            if len(color) == 4 and color[3] < 255:
                s = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
                pygame.draw.rect(s, color, (0, 0, r.width, r.height), border_radius=4)
                surf.blit(s, r.topleft)
            else:
                pygame.draw.rect(surf, color, r, border_radius=4)

        bc = self.border_color
        if bc and (len(bc) == 3 or bc[3] > 0):
            pygame.draw.rect(surf, bc, r, 2, border_radius=4)

        tx = r.x + 8
        if self.icon:
            icon_small = pygame.transform.scale(self.icon, (16, 16))
            surf.blit(icon_small, (tx, r.centery - 8))
            tx += 22
        text = fonts.small.render(self.label, True, self.text_color)
        surf.blit(text, text.get_rect(midleft=(tx, r.centery)))


# ── OrderTicket ────────────────────────────────────────────────────────────────
class OrderTicket:
    H = 88
    W = 192

    def __init__(self, order, x, y, assets, fonts):
        self.order  = order
        self.rect   = pygame.Rect(x, y, self.W, self.H)
        self.assets = assets
        self.fonts  = fonts

    def update(self, dt):
        pass   # display-only

    def handle_event(self, event):
        return False

    def draw(self, surf):
        o = self.order
        urg = o.urgency
        border_col = (
            C_RED   if urg > 0.7 else
            C_GOLD  if urg > 0.4 else
            C_BORDER
        )
        draw_pixel_rect(surf, C_DARK, self.rect, border_col, border=2, radius=6)

        # Icon
        icon = self.assets.get(o.drink.lower().replace(" ", "_"))
        if icon:
            big_icon = pygame.transform.scale(icon, (32, 32))
            surf.blit(big_icon, (self.rect.x + 6, self.rect.y + 8))

        # Drink name — sits next to icon
        ix = self.rect.x + (44 if icon else 8)
        name_surf = self.fonts.small.render(o.drink, True, C_GOLD)
        surf.blit(name_surf, (ix, self.rect.y + 12))

        # Timer bar
        bar_rect = pygame.Rect(self.rect.x + 6, self.rect.y + 56,
                               self.rect.width - 12, 10)
        timer_col = C_RED if urg > 0.6 else C_GREEN
        draw_bar(surf, bar_rect, o.time_left, o.time_limit, fg_color=timer_col)

        # Timer text — below bar, small font so it never overlaps
        tl_text = self.fonts.tiny.render(f"{o.time_left:.0f}s", True, C_CREAM)
        surf.blit(tl_text, (self.rect.x + 6, self.rect.y + 70))