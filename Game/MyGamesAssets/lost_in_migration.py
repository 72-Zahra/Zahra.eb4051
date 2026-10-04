
import math
import os
import random
import sys

import pygame

# (تنظیمات)
W, H = 1024, 768           # مثل بازی اصلی
FPS = 60
GAME_SECONDS = 60          # طول هر دور
POINTS_PER_CORRECT = 50    # امتیاز هر جواب درست (ضربدر ضریب)
DOTS_PER_LEVEL = 4         # چند جواب درست پشت‌سرهم تا ضریب بالا بره
MAX_MULT = 5
LOCKOUT_TIME = 0.10        # مکث خیلی کوتاه بعد از هر جواب (جلوگیری از دوبار زدن اتفاقی)
INCONGRUENT_CHANCE = 0.5   # احتمال اینکه بقیه‌ی پرنده‌ها جهت متفاوت داشته باشن

# اگه می‌خوای از بک‌گراند استخراج‌شده استفاده بشه (کنار این فایل: output/images/...)
USE_EXTRACTED_BACKGROUND = True
EXTRACTED_BG = "background_232.png"

DIR_NAMES = ["right", "down", "left", "up"]
DIR_ANGLE = {"right": 0, "down": 90, "left": 180, "up": 270}
KEYMAP = {
    pygame.K_RIGHT: "right", pygame.K_DOWN: "down",
    pygame.K_LEFT: "left", pygame.K_UP: "up",
    pygame.K_d: "right", pygame.K_s: "down",
    pygame.K_a: "left", pygame.K_w: "up",
}

# چیدمان ^ : پرنده‌ی اول (نوک) همون پرنده‌ی وسطه. فاصله‌ها از روی عکس‌ها.
FLOCK_OFFSETS = [(0, 0), (-52, 53), (52, 53), (-105, 106), (105, 106)]
FLOCK_ORIGIN = (0.66, 0.49)       # جای نوک مثلث نسبت به عرض و ارتفاع قاب

# ستون فلش‌های سمت چپ (نتیجه‌ی دور قبل)
COLUMN_X = 0.23
COLUMN_Y0, COLUMN_DY = 0.23, 0.105

INK = (14, 18, 30)
NAVY = (16, 30, 64)
TEXT = (22, 38, 72)
ARROW_BLUE = (64, 108, 170)
WHITE = (255, 255, 255)
GREEN = (86, 170, 80)
RED = (205, 70, 70)


#ابزارهای رسم 
def rotate(points, angle_deg):
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    return [(x * c - y * s, x * s + y * c) for x, y in points]


BODY = [(16, 0), (4, -3), (-12, -2.5), (-14, 0), (-12, 2.5), (4, 3)]
WING_TOP = [(6, -2), (-6, -14), (-11, -14), (-4, -2)]
WING_BOTTOM = [(x, -y) for x, y in WING_TOP]


def draw_bird(surf, pos, direction, scale=2.0, color=INK):
    ang = DIR_ANGLE[direction]
    for poly in (BODY, WING_TOP, WING_BOTTOM):
        pts = rotate(poly, ang)
        pts = [(pos[0] + x * scale, pos[1] + y * scale) for x, y in pts]
        pygame.draw.polygon(surf, color, pts)


def make_background():
    bg = None
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "output", "images", EXTRACTED_BG)
    if USE_EXTRACTED_BACKGROUND and os.path.exists(path):
        try:
            img = pygame.image.load(path).convert()
            bg = pygame.transform.smoothscale(img, (W, H))
        except Exception:
            bg = None
    if bg is None:
        bg = pygame.Surface((W, H))
        top, bottom = (64, 152, 214), (180, 226, 246)
        for y in range(H):
            t = y / (H - 1)
            col = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
            pygame.draw.line(bg, col, (0, y), (W, y))
    # خورشید کم‌رنگ بالای پرنده‌ها
    sun = pygame.Surface((120, 120), pygame.SRCALPHA)
    pygame.draw.circle(sun, (255, 255, 255, 110), (60, 60), 39)
    bg.blit(sun, (int(W * 0.64) - 60, int(H * FLOCK_ORIGIN[1]) - 72 - 60))
    return bg


def make_cloud():
    """ابر با کف صاف، مثل عکس‌ها"""
    w, h, base = 170, 70, 52
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for cx, cy, r in [(40, 42, 22), (72, 32, 30), (108, 40, 24), (134, 46, 17), (84, 44, 20)]:
        pygame.draw.circle(s, (255, 255, 255, 95), (cx, cy), r)
    s.fill((0, 0, 0, 0), pygame.Rect(0, base, w, h - base))
    return s


