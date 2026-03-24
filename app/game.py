import math
import random
import sys
from dataclasses import dataclass, field

import pygame

# ============================================================
# CONFIG
# ============================================================
WIDTH, HEIGHT = 1280, 720
FPS = 60
TITLE = "Ghost Haunter - Assombre as Casas"

WORLD_SCREEN_HOUSES = 5
HOUSE_MIN_SPACING = 220
HOUSE_MAX_SPACING = 340

PLAYER_SPEED = 260
PLAYER_ACCEL = 0.14

NIGHT_COLOR = (16, 16, 28)
FOG_COLOR = (40, 40, 70)
MOON_COLOR = (240, 240, 210)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (120, 120, 120)
LIGHT_GRAY = (180, 180, 180)
GREEN = (80, 220, 120)
YELLOW = (255, 220, 90)
RED = (240, 80, 80)
BLUE = (100, 180, 255)
PURPLE = (170, 120, 255)
CYAN = (120, 255, 255)
ORANGE = (255, 160, 70)

GROUND_Y = HEIGHT - 150
WORLD_HEIGHT = HEIGHT
HAUNT_DISTANCE = 110
PLAYER_RADIUS = 22

START_LIVES = 3

SPAWN_MARGIN = 450
MAX_ENTITIES_AHEAD = 5000

# ============================================================
# INIT
# ============================================================
pygame.init()
pygame.display.set_caption(TITLE)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

FONT_SM = pygame.font.SysFont("consolas", 18)
FONT_MD = pygame.font.SysFont("consolas", 28, bold=True)
FONT_LG = pygame.font.SysFont("consolas", 48, bold=True)

# ============================================================
# HELPERS
# ============================================================
def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))

def lerp(a, b, t):
    return a + (b - a) * t

def distance(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)

def draw_text(surface, text, font, color, x, y, center=False, shadow=True):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)

    if shadow:
        shadow_render = font.render(text, True, (0, 0, 0))
        shadow_rect = rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        surface.blit(shadow_render, shadow_rect)

    surface.blit(rendered, rect)

def world_to_screen(world_x, cam_x):
    return int(world_x - cam_x)

# ============================================================
# PARTICLES
# ============================================================
@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: tuple
    radius: float

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.vy -= 4 * dt
        return self.life > 0

    def draw(self, surface, cam_x):
        alpha_ratio = max(0.0, min(1.0, self.life / self.max_life if self.max_life > 0 else 0.0))
        r = max(1, int(self.radius * alpha_ratio))

        safe_color = []
        for c in self.color[:3]:
            value = int(c * alpha_ratio)
            value = max(0, min(255, value))
            safe_color.append(value)

        while len(safe_color) < 3:
            safe_color.append(255)

        pygame.draw.circle(
            surface,
            tuple(safe_color),
            (int(world_to_screen(self.x, cam_x)), int(self.y)),
            r
        )

