import json
import math
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pygame

# ============================================================
# CONFIG
# ============================================================
WIDTH, HEIGHT = 1280, 720
FPS = 60
TITLE = "Ghost Haunter - Strategic Infinite Haunting"

GROUND_Y = HEIGHT - 135
PLAYER_RADIUS = 22
HAUNT_DISTANCE = 140

WORLD_SCREEN_HOUSES_MIN = 4
WORLD_SCREEN_HOUSES_MAX = 6

META_FILE = Path(__file__).resolve().parent / "meta_progress.json"

NIGHT = (14, 14, 30)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (240, 80, 90)
GREEN = (80, 230, 130)
YELLOW = (255, 220, 110)
BLUE = (90, 190, 255)
CYAN = (110, 255, 255)
PURPLE = (170, 120, 255)
ORANGE = (255, 160, 80)

pygame.init()
pygame.display.set_caption(TITLE)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

FONT_SM = pygame.font.SysFont("consolas", 18)
FONT_MD = pygame.font.SysFont("consolas", 28, bold=True)
FONT_LG = pygame.font.SysFont("consolas", 46, bold=True)


# ============================================================
# HELPERS
# ============================================================
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


def draw_text(surface, text, font, color, x, y, center=False, shadow=True):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)

    if shadow:
        sh = font.render(text, True, (0, 0, 0))
        surface.blit(sh, rect.move(2, 2))
    surface.blit(img, rect)


def dist(a, b, c, d):
    return math.hypot(a - c, b - d)


def world_to_screen(world_x, cam_x):
    return int(world_x - cam_x)


# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class MetaProgress:
    essence_bank: int = 0
    speed_level: int = 0
    haunt_level: int = 0
    power_level: int = 0

    @classmethod
    def load(cls):
        if META_FILE.exists():
            try:
                return cls(**json.loads(META_FILE.read_text()))
            except (json.JSONDecodeError, OSError, TypeError):
                pass
        return cls()

    def save(self):
        META_FILE.write_text(json.dumps(self.__dict__, indent=2))

    def cost(self, key):
        lvl = getattr(self, f"{key}_level")
        return 30 + lvl * 25


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
        self.vy += 18 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface, cam_x):
        ratio = max(0.0, self.life / self.max_life if self.max_life else 0.0)
        col = tuple(int(clamp(c * ratio, 0, 255)) for c in self.color[:3])
        pygame.draw.circle(surface, col, (world_to_screen(self.x, cam_x), int(self.y)), max(1, int(self.radius * ratio)))


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: tuple
    life: float = 1.3

    def update(self, dt):
        self.y -= 34 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface, cam_x):
        ratio = clamp(self.life / 1.3, 0, 1)
        draw_text(surface, self.text, FONT_SM, tuple(int(c * ratio) for c in self.color), world_to_screen(self.x, cam_x), int(self.y), center=True, shadow=False)