def fmt_time(t):
    t = max(0, math.ceil(t))
    return f"{t // 60}:{t % 60:02d}"


# بازی 
class Game:
    def __init__(self, screen):
        self.screen = screen
        self.bg = make_background()
        self.cloud = make_cloud()
        self.clouds = [[random.uniform(0, W), random.uniform(H * 0.12, H * 0.85),
                        random.uniform(0.8, 1.5), random.uniform(5, 16)] for _ in range(7)]
        names = "arial,helvetica,dejavusans"
        self.font_s = pygame.font.SysFont(names, 16, bold=True)
        self.font_m = pygame.font.SysFont(names, 26, bold=True)
        self.font_l = pygame.font.SysFont(names, 56, bold=True)
        self.pause_rect = pygame.Rect(0, 0, 66, 66)
        self.t = 0.0
        self.state = "title"   # title / playing / paused / over
        self.reset()

    def reset(self):
        self.time_left = float(GAME_SECONDS)
        self.score = 0
        self.dots = 0
        self.mult = 1
        self.correct = 0
        self.total = 0
        self.rts = []
        self.lockout = 0.0
        self.trial_time = 0.0
        self.center_dir = "up"
        self.flank_dir = "up"
        self.prev = None        # (جهت وسط، جهت بقیه، درست؟) دور قبل
        self.prev_timer = 0.0

    #منطق 
    def start(self):
        self.reset()
        self.state = "playing"
        self.new_trial()

    def new_trial(self):
        self.center_dir = random.choice(DIR_NAMES)
        if random.random() < INCONGRUENT_CHANCE:
            self.flank_dir = random.choice([d for d in DIR_NAMES if d != self.center_dir])
        else:
            self.flank_dir = self.center_dir
        self.trial_time = 0.0

    def answer(self, d):
        if self.state != "playing" or self.lockout > 0:
            return
        ok = (d == self.center_dir)
        self.total += 1
        if ok:
            self.correct += 1
            self.rts.append(self.trial_time)
            self.score += POINTS_PER_CORRECT * self.mult
            self.dots += 1
            if self.dots >= DOTS_PER_LEVEL:
                self.dots = 0
                self.mult = min(MAX_MULT, self.mult + 1)
        else:
            self.dots = 0
            self.mult = 1
        # نتیجه‌ی این دور می‌ره توی ستون سمت چپ و دور بعد فوراً شروع می‌شه
        self.prev = (self.center_dir, self.flank_dir, ok)
        self.prev_timer = 1.0
        self.new_trial()
        self.lockout = LOCKOUT_TIME

    def toggle_pause(self):
        if self.state == "playing":
            self.state = "paused"
        elif self.state == "paused":
            self.state = "playing"

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if self.state in ("title", "over"):
                if e.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.start()
            elif e.key in (pygame.K_p, pygame.K_ESCAPE):
                self.toggle_pause()
            elif e.key in KEYMAP:
                self.answer(KEYMAP[e.key])
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.state in ("playing", "paused") and self.pause_rect.collidepoint(e.pos):
                self.toggle_pause()

    def update(self, dt):
        self.t += dt
        for c in self.clouds:
            c[0] += c[3] * dt
            if c[0] > W + 20:
                c[0] = -180 * c[2]
        if self.state != "playing":
            return
        self.time_left -= dt
        self.trial_time += dt
        if self.lockout > 0:
            self.lockout -= dt
        if self.prev_timer > 0:
            self.prev_timer = max(0.0, self.prev_timer - dt)
        if self.time_left <= 0:
            self.time_left = 0
            self.state = "over"

    # --- رسم ---
    def draw_flock(self):
        ox = W * FLOCK_ORIGIN[0]
        oy = H * FLOCK_ORIGIN[1] + math.sin(self.t * 2.0) * 3
        for i, (dx, dy) in enumerate(FLOCK_OFFSETS):
            d = self.center_dir if i == 0 else self.flank_dir
            draw_bird(self.screen, (ox + dx, oy + dy), d)

    def draw_prev_column(self):
        """ستون ۵ فلش آبی سمت چپ: نتیجه‌ی دور قبل (تیک سبز یا ضربدر قرمز روی فلش وسط)"""
        if not self.prev or self.prev_timer <= 0:
            return
        center, flank, ok = self.prev
        alpha = max(0.0, min(1.0, self.prev_timer / 0.5))
        sw, sh = 220, int(H * 0.6)
        x0, y0 = int(W * COLUMN_X) - sw // 2, int(H * 0.15)
        surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for i in range(5):
            d = center if i == 2 else flank
            y = (COLUMN_Y0 + COLUMN_DY * i) * H - y0
            draw_bird(surf, (sw // 2, y), d, 1.5, ARROW_BLUE)
        ym = (COLUMN_Y0 + COLUMN_DY * 2) * H - y0
        cx = sw // 2
        if ok:
            pygame.draw.lines(surf, GREEN, False,
                              [(cx - 46, ym - 2), (cx - 32, ym + 14), (cx - 4, ym - 20)], 9)
        else:
            pygame.draw.line(surf, RED, (cx - 40, ym - 16), (cx - 8, ym + 16), 9)
            pygame.draw.line(surf, RED, (cx - 40, ym + 16), (cx - 8, ym - 16), 9)
        surf.set_alpha(int(255 * alpha))
        self.screen.blit(surf, (x0, y0))

    def put_text(self, text, x, y, right=False):
        img = self.font_s.render(text, True, TEXT)
        self.screen.blit(img, (x - img.get_width() if right else x, y))

    def draw_hud(self):
        # دکمه‌ی توقف: مربع سرمه‌ای گوشه‌ی بالا چپ
        pr = self.pause_rect
        pygame.draw.rect(self.screen, NAVY, pr)
        pygame.draw.rect(self.screen, (225, 238, 250), (pr.x + 22, pr.y + 19, 8, 28))
        pygame.draw.rect(self.screen, (225, 238, 250), (pr.x + 36, pr.y + 19, 8, 28))
        # نوار روشن و شفاف بالا سمت راست
        pw, ph = int(W * 0.43), 58
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((200, 228, 248, 95))
        self.screen.blit(panel, (W - pw, 0))
        bx = W - pw
        self.put_text("TIME", bx + 16, 20)
        self.put_text(fmt_time(self.time_left), bx + 78, 20)
        self.put_text("SCORE", bx + 160, 20)
        self.put_text(str(self.score), bx + 312, 20, right=True)
        for i in range(DOTS_PER_LEVEL):
            cx = bx + 336 + i * 17
            col = NAVY if i < self.dots else (150, 192, 224)
            pygame.draw.circle(self.screen, col, (cx, 29), 6)
        self.put_text(f"x{self.mult}", W - 14, 20, right=True)

    def overlay(self, lines, dim=120):
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((10, 25, 55, dim))
        self.screen.blit(shade, (0, 0))
        y = H // 2 - 22 * len(lines)
        for text, font, col in lines:
            img = font.render(text, True, col)
            self.screen.blit(img, (W // 2 - img.get_width() // 2, y))
            y += img.get_height() + 14

    def draw(self):
        self.screen.blit(self.bg, (0, 0))
        for x, y, s, _ in self.clouds:
            c = pygame.transform.smoothscale(self.cloud, (int(170 * s), int(70 * s)))
            self.screen.blit(c, (x, y))

        if self.state == "title":
            self.overlay([
                ("LOST IN MIGRATION", self.font_l, WHITE),
                ("Press the arrow key the CENTER bird is facing.", self.font_m, WHITE),
                ("Ignore all the other birds.", self.font_m, WHITE),
                ("Press SPACE to start   (P = pause)", self.font_m, (255, 230, 150)),
                ("Fan-made practice clone", self.font_s, (225, 235, 250)),
            ], dim=90)
            return

        if self.state == "playing":
            self.draw_prev_column()
            self.draw_flock()
        self.draw_hud()

        if self.state == "paused":
            self.overlay([("PAUSED", self.font_l, WHITE),
                          ("Press P to resume", self.font_m, WHITE)], dim=150)
        elif self.state == "over":
            acc = (100 * self.correct / self.total) if self.total else 0
            avg = (1000 * sum(self.rts) / len(self.rts)) if self.rts else 0
            self.overlay([
                ("TIME'S UP", self.font_l, WHITE),
                (f"Score: {self.score}", self.font_m, WHITE),
                (f"Accuracy: {acc:.0f}%  ({self.correct}/{self.total})", self.font_m, WHITE),
                (f"Average reaction: {avg:.0f} ms", self.font_m, WHITE),
                ("Press SPACE to play again", self.font_m, (255, 230, 150)),
            ], dim=150)


def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Lost in Migration - practice clone")
    game = Game(screen)
    clock = pygame.time.Clock()
    while True:
        dt = clock.tick(FPS) / 1000
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            game.handle_event(e)
        game.update(dt)
        game.draw()
        pygame.display.flip()


if __name__ == "__main__":
    main()