# ============================================================
# GAME ENTITIES
# ============================================================
@dataclass
class House:
    x: float
    y: float
    w: int
    h: int
    haunted: bool = False
    danger_type: str = None  # None, "hunter", "wizard"
    haunt_progress: float = 0.0
    haunt_required: float = 2.2
    pulse: float = field(default_factory=lambda: random.random() * 10)
    score_value: int = 100

    def rect(self):
        return pygame.Rect(self.x - self.w // 2, self.y - self.h, self.w, self.h)

    def update(self, dt):
        self.pulse += dt * 3.0

    def draw(self, surface, cam_x):
        rx = world_to_screen(self.x, cam_x)
        body_rect = pygame.Rect(rx - self.w // 2, self.y - self.h, self.w, self.h)
        roof_points = [
            (rx - self.w // 2 - 8, self.y - self.h),
            (rx, self.y - self.h - 28),
            (rx + self.w // 2 + 8, self.y - self.h),
        ]

        base_color = (65, 50, 70) if not self.haunted else (95, 55, 120)
        roof_color = (90, 40, 40) if not self.haunted else (130, 70, 170)

        pygame.draw.polygon(surface, roof_color, roof_points)
        pygame.draw.rect(surface, base_color, body_rect, border_radius=8)

        # Door
        door_rect = pygame.Rect(rx - 12, self.y - 40, 24, 40)
        pygame.draw.rect(surface, (40, 25, 25), door_rect, border_radius=4)

        # Windows
        wx1 = rx - self.w // 4 - 8
        wx2 = rx + self.w // 4 - 8
        wy = self.y - self.h + 26
        glow = 100 + int(55 * abs(math.sin(self.pulse)))

        if self.haunted:
            win_color = (glow, 80, glow)
        else:
            win_color = (240, 200, 120)

        pygame.draw.rect(surface, win_color, (wx1, wy, 16, 16), border_radius=3)
        pygame.draw.rect(surface, win_color, (wx2, wy, 16, 16), border_radius=3)

        # Danger signs
        if not self.haunted and self.danger_type == "hunter":
            pygame.draw.circle(surface, RED, (rx + self.w // 2 - 12, self.y - self.h + 14), 9)
            pygame.draw.line(surface, WHITE, (rx + self.w // 2 - 16, self.y - self.h + 14),
                             (rx + self.w // 2 - 8, self.y - self.h + 14), 2)
            pygame.draw.line(surface, WHITE, (rx + self.w // 2 - 12, self.y - self.h + 10),
                             (rx + self.w // 2 - 12, self.y - self.h + 18), 2)

        elif not self.haunted and self.danger_type == "wizard":
            pygame.draw.polygon(surface, CYAN, [
                (rx + self.w // 2 - 12, self.y - self.h + 22),
                (rx + self.w // 2 - 6, self.y - self.h + 8),
                (rx + self.w // 2, self.y - self.h + 20),
                (rx + self.w // 2 + 6, self.y - self.h + 6),
                (rx + self.w // 2 + 10, self.y - self.h + 22)
            ])

        # Haunt progress bar
        if not self.haunted and self.haunt_progress > 0:
            bw = self.w
            bx = rx - bw // 2
            by = self.y - self.h - 18
            pygame.draw.rect(surface, (40, 40, 55), (bx, by, bw, 8), border_radius=3)
            fill = int((self.haunt_progress / self.haunt_required) * bw)
            pygame.draw.rect(surface, PURPLE, (bx, by, fill, 8), border_radius=3)

@dataclass
class Hunter:
    x: float
    y: float
    patrol_min: float
    patrol_max: float
    speed: float
    direction: int = 1
    radius: int = 18
    cooldown: float = 0.0

    def update(self, dt):
        self.x += self.speed * self.direction * dt
        if self.x < self.patrol_min:
            self.x = self.patrol_min
            self.direction = 1
        elif self.x > self.patrol_max:
            self.x = self.patrol_max
            self.direction = -1

        if self.cooldown > 0:
            self.cooldown -= dt

    def draw(self, surface, cam_x):
        sx = world_to_screen(self.x, cam_x)
        pygame.draw.circle(surface, (230, 230, 235), (sx, int(self.y)), self.radius)
        pygame.draw.rect(surface, (70, 90, 110), (sx - 10, self.y + 10, 20, 24), border_radius=5)
        pygame.draw.circle(surface, (255, 255, 180), (sx + self.direction * 18, int(self.y)), 10)

@dataclass
class Wizard:
    x: float
    y: float
    range_radius: int
    pulse: float = field(default_factory=lambda: random.random() * 5)
    attack_cd: float = 0.0

    def update(self, dt):
        self.pulse += dt * 2.5
        if self.attack_cd > 0:
            self.attack_cd -= dt

    def draw(self, surface, cam_x):
        sx = world_to_screen(self.x, cam_x)
        pygame.draw.circle(surface, (80, 20, 120), (sx, int(self.y)), 17)
        pygame.draw.polygon(surface, (120, 40, 180), [
            (sx - 16, self.y + 18),
            (sx, self.y - 24),
            (sx + 16, self.y + 18)
        ])

        rr = int(self.range_radius + 8 * math.sin(self.pulse))
        pygame.draw.circle(surface, (70, 160, 255), (sx, int(self.y)), rr, 2)

@dataclass
class FloatingScore:
    x: float
    y: float
    value: str
    color: tuple
    life: float = 1.2

    def update(self, dt):
        self.y -= 30 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface, cam_x):
        ratio = max(0, self.life / 1.2)
        col = tuple(int(c * ratio) for c in self.color)
        draw_text(surface, self.value, FONT_SM, col, world_to_screen(self.x, cam_x), int(self.y), center=True, shadow=False)

# ============================================================
# PLAYER
# ============================================================
class Player:
    def __init__(self):
        self.x = 120
        self.y = GROUND_Y - 80
        self.vx = 0
        self.vy = 0
        self.radius = PLAYER_RADIUS
        self.hp = START_LIVES
        self.score = 0
        self.combo = 0
        self.combo_timer = 0.0
        self.invuln = 0.0
        self.haunting = False
        self.anim = 0.0
        self.dash_cd = 0.0

    def update(self, dt, keys):
        self.anim += dt * 8

        move = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.y -= PLAYER_SPEED * 0.75 * dt
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.y += PLAYER_SPEED * 0.75 * dt

        target_vx = move * PLAYER_SPEED
        self.vx = lerp(self.vx, target_vx, PLAYER_ACCEL)
        self.x += self.vx * dt

        bob = math.sin(self.anim * 1.7) * 8
        target_y = clamp(self.y, 120, GROUND_Y - 40) + bob * 0.04
        self.y = lerp(self.y, target_y, 0.2)

        if self.combo_timer > 0:
            self.combo_timer -= dt
        else:
            self.combo = 0

        if self.invuln > 0:
            self.invuln -= dt

        if self.dash_cd > 0:
            self.dash_cd -= dt

    def dash(self):
        if self.dash_cd <= 0:
            self.x += 110
            self.dash_cd = 2.0

    def hurt(self):
        if self.invuln <= 0:
            self.hp -= 1
            self.combo = 0
            self.combo_timer = 0
            self.invuln = 2.0
            return True
        return False

    def add_score(self, amount):
        self.combo += 1
        self.combo_timer = 4.0
        mult = 1.0 + min(self.combo * 0.1, 1.5)
        gained = int(amount * mult)
        self.score += gained
        return gained, mult

    def draw(self, surface, cam_x):
        if self.invuln > 0 and int(self.invuln * 10) % 2 == 0:
            return

        sx = world_to_screen(self.x, cam_x)
        sy = int(self.y)

        aura_r = self.radius + int(4 * abs(math.sin(self.anim * 1.4)))
        pygame.draw.circle(surface, (90, 220, 255), (sx, sy), aura_r + 10, 2)

        # body
        pygame.draw.circle(surface, (220, 245, 255), (sx, sy), self.radius)
        pygame.draw.rect(surface, (220, 245, 255), (sx - self.radius, sy, self.radius * 2, self.radius + 10), border_radius=15)

        # eyes
        pygame.draw.circle(surface, BLACK, (sx - 7, sy - 3), 3)
        pygame.draw.circle(surface, BLACK, (sx + 7, sy - 3), 3)

        # mouth
        pygame.draw.arc(surface, BLACK, (sx - 8, sy + 1, 16, 12), math.pi * 0.1, math.pi * 0.9, 2)

        # tail waves
        points = [
            (sx - self.radius, sy + self.radius + 4),
            (sx - 10, sy + self.radius + 14 + int(2 * math.sin(self.anim))),
            (sx + 5, sy + self.radius + 4),
            (sx + 15, sy + self.radius + 14 + int(2 * math.cos(self.anim))),
            (sx + self.radius, sy + self.radius + 4),
        ]
        pygame.draw.lines(surface, (200, 240, 255), False, points, 6)

# ============================================================
# GAME
# ============================================================
class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.player = Player()
        self.cam_x = 0
        self.houses = []
        self.hunters = []
        self.wizards = []
        self.particles = []
        self.floating_scores = []
        self.next_house_x = 350
        self.best_distance = 0
        self.game_over = False
        self.paused = False
        self.time_survived = 0.0
        self.difficulty = 1.0
        self.generate_until(self.player.x + WIDTH + 2000)

    def generate_until(self, target_x):
        while self.next_house_x < target_x:
            self.spawn_house_cluster()
            self.next_house_x += random.randint(220, 320)

    def spawn_house_cluster(self):
        visible_span = WIDTH * 1.2
        approx_house_gap = visible_span / WORLD_SCREEN_HOUSES
        x = self.next_house_x + random.randint(-50, 60)
        y = GROUND_Y

        w = random.randint(70, 120)
        h = random.randint(80, 150)

        score_value = random.choice([80, 100, 120, 150])

        danger_roll = random.random()
        danger_type = None

        # Difficulty increases over distance
        self.difficulty = 1.0 + self.player.x / 3500.0

        hunter_chance = min(0.12 + self.difficulty * 0.03, 0.38)
        wizard_chance = min(0.10 + self.difficulty * 0.025, 0.34)

        if danger_roll < hunter_chance:
            danger_type = "hunter"
        elif danger_roll < hunter_chance + wizard_chance:
            danger_type = "wizard"

        house = House(
            x=x,
            y=y,
            w=w,
            h=h,
            haunted=False,
            danger_type=danger_type,
            haunt_required=max(1.0, 2.4 - min(self.difficulty * 0.07, 1.2)),
            score_value=score_value + int(self.difficulty * 10),
        )
        self.houses.append(house)

        if danger_type == "hunter":
            patrol = random.randint(100, 170)
            hunter = Hunter(
                x=x + random.randint(-20, 20),
                y=GROUND_Y - 18,
                patrol_min=x - patrol,
                patrol_max=x + patrol,
                speed=random.randint(60, 110) + self.difficulty * 8,
            )
            self.hunters.append(hunter)

        elif danger_type == "wizard":
            wizard = Wizard(
                x=x + random.randint(-40, 40),
                y=GROUND_Y - 24,
                range_radius=random.randint(85, 130) + int(self.difficulty * 5),
            )
            self.wizards.append(wizard)

        self.next_house_x += int(approx_house_gap + random.randint(-30, 30))

    def spawn_particles(self, x, y, color, amount=10, speed=100):
        safe_color = tuple(max(0, min(255, int(c))) for c in color[:3])

        for _ in range(amount):
            ang = random.random() * math.pi * 2
            spd = random.uniform(speed * 0.3, speed)
            vx = math.cos(ang) * spd
            vy = math.sin(ang) * spd
            life = random.uniform(0.3, 0.9)
            radius = float(random.uniform(2, 5))
            self.particles.append(Particle(x, y, vx, vy, life, life, safe_color, radius))

    def nearest_house_in_range(self):
        candidate = None
        best_dist = 999999
        for house in self.houses:
            if house.haunted:
                continue
            d = distance(self.player.x, self.player.y, house.x, house.y - house.h * 0.5)
            if d < HAUNT_DISTANCE and d < best_dist:
                candidate = house
                best_dist = d
        return candidate

    def handle_haunting(self, dt, keys):
        self.player.haunting = False
        target = self.nearest_house_in_range()

        if target and (keys[pygame.K_SPACE] or keys[pygame.K_RETURN]):
            self.player.haunting = True
            target.haunt_progress += dt

            if random.random() < 0.35:
                self.particles.append(
                    Particle(
                        self.player.x + random.randint(-18, 18),
                        self.player.y + random.randint(-8, 8),
                        random.uniform(-20, 20),
                        random.uniform(-40, 10),
                        0.7,
                        0.7,
                        PURPLE,
                        random.uniform(2, 4),
                    )
                )

            if target.haunt_progress >= target.haunt_required:
                target.haunted = True
                gained, mult = self.player.add_score(target.score_value)
                self.spawn_particles(target.x, target.y - target.h // 2, CYAN, amount=26, speed=120)
                self.spawn_particles(target.x, target.y - target.h // 2, PURPLE, amount=26, speed=120)
                self.floating_scores.append(
                    FloatingScore(target.x, target.y - target.h - 10, f"+{gained}", YELLOW)
                )
                self.floating_scores.append(
                    FloatingScore(target.x, target.y - target.h - 32, f"x{mult:.1f}", CYAN)
                )

    def handle_enemies(self, dt):
        # Hunters damage on touch
        for hunter in self.hunters:
            hunter.update(dt)
            d = distance(self.player.x, self.player.y, hunter.x, hunter.y)
            if d < self.player.radius + hunter.radius + 5:
                if self.player.hurt():
                    self.spawn_particles(self.player.x, self.player.y, RED, amount=24, speed=160)
                    self.floating_scores.append(FloatingScore(self.player.x, self.player.y - 40, "-1 VIDA", RED))

        # Wizards damage in aura if not moving carefully
        for wizard in self.wizards:
            wizard.update(dt)
            d = distance(self.player.x, self.player.y, wizard.x, wizard.y)
            in_range = d < wizard.range_radius
            if in_range and wizard.attack_cd <= 0:
                if self.player.hurt():
                    wizard.attack_cd = 1.5
                    self.spawn_particles(self.player.x, self.player.y, BLUE, amount=20, speed=130)
                    self.floating_scores.append(FloatingScore(self.player.x, self.player.y - 40, "MALDIÇÃO!", BLUE))

    def cleanup_world(self):
        left_bound = self.cam_x - 300
        right_bound = self.cam_x + WIDTH + MAX_ENTITIES_AHEAD

        self.houses = [h for h in self.houses if left_bound < h.x < right_bound]
        self.hunters = [e for e in self.hunters if left_bound < e.x < right_bound]
        self.wizards = [e for e in self.wizards if left_bound < e.x < right_bound]

    def update(self, dt):
        if self.game_over or self.paused:
            return

        keys = pygame.key.get_pressed()

        self.player.update(dt, keys)

        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            self.player.dash()

        self.time_survived += dt
        self.best_distance = max(self.best_distance, self.player.x)

        self.cam_x = max(0, self.player.x - WIDTH * 0.25)

        self.generate_until(self.player.x + WIDTH * 3)
        self.cleanup_world()

        for house in self.houses:
            house.update(dt)

        self.handle_haunting(dt, keys)
        self.handle_enemies(dt)

        self.particles = [p for p in self.particles if p.update(dt)]
        self.floating_scores = [f for f in self.floating_scores if f.update(dt)]

        # passive ambient particles
        if random.random() < 0.16:
            self.particles.append(
                Particle(
                    self.cam_x + WIDTH + random.randint(0, 100),
                    random.randint(90, GROUND_Y - 80),
                    random.uniform(-18, -5),
                    random.uniform(-6, 6),
                    random.uniform(1.8, 3.5),
                    random.uniform(1.8, 3.5),
                    (120, 120, 170),
                    random.uniform(1, 3),
                )
            )

        if self.player.hp <= 0:
            self.game_over = True

    # ========================================================
    # DRAW
    # ========================================================
    def draw_background(self, surface):
        surface.fill(NIGHT_COLOR)

        # moon
        pygame.draw.circle(surface, MOON_COLOR, (1040, 110), 48)
        pygame.draw.circle(surface, NIGHT_COLOR, (1058, 98), 40)

        # stars
        for i in range(35):
            sx = (i * 123) % WIDTH
            sy = (i * 77) % (GROUND_Y - 220)
            pygame.draw.circle(surface, WHITE, (sx, sy), 1)

        # far hills
        for i in range(-2, 8):
            x = (i * 260) - int(self.cam_x * 0.15) % 260
            pygame.draw.ellipse(surface, (28, 35, 52), (x, GROUND_Y - 70, 320, 150))

        # closer hills
        for i in range(-2, 8):
            x = (i * 220) - int(self.cam_x * 0.3) % 220
            pygame.draw.ellipse(surface, (35, 45, 65), (x, GROUND_Y - 40, 260, 120))

        # ground
        pygame.draw.rect(surface, (32, 50, 40), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
        pygame.draw.rect(surface, (25, 40, 30), (0, GROUND_Y + 16, WIDTH, HEIGHT - GROUND_Y))

        # grass details
        for x in range(0, WIDTH, 24):
            h = 6 + ((x * 7) % 8)
            pygame.draw.line(surface, (45, 80, 52), (x, GROUND_Y), (x + 3, GROUND_Y - h), 2)

    def draw_world(self, surface):
        # mist
        mist = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        mist.fill((0, 0, 0, 0))
        for i in range(4):
            pygame.draw.ellipse(
                mist,
                (140, 140, 180, 18),
                (
                    -100 + i * 340 - int(self.cam_x * (0.08 + i * 0.01)) % 200,
                    110 + i * 85,
                    420,
                    90,
                ),
            )
        surface.blit(mist, (0, 0))

        for house in self.houses:
            house.draw(surface, self.cam_x)

        for hunter in self.hunters:
            hunter.draw(surface, self.cam_x)

        for wizard in self.wizards:
            wizard.draw(surface, self.cam_x)

        for particle in self.particles:
            particle.draw(surface, self.cam_x)

        self.player.draw(surface, self.cam_x)

        # haunting beam
        if self.player.haunting:
            target = self.nearest_house_in_range()
            if target:
                sx1 = world_to_screen(self.player.x, self.cam_x)
                sx2 = world_to_screen(target.x, self.cam_x)
                sy1 = int(self.player.y)
                sy2 = int(target.y - target.h * 0.55)

                for i in range(3):
                    off = random.randint(-4, 4)
                    pygame.draw.line(surface, (180, 120, 255), (sx1, sy1 + off), (sx2, sy2 + off), 2)

        for fs in self.floating_scores:
            fs.draw(surface, self.cam_x)

    def draw_hud(self, surface):
        panel = pygame.Surface((390, 120), pygame.SRCALPHA)
        panel.fill((12, 12, 20, 170))
        surface.blit(panel, (16, 16))
        pygame.draw.rect(surface, (90, 90, 120), (16, 16, 390, 120), 2, border_radius=12)

        draw_text(surface, f"Pontos: {self.player.score}", FONT_MD, YELLOW, 30, 28)
        draw_text(surface, f"Combo: x{1.0 + min(self.player.combo * 0.1, 1.5):.1f}", FONT_SM, CYAN, 30, 64)
        draw_text(surface, f"Distância: {int(self.best_distance)} m", FONT_SM, WHITE, 30, 88)

        draw_text(surface, "Vidas:", FONT_SM, WHITE, 250, 30)
        for i in range(self.player.hp):
            pygame.draw.circle(surface, (220, 245, 255), (310 + i * 28, 40), 10)
            pygame.draw.circle(surface, (120, 220, 255), (310 + i * 28, 40), 12, 2)

        draw_text(surface, f"Dificuldade: {self.difficulty:.1f}", FONT_SM, ORANGE, 250, 66)

        draw_text(surface, "A/D ou ←/→ mover | W/S voar | SPACE assombrar | SHIFT dash", FONT_SM, LIGHT_GRAY, 16, HEIGHT - 34)

        target = self.nearest_house_in_range()
        if target and not target.haunted:
            draw_text(surface, "Casa ao alcance! Segure SPACE para assombrar", FONT_SM, PURPLE, WIDTH // 2, 28, center=True)

    def draw_game_over(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))

        draw_text(surface, "FIM DE JOGO", FONT_LG, RED, WIDTH // 2, HEIGHT // 2 - 120, center=True)
        draw_text(surface, f"Pontuação final: {self.player.score}", FONT_MD, YELLOW, WIDTH // 2, HEIGHT // 2 - 40, center=True)
        draw_text(surface, f"Casas assombradas: {sum(1 for h in self.houses if h.haunted)}+", FONT_MD, CYAN, WIDTH // 2, HEIGHT // 2 + 5, center=True)
        draw_text(surface, f"Distância percorrida: {int(self.best_distance)} m", FONT_MD, WHITE, WIDTH // 2, HEIGHT // 2 + 50, center=True)
        draw_text(surface, "Pressione R para reiniciar", FONT_MD, GREEN, WIDTH // 2, HEIGHT // 2 + 130, center=True)

    def draw_pause(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surface.blit(overlay, (0, 0))
        draw_text(surface, "PAUSADO", FONT_LG, WHITE, WIDTH // 2, HEIGHT // 2, center=True)

    def draw(self, surface):
        self.draw_background(surface)
        self.draw_world(surface)
        self.draw_hud(surface)

        if self.paused and not self.game_over:
            self.draw_pause(surface)

        if self.game_over:
            self.draw_game_over(surface)

# ============================================================
# MENU
# ============================================================
def draw_menu(surface, blink_timer):
    surface.fill((10, 10, 22))

    pygame.draw.circle(surface, MOON_COLOR, (950, 120), 56)
    pygame.draw.circle(surface, (10, 10, 22), (970, 104), 44)

    draw_text(surface, "GHOST HAUNTER", FONT_LG, CYAN, WIDTH // 2, 160, center=True)
    draw_text(surface, "Assombre casas. Fuja de caçadores e feiticeiros.", FONT_MD, WHITE, WIDTH // 2, 240, center=True)
    draw_text(surface, "Jogo infinito com mapa procedural e perigo crescente.", FONT_SM, LIGHT_GRAY, WIDTH // 2, 285, center=True)

    # mini ghost icon
    gx, gy = WIDTH // 2, 410
    pygame.draw.circle(surface, (220, 245, 255), (gx, gy), 38)
    pygame.draw.rect(surface, (220, 245, 255), (gx - 38, gy, 76, 48), border_radius=18)
    pygame.draw.circle(surface, BLACK, (gx - 12, gy - 4), 5)
    pygame.draw.circle(surface, BLACK, (gx + 12, gy - 4), 5)
    pygame.draw.arc(surface, BLACK, (gx - 14, gy + 6, 28, 18), math.pi * 0.1, math.pi * 0.9, 3)

    for i in range(3):
        pygame.draw.line(surface, (180, 220, 255), (gx - 34 + i * 24, gy + 40), (gx - 24 + i * 24, gy + 52), 6)

    if int(blink_timer * 2) % 2 == 0:
        draw_text(surface, "Pressione ENTER para começar", FONT_MD, GREEN, WIDTH // 2, 590, center=True)

    draw_text(surface, "Controles: A/D mover | W/S voar | SPACE assombrar | SHIFT dash | ESC pausa",
              FONT_SM, LIGHT_GRAY, WIDTH // 2, 650, center=True)

# ============================================================
# MAIN LOOP
# ============================================================
def main():
    game = Game()
    state = "menu"
    blink_timer = 0.0

    while True:
        dt = clock.tick(FPS) / 1000.0
        blink_timer += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if state == "menu":
                    if event.key == pygame.K_RETURN:
                        game.reset()
                        state = "playing"

                elif state == "playing":
                    if event.key == pygame.K_ESCAPE:
                        game.paused = not game.paused

                    if game.game_over and event.key == pygame.K_r:
                        game.reset()

        if state == "menu":
            draw_menu(screen, blink_timer)

        elif state == "playing":
            game.update(dt)
            game.draw(screen)

        pygame.display.flip()

if __name__ == "__main__":
    main()