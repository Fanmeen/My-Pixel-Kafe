import math
import random
import pygame

from constants import (
    SCREEN_W, ORDER_TIME_BASE, WALK_SPEED,
    CUSTOMER_COLORS, SKIN_TONES, C_DARK,
)

# ── Order ──────────────────────────────────────────────────────────────────────
class Order:
    def __init__(self, oid, drink, time_limit=ORDER_TIME_BASE):
        self.id         = oid
        self.drink      = drink
        self.time_limit = time_limit + random.uniform(-3, 5)
        self.elapsed    = 0.0

    @property
    def time_left(self):
        return max(0.0, self.time_limit - self.elapsed)

    @property
    def urgency(self):
        return self.elapsed / self.time_limit

    @property
    def expired(self):
        return self.elapsed >= self.time_limit

# ── Customer ───────────────────────────────────────────────────────────────────
class Customer:
    COUNTER_FRONT_Y = 340
    BARISTA_X       = SCREEN_W // 3 - 45
    SLOT_SPACING    = 52
    QUEUE_START_X   = BARISTA_X + 190
    ENTRANCE_X      = 107

    @classmethod
    def slot_x(cls, slot):
        return cls.QUEUE_START_X + slot * cls.SLOT_SPACING

    def __init__(self, cid, drink, slot, assets, order_id=None):
        self.id         = cid
        self.order_id   = order_id   # tied 1-to-1 with their specific Order
        self.drink      = drink
        self.slot       = slot
        self.color      = random.choice(CUSTOMER_COLORS)
        self.skin       = random.choice(SKIN_TONES)
        self.sprite_variant = random.randint(1, 3)
        self.assets     = assets

        self.x = float(self.ENTRANCE_X)
        self.y = float(self.COUNTER_FRONT_Y)
        self.target_x = float(self.slot_x(slot))

        self.walking      = True
        self.leaving      = False
        self.gone         = False
        self.served       = False
        self.seated       = False
        self.sit_side     = None   # "left" | "right" when seated at a table
        self.walk_anim    = 0.0
        self.walk_frame   = 0
        self.arrived_timer = 0.0

    @property
    def sprite_key(self):
        v = self.sprite_variant
        if self.seated and self.sit_side:
            return f"customer_sit_{self.sit_side}_{v}"
        if self.walking:
            if self.leaving or self.target_x < self.x:
                return f"customer_left_{v}"
            return f"customer_right_{v}"
        return f"customer_{v}"

    def update_slot(self, new_slot):
        """Forces the customer to move to a new position in the queue."""
        self.slot = new_slot
        self.target_x = float(self.slot_x(new_slot))
        # If they aren't at the new target, start walking and reset the
        # arrived_timer so the bubble only appears after they fully settle.
        if abs(self.x - self.target_x) > 2:
            self.walking = True
            self.arrived_timer = 0.0

    def update(self, dt):
        if not self.walking:
            if not self.leaving:
                self.arrived_timer += dt
            return

        target_y = getattr(self, 'target_y', self.y)
        dx   = self.target_x - self.x
        dy   = target_y - self.y
        dist = math.hypot(dx, dy)
        move = WALK_SPEED * dt

        if dist <= move or dist == 0:
            self.x       = self.target_x
            self.y       = target_y
            self.walking = False
            if self.leaving:
                self.gone = True
        else:
            ratio = move / dist
            self.x += dx * ratio
            self.y += dy * ratio

        self.walk_anim  += dt * 8.0
        self.walk_frame  = int(self.walk_anim) % 4

    def draw(self, surf, fonts, is_first=False):
        ix, iy = int(self.x), int(self.y)
        sprite = self.assets.get(self.sprite_key)
        if sprite:
            surf.blit(sprite, (ix - 36, iy - 100))
        else:
            self._draw_placeholder(surf, ix, iy)

        # Show an order bubble above every customer who has fully arrived and
        # is waiting to be served.  This keeps the speech bubbles consistent
        # with the order tickets shown in the bottom panel (one bubble per
        # visible ticket, no matter which queue position the customer is in).
        if not self.walking and not self.leaving and self.arrived_timer >= 0.4:
            bw, bh = 96, 36
            bx, by = ix - bw // 2, iy - 110
            bubble_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            bubble_surf.fill((255, 255, 255, 230))
            pygame.draw.rect(bubble_surf, C_DARK, (0, 0, bw, bh), 2, border_radius=7)
            pygame.draw.polygon(bubble_surf, (255, 255, 255, 230),
                                [(bw//2 - 6, bh), (bw//2 + 6, bh), (bw//2, bh + 10)])
            surf.blit(bubble_surf, (bx, by))

            icon = self.assets.get(self.drink.lower().replace(" ", "_"))
            if icon:
                small_icon = pygame.transform.scale(icon, (18, 18))
                surf.blit(small_icon, (bx + 5, by + 9))
            text = fonts.tiny.render(self.drink[:10], False, C_DARK)
            surf.blit(text, (bx + (26 if icon else 8), by + 12))

    def _draw_placeholder(self, surf, x, y):
        bob = int(math.sin(self.walk_anim * math.pi) * 2) if self.walking else 0
        pygame.draw.rect(surf, self.color, (x - 10, y - 36 + bob, 20, 20), border_radius=2)
        pygame.draw.rect(surf, self.skin, (x - 8, y - 54 + bob, 16, 16), border_radius=2)