@dataclass
class House:
    x: float
    y: float
    w: int
    h: int
    house_type: str
    haunted: bool = False
    haunt_progress: float = 0.0
    haunt_required: float = 2.0
    deep_level: float = 0.0
    ritual_phase: float = 0.0
    alert_timer: float = 0.0
    last_angle: float = 0.0
    orbit_accum: float = 0.0

    def center(self):
        return self.x, self.y - self.h * 0.55

    def update(self, dt):
        self.ritual_phase += dt * 1.8
        self.alert_timer = max(0.0, self.alert_timer - dt)
        if self.haunt_progress > 0 and not self.haunted:
            self.haunt_progress = max(0.0, self.haunt_progress - dt * 0.1)

    def draw(self, surface, cam_x):
        sx = world_to_screen(self.x, cam_x)
        body = pygame.Rect(sx - self.w // 2, self.y - self.h, self.w, self.h)
        roof = [(sx - self.w // 2 - 8, self.y - self.h), (sx, self.y - self.h - 30), (sx + self.w // 2 + 8, self.y - self.h)]

        base = (70, 52, 70) if not self.haunted else (90, 62, 120)
        roof_col = (95, 45, 50) if not self.haunted else (130, 70, 170)
        pygame.draw.polygon(surface, roof_col, roof)
        pygame.draw.rect(surface, base, body, border_radius=8)

        glow = 130 + int(90 * abs(math.sin(self.ritual_phase)))
        win_col = (glow, 200, 140) if self.house_type != "alert" else (255, 140, 140)
        if self.haunted:
            win_col = (180, 110, 255)
        pygame.draw.rect(surface, win_col, (sx - self.w // 4 - 8, self.y - self.h + 24, 16, 16), border_radius=3)
        pygame.draw.rect(surface, win_col, (sx + self.w // 4 - 8, self.y - self.h + 24, 16, 16), border_radius=3)

        type_color = {
            "normal": WHITE,
            "resistant": ORANGE,
            "ritual": CYAN,
            "alert": RED,
        }[self.house_type]
        pygame.draw.circle(surface, type_color, (sx + self.w // 2 - 12, self.y - self.h + 14), 8)

        if self.house_type == "alert" and not self.haunted:
            pulse = 120 + int(120 * abs(math.sin(self.ritual_phase * 2)))
            pygame.draw.circle(surface, (pulse, 60, 60), (sx, self.y - self.h // 2), self.w // 2 + 25, 2)

        if not self.haunted and self.haunt_progress > 0:
            bw = self.w
            bx, by = sx - bw // 2, self.y - self.h - 18
            pygame.draw.rect(surface, (30, 30, 45), (bx, by, bw, 8), border_radius=3)
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
    detect_radius: float = 175.0
    chase_timer: float = 0.0
    attack_cd: float = 0.0

    def update(self, dt, player_x, player_y, difficulty):
        self.detect_radius = 170 + difficulty * 6
        if self.attack_cd > 0:
            self.attack_cd -= dt

        d = dist(self.x, self.y, player_x, player_y)
        if d < self.detect_radius:
            self.chase_timer = 1.8

        if self.chase_timer > 0:
            self.chase_timer -= dt
            direction = 1 if player_x > self.x else -1
            self.x += direction * (self.speed + 80 + difficulty * 7) * dt
            self.direction = direction
        else:
            self.x += self.speed * self.direction * dt
            if self.x <= self.patrol_min:
                self.x = self.patrol_min
                self.direction = 1
            elif self.x >= self.patrol_max:
                self.x = self.patrol_max
                self.direction = -1

    def draw(self, surface, cam_x):
        sx = world_to_screen(self.x, cam_x)
        pygame.draw.circle(surface, (235, 235, 240), (sx, int(self.y)), 17)
        pygame.draw.rect(surface, (70, 90, 112), (sx - 9, self.y + 8, 18, 24), border_radius=5)
        pygame.draw.circle(surface, (255, 250, 160), (sx + self.direction * 15, int(self.y)), 9)
        if self.chase_timer > 0:
            pygame.draw.circle(surface, RED, (sx, int(self.y - 22)), 6)


@dataclass
class Wizard:
    x: float
    y: float
    range_radius: float
    pulse: float = field(default_factory=lambda: random.random() * 9)
    cast_cd: float = 0.0
    zone_timer: float = 0.0

    def update(self, dt, difficulty):
        self.pulse += dt * 2.2
        self.range_radius = 90 + difficulty * 8
        if self.cast_cd > 0:
            self.cast_cd -= dt
        else:
            self.zone_timer = 1.3
            self.cast_cd = max(2.2 - difficulty * 0.04, 0.8)
        self.zone_timer = max(0.0, self.zone_timer - dt)

    def draw(self, surface, cam_x):
        sx = world_to_screen(self.x, cam_x)
        pygame.draw.circle(surface, (90, 20, 130), (sx, int(self.y)), 16)
        pygame.draw.polygon(surface, (140, 50, 190), [(sx - 16, self.y + 16), (sx, self.y - 22), (sx + 16, self.y + 16)])
        rr = int(self.range_radius + 8 * math.sin(self.pulse))
        pygame.draw.circle(surface, (80, 170, 255), (sx, int(self.y)), rr, 2)
        if self.zone_timer > 0:
            pygame.draw.circle(surface, (255, 80, 220), (sx, int(self.y)), int(rr * 0.6), 3)


# ============================================================
# PLAYER
# ============================================================
class Player:
    def __init__(self, meta: MetaProgress):
        self.meta = meta
        self.x = 140
        self.y = GROUND_Y - 90
        self.vx = 0.0
        self.vy = 0.0
        self.radius = PLAYER_RADIUS

        self.max_hp = 4
        self.hp = self.max_hp
        self.score = 0
        self.combo = 0
        self.combo_timer = 0.0
        self.invuln = 0.0
        self.haunting = False
        self.anim = 0.0

        self.energy_max = 100
        self.energy = 100

        self.cd_dash = 0.0
        self.cd_teleport = 0.0
        self.cd_invis = 0.0
        self.cd_aoe = 0.0
        self.invis_timer = 0.0

    @property
    def speed(self):
        return 250 + self.meta.speed_level * 16

    @property
    def haunt_bonus(self):
        return 1.0 + self.meta.haunt_level * 0.12

    @property
    def power_bonus(self):
        return 1.0 + self.meta.power_level * 0.18

    def update(self, dt, keys):
        self.anim += dt * 8

        mx = 0
        my = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            mx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            mx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            my -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            my += 1

        self.vx = lerp(self.vx, mx * self.speed, 0.13)
        self.vy = lerp(self.vy, my * self.speed * 0.85, 0.18)
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.y = clamp(self.y, 90, GROUND_Y - 45)

        if self.combo_timer > 0:
            self.combo_timer -= dt
        else:
            self.combo = 0

        self.energy = min(self.energy_max, self.energy + dt * 10)

        for attr in ("invuln", "cd_dash", "cd_teleport", "cd_invis", "cd_aoe", "invis_timer"):
            setattr(self, attr, max(0.0, getattr(self, attr) - dt))

    def damage(self):
        if self.invuln > 0 or self.invis_timer > 0:
            return False
        self.hp -= 1
        self.combo = 0
        self.combo_timer = 0
        self.invuln = 1.5
        return True

    def add_score(self, base):
        self.combo += 1
        self.combo_timer = 4.0
        mult = 1.0 + min(self.combo * 0.08, 2.0)
        gain = int(base * mult)
        self.score += gain
        return gain, mult

    def can_use(self, cd_attr, cost):
        return getattr(self, cd_attr) <= 0 and self.energy >= cost

    def cast_dash(self):
        if self.can_use("cd_dash", 24):
            self.energy -= 24
            self.cd_dash = 1.6
            self.x += 130
            return True
        return False

    def cast_teleport(self):
        if self.can_use("cd_teleport", 30):
            self.energy -= 30
            self.cd_teleport = 4.8
            self.x += 220
            self.y += random.randint(-50, 50)
            self.y = clamp(self.y, 90, GROUND_Y - 45)
            return True
        return False

    def cast_invis(self):
        if self.can_use("cd_invis", 38):
            self.energy -= 38
            self.cd_invis = 10.0
            self.invis_timer = 3.0
            return True
        return False

    def draw(self, surface, cam_x):
        if self.invuln > 0 and int(self.invuln * 12) % 2 == 0:
            return

        sx, sy = world_to_screen(self.x, cam_x), int(self.y)
        aura_col = (90, 230, 255) if self.invis_timer <= 0 else (120, 255, 160)
        aura = self.radius + int(4 * abs(math.sin(self.anim)))
        pygame.draw.circle(surface, aura_col, (sx, sy), aura + 11, 2)
        pygame.draw.circle(surface, (220, 245, 255), (sx, sy), self.radius)
        pygame.draw.rect(surface, (220, 245, 255), (sx - self.radius, sy, self.radius * 2, self.radius + 10), border_radius=13)
        pygame.draw.circle(surface, BLACK, (sx - 7, sy - 3), 3)
        pygame.draw.circle(surface, BLACK, (sx + 7, sy - 3), 3)


# ============================================================
# WORLD EVENTS
# ============================================================
EVENTS = ["normal", "haunted_village", "protected_zone", "eclipse", "hunter_wave"]


# ============================================================
# GAME
# ============================================================
class Game:
    def __init__(self, meta):
        self.meta = meta
        self.reset()

    def reset(self):
        self.player = Player(self.meta)
        self.cam_x = 0.0
        self.cam_shake = 0.0

        self.houses = []
        self.hunters = []
        self.wizards = []
        self.particles = []
        self.floating = []

        self.next_house_x = 260
        self.best_dist = 0
        self.time_survived = 0.0
        self.difficulty = 1.0

        self.current_event = "normal"
        self.event_until_x = 0

        self.essence_run = 0
        self.game_over = False
        self.paused = False

        self.generate_until(self.player.x + WIDTH * 3)

    def maybe_roll_event(self):
        if self.player.x < self.event_until_x:
            return
        if random.random() < 0.17:
            self.current_event = random.choice(EVENTS[1:])
            self.event_until_x = self.player.x + random.randint(1200, 2100)
            self.floating.append(FloatingText(self.player.x + 200, 120, self.current_event.upper(), ORANGE))
        else:
            self.current_event = "normal"
            self.event_until_x = self.player.x + random.randint(800, 1300)

    def generate_until(self, target_x):
        while self.next_house_x < target_x:
            self.maybe_roll_event()
            self.spawn_screen_pack()

    def spawn_screen_pack(self):
        houses_count = random.randint(WORLD_SCREEN_HOUSES_MIN, WORLD_SCREEN_HOUSES_MAX)
        span = WIDTH * random.uniform(0.9, 1.15)
        gap = span / houses_count

        for _ in range(houses_count):
            hx = self.next_house_x + random.randint(-40, 40)
            w, h = random.randint(72, 122), random.randint(80, 155)

            house_type = random.choices(["normal", "resistant", "ritual", "alert"], weights=[46, 22, 18, 14], k=1)[0]
            if self.current_event == "haunted_village":
                house_type = random.choices(["normal", "resistant", "ritual"], weights=[52, 28, 20], k=1)[0]
            elif self.current_event == "protected_zone":
                house_type = random.choice(["alert", "resistant", "ritual"])

            req = random.uniform(1.6, 2.8) + self.difficulty * 0.03
            self.houses.append(House(hx, GROUND_Y, w, h, house_type, haunt_required=req))

            enemy_roll = random.random()
            hunter_bonus = 0.15 if self.current_event in ("protected_zone", "hunter_wave") else 0.0
            wizard_bonus = 0.16 if self.current_event == "protected_zone" else 0.0
            hunter_ch = min(0.12 + self.difficulty * 0.02 + hunter_bonus, 0.75)
            wizard_ch = min(0.10 + self.difficulty * 0.017 + wizard_bonus, 0.60)

            if enemy_roll < hunter_ch:
                patrol = random.randint(120, 180)
                self.hunters.append(Hunter(hx, GROUND_Y - 20, hx - patrol, hx + patrol, random.randint(62, 110)))
            elif enemy_roll < hunter_ch + wizard_ch:
                self.wizards.append(Wizard(hx + random.randint(-30, 30), GROUND_Y - 26, 95))

            self.next_house_x += int(gap + random.randint(-28, 34))

    def nearest_house(self):
        cand, best = None, 999999
        for house in self.houses:
            if house.haunted:
                continue
            cx, cy = house.center()
            d = dist(self.player.x, self.player.y, cx, cy)
            if d < HAUNT_DISTANCE and d < best:
                cand, best = house, d
        return cand

    def spawn_particles(self, x, y, color, amount=14, speed=120):
        for _ in range(amount):
            a = random.random() * math.tau
            s = random.uniform(speed * 0.35, speed)
            self.particles.append(Particle(x, y, math.cos(a) * s, math.sin(a) * s, random.uniform(0.35, 0.9), random.uniform(0.35, 0.9), color, random.uniform(2, 4.5)))

    def haunt_house(self, house, dt, quick_mode):
        px, py = self.player.x, self.player.y
        hx, hy = house.center()
        motion = math.hypot(self.player.vx, self.player.vy)
        gain = dt * self.player.haunt_bonus

        if house.house_type == "resistant":
            ang = math.atan2(py - hy, px - hx)
            delta = abs((ang - house.last_angle + math.pi) % (2 * math.pi) - math.pi)
            house.orbit_accum += delta
            house.last_angle = ang
            if motion > 75 and house.orbit_accum > 0.06:
                gain *= 1.35
            else:
                gain *= 0.38

        elif house.house_type == "ritual":
            rhythm = 0.5 + 0.5 * math.sin(house.ritual_phase * 3.1)
            if rhythm > 0.6:
                gain *= 1.7
            else:
                gain *= 0.28

        elif house.house_type == "alert":
            detect = dist(px, py, house.x, house.y - house.h * 0.5) < house.w * 0.7 + 50
            if detect and self.player.invis_timer <= 0:
                gain *= 0.55
                house.alert_timer = 1.4
                if random.random() < 0.03:
                    self.hunters.append(Hunter(house.x + random.randint(-45, 45), GROUND_Y - 20, house.x - 170, house.x + 170, 88))

        if quick_mode:
            gain *= 0.75
        else:
            gain *= 1.25
            house.deep_level += dt
            if house.deep_level > 2.2 and random.random() < 0.06:
                if random.random() < 0.55:
                    self.wizards.append(Wizard(house.x + random.randint(-60, 60), GROUND_Y - 26, 95))
                else:
                    self.hunters.append(Hunter(house.x, GROUND_Y - 20, house.x - 150, house.x + 150, 94))
                self.floating.append(FloatingText(house.x, house.y - house.h - 25, "OVERCHARGE!", RED))

        house.haunt_progress += gain

        if random.random() < 0.32:
            self.particles.append(Particle(px + random.randint(-16, 16), py + random.randint(-10, 10), random.uniform(-20, 20), random.uniform(-35, 12), 0.7, 0.7, PURPLE, random.uniform(1.8, 3.8)))

        if house.haunt_progress >= house.haunt_required:
            house.haunted = True
            reward = 80 + int(house.haunt_required * 45)
            reward *= 1 if quick_mode else 2
            if self.current_event == "eclipse":
                reward = int(reward * 1.25)
            gain_score, mult = self.player.add_score(int(reward * self.player.power_bonus))
            essence_gain = max(1, gain_score // 75)
            self.essence_run += essence_gain

            self.spawn_particles(house.x, house.y - house.h * 0.5, CYAN, 28, 130)
            self.spawn_particles(house.x, house.y - house.h * 0.5, PURPLE, 24, 110)
            self.floating.append(FloatingText(house.x, house.y - house.h - 10, f"+{gain_score}", YELLOW))
            self.floating.append(FloatingText(house.x, house.y - house.h - 34, f"ESSENCE +{essence_gain}", GREEN))
            self.floating.append(FloatingText(house.x, house.y - house.h - 58, f"x{mult:.1f}", CYAN))
            self.cam_shake = max(self.cam_shake, 8)

    def handle_player_actions(self, dt, keys, keydowns):
        self.player.haunting = False

        if pygame.K_LSHIFT in keydowns or pygame.K_RSHIFT in keydowns:
            if self.player.cast_dash():
                self.cam_shake = max(self.cam_shake, 4)

        if pygame.K_q in keydowns and self.player.cast_teleport():
            self.spawn_particles(self.player.x, self.player.y, CYAN, 22, 140)
            self.cam_shake = max(self.cam_shake, 6)

        if pygame.K_e in keydowns and self.player.cast_invis():
            self.spawn_particles(self.player.x, self.player.y, GREEN, 18, 100)

        if pygame.K_f in keydowns and self.player.can_use("cd_aoe", 42):
            self.player.energy -= 42
            self.player.cd_aoe = 8.0
            for h in self.houses:
                if not h.haunted and dist(self.player.x, self.player.y, h.x, h.y - h.h * 0.5) < 230:
                    h.haunt_progress += 0.7 * self.player.haunt_bonus
            self.spawn_particles(self.player.x, self.player.y, PURPLE, 45, 170)
            self.floating.append(FloatingText(self.player.x, self.player.y - 42, "AOE HAUNT", PURPLE))

        target = self.nearest_house()
        if target and (keys[pygame.K_SPACE] or keys[pygame.K_RETURN]):
            self.player.haunting = True
            quick_mode = not keys[pygame.K_LCTRL]
            self.haunt_house(target, dt, quick_mode)

    def handle_enemies(self, dt):
        for hunter in self.hunters:
            hunter.update(dt, self.player.x, self.player.y, self.difficulty)
            if dist(self.player.x, self.player.y, hunter.x, hunter.y) < self.player.radius + 20 and hunter.attack_cd <= 0:
                hunter.attack_cd = 1.1
                if self.player.damage():
                    self.spawn_particles(self.player.x, self.player.y, RED, 20, 145)
                    self.floating.append(FloatingText(self.player.x, self.player.y - 36, "HUNTER HIT", RED))
                    self.cam_shake = max(self.cam_shake, 10)

        for wiz in self.wizards:
            wiz.update(dt, self.difficulty)
            d = dist(self.player.x, self.player.y, wiz.x, wiz.y)
            in_zone = d < wiz.range_radius
            if in_zone and wiz.zone_timer > 0 and random.random() < 0.09:
                self.player.energy = max(0, self.player.energy - (8 + self.difficulty))
                self.floating.append(FloatingText(self.player.x, self.player.y - 20, "ENERGY DRAIN", BLUE))
            if in_zone and self.player.invis_timer <= 0 and random.random() < 0.02:
                if self.player.damage():
                    self.spawn_particles(self.player.x, self.player.y, BLUE, 16, 120)
                    self.floating.append(FloatingText(self.player.x, self.player.y - 36, "HEX", BLUE))

    def cleanup(self):
        left = self.cam_x - 300
        right = self.cam_x + WIDTH + 5000
        self.houses = [h for h in self.houses if left < h.x < right]
        self.hunters = [h for h in self.hunters if left < h.x < right]
        self.wizards = [w for w in self.wizards if left < w.x < right]

    def update(self, dt, keydowns):
        if self.paused or self.game_over:
            return

        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)

        self.time_survived += dt
        self.best_dist = max(self.best_dist, int(self.player.x))
        self.difficulty = 1.0 + self.best_dist / 2800.0

        if self.current_event == "eclipse":
            self.player.energy = min(self.player.energy_max, self.player.energy + dt * 7)

        self.handle_player_actions(dt, keys, keydowns)

        for house in self.houses:
            house.update(dt)
        self.handle_enemies(dt)

        self.generate_until(self.player.x + WIDTH * 3)

        self.particles = [p for p in self.particles if p.update(dt)]
        self.floating = [f for f in self.floating if f.update(dt)]

        if random.random() < 0.14:
            self.particles.append(Particle(self.cam_x + WIDTH + random.randint(0, 100), random.randint(80, GROUND_Y - 75), random.uniform(-24, -8), random.uniform(-8, 8), random.uniform(1.7, 3.2), random.uniform(1.7, 3.2), (130, 130, 180), random.uniform(1, 2.4)))

        self.cam_x = lerp(self.cam_x, max(0, self.player.x - WIDTH * 0.26), 0.12)
        if self.cam_shake > 0:
            self.cam_shake = max(0, self.cam_shake - dt * 22)

        self.cleanup()

        if self.player.hp <= 0:
            self.game_over = True
            self.meta.essence_bank += self.essence_run
            self.meta.save()

    # --------------------------- DRAW ---------------------------
    def draw_background(self, surface):
        surface.fill(NIGHT)
        pygame.draw.circle(surface, (238, 238, 205), (1030, 110), 50)
        pygame.draw.circle(surface, NIGHT, (1048, 96), 39)

        for i in range(42):
            sx = (i * 123) % WIDTH
            sy = (i * 77) % (GROUND_Y - 210)
            pygame.draw.circle(surface, WHITE, (sx, sy), 1)

        for i in range(-2, 8):
            x = (i * 260) - int(self.cam_x * 0.15) % 260
            pygame.draw.ellipse(surface, (28, 38, 56), (x, GROUND_Y - 70, 320, 150))
        for i in range(-2, 8):
            x = (i * 220) - int(self.cam_x * 0.30) % 220
            pygame.draw.ellipse(surface, (34, 48, 70), (x, GROUND_Y - 42, 260, 122))

        ground = (32, 54, 42) if self.current_event != "eclipse" else (45, 35, 65)
        pygame.draw.rect(surface, ground, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
        pygame.draw.rect(surface, (26, 42, 30), (0, GROUND_Y + 16, WIDTH, HEIGHT - GROUND_Y))

    def draw_world(self, surface):
        shake_x = random.randint(-int(self.cam_shake), int(self.cam_shake)) if self.cam_shake > 0 else 0
        shake_y = random.randint(-int(self.cam_shake), int(self.cam_shake)) if self.cam_shake > 0 else 0
        cam = self.cam_x - shake_x

        mist = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(4):
            pygame.draw.ellipse(mist, (140, 140, 180, 18), (-100 + i * 340 - int(cam * (0.08 + i * 0.01)) % 200, 115 + i * 85, 420, 90))
        surface.blit(mist, (0, shake_y))

        for house in self.houses:
            house.draw(surface, cam)
        for h in self.hunters:
            h.draw(surface, cam)
        for w in self.wizards:
            w.draw(surface, cam)
        for p in self.particles:
            p.draw(surface, cam)

        self.player.draw(surface, cam)

        if self.player.haunting:
            target = self.nearest_house()
            if target:
                sx1, sy1 = world_to_screen(self.player.x, cam), int(self.player.y)
                sx2, sy2 = world_to_screen(target.x, cam), int(target.y - target.h * 0.55)
                for _ in range(3):
                    off = random.randint(-4, 4)
                    pygame.draw.line(surface, (185, 125, 255), (sx1, sy1 + off), (sx2, sy2 + off), 2)

        for ft in self.floating:
            ft.draw(surface, cam)

    def draw_hud(self, surface):
        panel = pygame.Surface((520, 155), pygame.SRCALPHA)
        panel.fill((12, 12, 22, 180))
        surface.blit(panel, (16, 14))
        pygame.draw.rect(surface, (90, 90, 122), (16, 14, 520, 155), 2, border_radius=12)

        draw_text(surface, f"Score: {self.player.score}", FONT_MD, YELLOW, 30, 24)
        draw_text(surface, f"Combo x{1.0 + min(self.player.combo * 0.08, 2.0):.1f}", FONT_SM, CYAN, 30, 60)
        draw_text(surface, f"Health: {self.player.hp}/{self.player.max_hp}", FONT_SM, WHITE, 30, 86)
        draw_text(surface, f"Energy: {int(self.player.energy)}/{self.player.energy_max}", FONT_SM, GREEN, 30, 108)
        draw_text(surface, f"Essence(run): {self.essence_run}", FONT_SM, ORANGE, 30, 130)

        draw_text(surface, f"Event: {self.current_event}", FONT_SM, ORANGE, 280, 60)
        draw_text(surface, f"Diff: {self.difficulty:.1f}", FONT_SM, WHITE, 280, 86)
        draw_text(surface, f"Dist: {self.best_dist}m", FONT_SM, WHITE, 280, 108)

        bw = 190
        pygame.draw.rect(surface, (34, 48, 40), (330, 130, bw, 14), border_radius=6)
        fill = int((self.player.energy / self.player.energy_max) * bw)
        pygame.draw.rect(surface, (60, 220, 130), (330, 130, fill, 14), border_radius=6)

        tips = "SPACE haunt | LCTRL+SPACE deep haunt | SHIFT dash | Q teleport | E invis | F AOE | ESC pause"
        draw_text(surface, tips, FONT_SM, (190, 195, 215), 16, HEIGHT - 34)

    def draw_pause(self, surface):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 130))
        surface.blit(ov, (0, 0))
        draw_text(surface, "PAUSED", FONT_LG, WHITE, WIDTH // 2, HEIGHT // 2 - 20, center=True)

    def draw_game_over(self, surface):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        surface.blit(ov, (0, 0))
        draw_text(surface, "GAME OVER", FONT_LG, RED, WIDTH // 2, HEIGHT // 2 - 120, center=True)
        draw_text(surface, f"Final score: {self.player.score}", FONT_MD, YELLOW, WIDTH // 2, HEIGHT // 2 - 40, center=True)
        draw_text(surface, f"Distance: {self.best_dist}m", FONT_MD, WHITE, WIDTH // 2, HEIGHT // 2 + 4, center=True)
        draw_text(surface, f"Essence gained: {self.essence_run}", FONT_MD, GREEN, WIDTH // 2, HEIGHT // 2 + 48, center=True)
        draw_text(surface, "Press R to restart | U to upgrade", FONT_MD, CYAN, WIDTH // 2, HEIGHT // 2 + 122, center=True)

    def draw(self, surface):
        self.draw_background(surface)
        self.draw_world(surface)
        self.draw_hud(surface)
        if self.paused and not self.game_over:
            self.draw_pause(surface)
        if self.game_over:
            self.draw_game_over(surface)


# ============================================================
# MENU + UPGRADE
# ============================================================
def draw_menu(surface, blink):
    surface.fill((10, 10, 24))
    pygame.draw.circle(surface, (240, 240, 205), (960, 110), 56)
    pygame.draw.circle(surface, (10, 10, 24), (978, 98), 44)

    draw_text(surface, "GHOST HAUNTER", FONT_LG, CYAN, WIDTH // 2, 150, center=True)
    draw_text(surface, "Strategic infinite haunting in procedural houses", FONT_MD, WHITE, WIDTH // 2, 220, center=True)
    draw_text(surface, "Use risk/reward, abilities and upgrades to survive deeper worlds.", FONT_SM, (190, 195, 210), WIDTH // 2, 260, center=True)

    if int(blink * 2) % 2 == 0:
        draw_text(surface, "Press ENTER to start", FONT_MD, GREEN, WIDTH // 2, 560, center=True)
    draw_text(surface, "Press U for upgrades", FONT_MD, ORANGE, WIDTH // 2, 600, center=True)


def draw_upgrade_menu(surface, meta: MetaProgress, selected):
    surface.fill((12, 10, 28))
    draw_text(surface, "UPGRADES", FONT_LG, CYAN, WIDTH // 2, 120, center=True)
    draw_text(surface, f"Banked Essence: {meta.essence_bank}", FONT_MD, GREEN, WIDTH // 2, 190, center=True)

    items = [
        ("speed", "Move Speed", meta.speed_level),
        ("haunt", "Haunting Speed", meta.haunt_level),
        ("power", "Ability/Score Power", meta.power_level),
    ]

    for idx, (key, name, level) in enumerate(items):
        y = 270 + idx * 110
        active = idx == selected
        col = YELLOW if active else WHITE
        cost = meta.cost(key)
        draw_text(surface, f"{name}", FONT_MD, col, WIDTH // 2, y, center=True)
        draw_text(surface, f"Level: {level}  |  Cost: {cost} essence", FONT_SM, (190, 195, 210), WIDTH // 2, y + 34, center=True)

    draw_text(surface, "UP/DOWN select | ENTER buy | ESC back", FONT_SM, (200, 200, 220), WIDTH // 2, HEIGHT - 70, center=True)


def try_buy_upgrade(meta: MetaProgress, key):
    cost = meta.cost(key)
    if meta.essence_bank >= cost:
        meta.essence_bank -= cost
        setattr(meta, f"{key}_level", getattr(meta, f"{key}_level") + 1)
        meta.save()
        return True
    return False


# ============================================================
# MAIN LOOP
# ============================================================
def main():
    meta = MetaProgress.load()
    game = Game(meta)
    state = "menu"
    blink = 0.0
    upgrade_idx = 0

    while True:
        dt = clock.tick(FPS) / 1000.0
        blink += dt
        keydowns = []

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                keydowns.append(event.key)

                if state == "menu":
                    if event.key == pygame.K_RETURN:
                        game.reset()
                        state = "playing"
                    if event.key == pygame.K_u:
                        state = "upgrade"

                elif state == "playing":
                    if event.key == pygame.K_ESCAPE:
                        game.paused = not game.paused
                    if game.game_over and event.key == pygame.K_r:
                        game.reset()
                    if game.game_over and event.key == pygame.K_u:
                        state = "upgrade"

                elif state == "upgrade":
                    if event.key == pygame.K_ESCAPE:
                        state = "menu"
                    if event.key == pygame.K_UP:
                        upgrade_idx = (upgrade_idx - 1) % 3
                    if event.key == pygame.K_DOWN:
                        upgrade_idx = (upgrade_idx + 1) % 3
                    if event.key == pygame.K_RETURN:
                        key = ["speed", "haunt", "power"][upgrade_idx]
                        try_buy_upgrade(meta, key)

        if state == "menu":
            draw_menu(screen, blink)
        elif state == "upgrade":
            draw_upgrade_menu(screen, meta, upgrade_idx)
        elif state == "playing":
            game.update(dt, keydowns)
            game.draw(screen)

        pygame.display.flip()


if __name__ == "__main__":
    main()
