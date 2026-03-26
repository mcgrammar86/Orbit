"""
Orbit - A gravitational attractor game.

Launch your spaceship and use gravity, repulsion, moving planets, and
moving goals to navigate an increasingly chaotic cosmos.  Time your
launch carefully — the universe doesn't wait for you!

Controls:
  - Click & drag from the ship to aim and set power
  - Release to launch
  - Press R to reset the current level
  - Press N to skip to the next level
  - Press ESC or Q to quit

Requires: pygame  (pip install pygame)
"""

import sys
import math
import random
import pygame

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 900, 700
FPS = 60
DT = 0.4  # simulation time-step per frame

# Colours
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 220, 60)
RED = (220, 50, 50)
GREEN = (60, 220, 80)
BLUE = (80, 140, 255)
ORANGE = (255, 160, 40)
GREY = (120, 120, 120)
DARK_GREY = (40, 40, 50)
CYAN = (60, 220, 240)
MAGENTA = (200, 60, 220)
PURPLE = (140, 80, 220)
TRAIL_COLOR = (100, 180, 255)

G = 800  # gravitational constant (tuned for fun, not physics)
MAX_TRAIL = 600


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def dist(ax, ay, bx, by):
    return math.hypot(bx - ax, by - ay)


def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# ---------------------------------------------------------------------------
# Motion paths — reusable for any moving object
# ---------------------------------------------------------------------------
class LinearPath:
    """Bounce back and forth between two points."""

    def __init__(self, x1, y1, x2, y2, speed):
        self.x1, self.y1 = float(x1), float(y1)
        self.x2, self.y2 = float(x2), float(y2)
        self.speed = speed  # full traversals per second
        self._t = 0.0

    def update(self):
        self._t += self.speed / FPS
        if self._t > 1.0:
            self._t -= 1.0

    def pos(self):
        # triangle wave: 0→1→0 over one period
        t = 1.0 - abs(2.0 * self._t - 1.0)
        return (
            self.x1 + (self.x2 - self.x1) * t,
            self.y1 + (self.y2 - self.y1) * t,
        )


class CircularPath:
    """Orbit around a centre point."""

    def __init__(self, cx, cy, radius, speed, phase=0.0):
        self.cx, self.cy = float(cx), float(cy)
        self.radius = float(radius)
        self.speed = speed  # revolutions per second
        self._angle = phase

    def update(self):
        self._angle += self.speed * 2 * math.pi / FPS

    def pos(self):
        return (
            self.cx + self.radius * math.cos(self._angle),
            self.cy + self.radius * math.sin(self._angle),
        )


# ---------------------------------------------------------------------------
# Game objects
# ---------------------------------------------------------------------------
class Body:
    """A gravitational attractor or repulsor.

    Positive mass = attractor (pulls), negative mass = repulsor (pushes).
    Optionally moves along a path.
    """

    def __init__(self, x, y, mass, radius, color=YELLOW, path=None):
        self.home_x = x
        self.home_y = y
        self.x = float(x)
        self.y = float(y)
        self.mass = mass
        self.radius = radius
        self.color = color
        self.path = path
        self.is_repulsor = mass < 0
        self._ring_phase = 0.0

    def reset(self):
        self.x = float(self.home_x)
        self.y = float(self.home_y)
        if self.path:
            self.path._t = 0.0 if hasattr(self.path, "_t") else None
            if hasattr(self.path, "_angle"):
                self.path._angle = getattr(self.path, "_initial_phase", 0.0)

    def update(self):
        if self.path:
            self.path.update()
            self.x, self.y = self.path.pos()

    def draw(self, surface):
        ix, iy = int(self.x), int(self.y)

        if self.is_repulsor:
            # pulsing repulsion rings
            self._ring_phase = (self._ring_phase + 3) % 360
            for i in range(3):
                ring_r = self.radius + 6 + 8 * i + 4 * math.sin(
                    math.radians(self._ring_phase + i * 120)
                )
                alpha = max(20, 120 - 30 * i)
                ring_surf = pygame.Surface(
                    (int(ring_r * 2) + 4, int(ring_r * 2) + 4), pygame.SRCALPHA
                )
                pygame.draw.circle(
                    ring_surf,
                    (*self.color, alpha),
                    (int(ring_r) + 2, int(ring_r) + 2),
                    int(ring_r),
                    2,
                )
                surface.blit(ring_surf, (ix - int(ring_r) - 2, iy - int(ring_r) - 2))

        # glow
        glow_size = self.radius * 4
        glow = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
        pygame.draw.circle(
            glow,
            (*self.color, 30),
            (glow_size // 2, glow_size // 2),
            glow_size // 2,
        )
        surface.blit(glow, (ix - glow_size // 2, iy - glow_size // 2))

        # body
        pygame.draw.circle(surface, self.color, (ix, iy), self.radius)

        # movement indicator arrow
        if self.path:
            pygame.draw.circle(surface, WHITE, (ix, iy), self.radius + 3, 1)


class Obstacle:
    """A deadly zone — no gravity, just death on contact. Optionally moves."""

    def __init__(self, x, y, radius, path=None, color=RED):
        self.home_x = x
        self.home_y = y
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.path = path
        self.color = color
        self._spin = 0.0

    def reset(self):
        self.x = float(self.home_x)
        self.y = float(self.home_y)

    def update(self):
        if self.path:
            self.path.update()
            self.x, self.y = self.path.pos()
        self._spin += 2

    def hits(self, sx, sy):
        return dist(self.x, self.y, sx, sy) < self.radius

    def draw(self, surface):
        ix, iy = int(self.x), int(self.y)
        r = self.radius
        # draw an X-shaped hazard marker
        ang = math.radians(self._spin)
        for offset in [0, math.pi / 2]:
            a = ang + offset
            x1 = ix + int(r * 0.8 * math.cos(a))
            y1 = iy + int(r * 0.8 * math.sin(a))
            x2 = ix - int(r * 0.8 * math.cos(a))
            y2 = iy - int(r * 0.8 * math.sin(a))
            pygame.draw.line(surface, self.color, (x1, y1), (x2, y2), 3)
        pygame.draw.circle(surface, self.color, (ix, iy), r, 2)
        # danger glow
        glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.color, 20), (r * 2, r * 2), r * 2)
        surface.blit(glow, (ix - r * 2, iy - r * 2))


class Goal:
    """Target zone the spaceship must reach. Optionally moves."""

    def __init__(self, x, y, radius=24, path=None):
        self.home_x = x
        self.home_y = y
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.path = path
        self._pulse = 0

    def reset(self):
        self.x = float(self.home_x)
        self.y = float(self.home_y)

    def update(self):
        if self.path:
            self.path.update()
            self.x, self.y = self.path.pos()

    def draw(self, surface):
        self._pulse = (self._pulse + 2) % 360
        r = self.radius + 4 * math.sin(math.radians(self._pulse))
        ix, iy = int(self.x), int(self.y)
        pygame.draw.circle(surface, GREEN, (ix, iy), int(r), 3)
        pygame.draw.circle(surface, GREEN, (ix, iy), int(r * 0.5))
        if self.path:
            # motion trail hint
            pygame.draw.circle(surface, (40, 150, 60), (ix, iy), int(r + 6), 1)

    def contains(self, x, y):
        return dist(self.x, self.y, x, y) <= self.radius


class Spaceship:
    """Player-controlled spaceship."""

    def __init__(self, x, y):
        self.start_x = x
        self.start_y = y
        self.reset()

    def reset(self):
        self.x = self.start_x
        self.y = self.start_y
        self.vx = 0.0
        self.vy = 0.0
        self.launched = False
        self.alive = True
        self.trail = []

    def launch(self, vx, vy):
        self.vx = vx
        self.vy = vy
        self.launched = True

    def update(self, bodies, obstacles):
        if not self.launched or not self.alive:
            return

        # accumulate gravity / repulsion from all bodies
        ax, ay = 0.0, 0.0
        for body in bodies:
            dx = body.x - self.x
            dy = body.y - self.y
            r = math.hypot(dx, dy)
            if r < body.radius:
                self.alive = False
                return
            force = G * body.mass / (r * r)  # negative mass → repulsion
            ax += force * dx / r
            ay += force * dy / r

        self.vx += ax * DT
        self.vy += ay * DT
        self.x += self.vx * DT
        self.y += self.vy * DT

        # obstacle collision
        for obs in obstacles:
            if obs.hits(self.x, self.y):
                self.alive = False
                return

        self.trail.append((self.x, self.y))
        if len(self.trail) > MAX_TRAIL:
            self.trail.pop(0)

        # out of bounds
        margin = 80
        if (
            self.x < -margin
            or self.x > WIDTH + margin
            or self.y < -margin
            or self.y > HEIGHT + margin
        ):
            self.alive = False

    def draw(self, surface):
        # efficient trail rendering — single alpha surface
        if len(self.trail) > 1:
            trail_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            n = len(self.trail)
            for i in range(1, n):
                alpha = max(10, int(255 * i / n))
                color = (*TRAIL_COLOR, alpha)
                start = (int(self.trail[i - 1][0]), int(self.trail[i - 1][1]))
                end = (int(self.trail[i][0]), int(self.trail[i][1]))
                pygame.draw.line(trail_surf, color, start, end, 2)
            surface.blit(trail_surf, (0, 0))

        if not self.alive:
            return

        # ship triangle
        angle = math.atan2(self.vy, self.vx) if self.launched else 0
        size = 10
        pts = [
            (self.x + size * math.cos(angle), self.y + size * math.sin(angle)),
            (
                self.x + size * 0.6 * math.cos(angle + 2.5),
                self.y + size * 0.6 * math.sin(angle + 2.5),
            ),
            (
                self.x + size * 0.6 * math.cos(angle - 2.5),
                self.y + size * 0.6 * math.sin(angle - 2.5),
            ),
        ]
        pygame.draw.polygon(surface, WHITE, [(int(px), int(py)) for px, py in pts])

        # engine glow when launched
        if self.launched:
            glow_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (100, 180, 255, 60), (10, 10), 10)
            surface.blit(glow_surf, (int(self.x) - 10, int(self.y) - 10))


# ---------------------------------------------------------------------------
# Levels — 10 levels showcasing all mechanics
# ---------------------------------------------------------------------------
def make_levels():
    levels = []

    # -- Level 1: Tutorial — single attractor, static goal
    levels.append(
        {
            "bodies": [Body(450, 350, 50, 28, YELLOW)],
            "obstacles": [],
            "ship": (100, 350),
            "goal_args": {"x": 800, "y": 350},
            "hint": "Aim past the planet and let gravity curve your path.",
        }
    )

    # -- Level 2: Introduction to repulsors
    levels.append(
        {
            "bodies": [
                Body(450, 350, -40, 22, CYAN),  # repulsor
                Body(450, 180, 30, 20, ORANGE),
            ],
            "obstacles": [],
            "ship": (80, 350),
            "goal_args": {"x": 820, "y": 350},
            "hint": "The cyan body REPELS your ship — use it as a boost!",
        }
    )

    # -- Level 3: Moving goal — timing matters
    levels.append(
        {
            "bodies": [Body(450, 350, 60, 30, YELLOW)],
            "obstacles": [],
            "ship": (100, 600),
            "goal_args": {
                "x": 750,
                "y": 150,
                "path": LinearPath(750, 100, 750, 600, 0.3),
            },
            "hint": "The goal moves up and down — time your launch!",
        }
    )

    # -- Level 4: Moving attractor — slingshot timing
    levels.append(
        {
            "bodies": [
                Body(
                    450,
                    350,
                    70,
                    30,
                    YELLOW,
                    path=LinearPath(350, 350, 550, 350, 0.25),
                ),
            ],
            "obstacles": [],
            "ship": (100, 600),
            "goal_args": {"x": 100, "y": 100},
            "hint": "The planet slides back and forth — time your slingshot.",
        }
    )

    # -- Level 5: Obstacles introduced
    levels.append(
        {
            "bodies": [
                Body(350, 350, 45, 24, ORANGE),
                Body(600, 350, 45, 24, ORANGE),
            ],
            "obstacles": [
                Obstacle(475, 200, 18),
                Obstacle(475, 500, 18),
            ],
            "ship": (80, 350),
            "goal_args": {"x": 820, "y": 350},
            "hint": "Red hazards destroy your ship — thread the needle.",
        }
    )

    # -- Level 6: Moving obstacles — sweeping danger
    levels.append(
        {
            "bodies": [Body(450, 350, 80, 34, RED)],
            "obstacles": [
                Obstacle(
                    450,
                    180,
                    16,
                    path=LinearPath(300, 180, 600, 180, 0.4),
                ),
                Obstacle(
                    450,
                    520,
                    16,
                    path=LinearPath(600, 520, 300, 520, 0.4),
                ),
            ],
            "ship": (100, 350),
            "goal_args": {"x": 800, "y": 350},
            "hint": "Sweeping hazards — watch their pattern before launching.",
        }
    )

    # -- Level 7: Repulsor gauntlet
    levels.append(
        {
            "bodies": [
                Body(300, 250, -30, 18, CYAN),
                Body(450, 450, -30, 18, CYAN),
                Body(600, 250, -30, 18, CYAN),
                Body(450, 100, 35, 22, PURPLE),
            ],
            "obstacles": [],
            "ship": (60, 500),
            "goal_args": {"x": 840, "y": 100},
            "hint": "Repulsor gauntlet — bounce between the cyan fields.",
        }
    )

    # -- Level 8: Orbiting obstacles around a planet
    levels.append(
        {
            "bodies": [Body(450, 350, 90, 36, YELLOW)],
            "obstacles": [
                Obstacle(
                    450,
                    250,
                    14,
                    path=CircularPath(450, 350, 100, 0.6),
                ),
                Obstacle(
                    450,
                    450,
                    14,
                    path=CircularPath(450, 350, 100, 0.6, math.pi),
                ),
            ],
            "ship": (80, 600),
            "goal_args": {"x": 820, "y": 100},
            "hint": "Hazards orbit the planet — find a gap!",
        }
    )

    # -- Level 9: Moving everything — attractor, goal, and obstacles
    levels.append(
        {
            "bodies": [
                Body(
                    300,
                    350,
                    55,
                    26,
                    ORANGE,
                    path=LinearPath(300, 250, 300, 450, 0.3),
                ),
                Body(600, 350, -35, 20, CYAN),
            ],
            "obstacles": [
                Obstacle(
                    450,
                    350,
                    15,
                    path=LinearPath(450, 200, 450, 500, 0.5),
                ),
            ],
            "ship": (60, 350),
            "goal_args": {
                "x": 820,
                "y": 200,
                "path": LinearPath(820, 150, 820, 550, 0.35),
            },
            "hint": "Everything moves — watch, plan, then fire!",
        }
    )

    # -- Level 10: The gauntlet — all mechanics combined
    levels.append(
        {
            "bodies": [
                Body(
                    350,
                    300,
                    60,
                    28,
                    YELLOW,
                    path=CircularPath(350, 350, 50, 0.2),
                ),
                Body(600, 400, -40, 22, CYAN),
                Body(200, 150, 30, 18, PURPLE),
            ],
            "obstacles": [
                Obstacle(
                    480,
                    350,
                    14,
                    path=LinearPath(460, 200, 460, 500, 0.45),
                ),
                Obstacle(
                    700,
                    300,
                    14,
                    path=CircularPath(700, 350, 60, 0.5),
                ),
            ],
            "ship": (60, 600),
            "goal_args": {
                "x": 830,
                "y": 80,
                "path": LinearPath(780, 80, 830, 200, 0.25),
            },
            "hint": "The ultimate challenge — gravity, repulsion, obstacles, all moving.",
        }
    )

    return levels


def build_level(level_data):
    """Instantiate live objects from a level dict."""
    bodies = level_data["bodies"]
    obstacles = level_data["obstacles"]
    ship = Spaceship(*level_data["ship"])
    gargs = level_data["goal_args"]
    goal = Goal(gargs["x"], gargs["y"], path=gargs.get("path"))
    hint = level_data["hint"]
    return bodies, obstacles, ship, goal, hint


# ---------------------------------------------------------------------------
# Prediction (dotted trajectory preview)
# ---------------------------------------------------------------------------
def predict_trajectory(ship_x, ship_y, vx, vy, bodies, obstacles, steps=300):
    """Simulate future positions for a trajectory preview.

    NOTE: prediction uses current body/obstacle positions (snapshot) since
    moving objects make the future truly unpredictable — that's the fun!
    """
    points = []
    x, y = float(ship_x), float(ship_y)
    svx, svy = float(vx), float(vy)
    for _ in range(steps):
        ax, ay = 0.0, 0.0
        hit = False
        for body in bodies:
            dx = body.x - x
            dy = body.y - y
            r = math.hypot(dx, dy)
            if r < body.radius:
                hit = True
                break
            force = G * body.mass / (r * r)
            ax += force * dx / r
            ay += force * dy / r
        if hit:
            break
        for obs in obstacles:
            if dist(obs.x, obs.y, x, y) < obs.radius:
                hit = True
                break
        if hit:
            break
        svx += ax * DT
        svy += ay * DT
        x += svx * DT
        y += svy * DT
        if x < -80 or x > WIDTH + 80 or y < -80 or y > HEIGHT + 80:
            break
        points.append((int(x), int(y)))
    return points


# ---------------------------------------------------------------------------
# Draw helpers
# ---------------------------------------------------------------------------
def draw_stars(surface, stars):
    for sx, sy, brightness in stars:
        c = min(255, brightness)
        surface.set_at((sx, sy), (c, c, c))


def draw_arrow(surface, start, end, color=WHITE):
    pygame.draw.line(surface, color, start, end, 2)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    head_len = 10
    for offset in [2.5, -2.5]:
        hx = end[0] - head_len * math.cos(angle + offset)
        hy = end[1] - head_len * math.sin(angle + offset)
        pygame.draw.line(surface, color, end, (int(hx), int(hy)), 2)


def draw_hud(surface, font, level_idx, total, hint, state):
    txt = font.render(f"Level {level_idx + 1} / {total}", True, WHITE)
    surface.blit(txt, (10, 10))

    # legend
    legend_y = HEIGHT - 26
    items = [
        (YELLOW, "Attractor"),
        (CYAN, "Repulsor"),
        (RED, "Hazard"),
        (GREEN, "Goal"),
    ]
    lx = 10
    for color, label in items:
        pygame.draw.circle(surface, color, (lx + 6, legend_y + 6), 6)
        lbl = font.render(label, True, GREY)
        surface.blit(lbl, (lx + 16, legend_y - 1))
        lx += 16 + lbl.get_width() + 14

    if state == "aiming":
        msg = font.render("Click & drag from ship to launch", True, GREY)
        surface.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT - 54))
    elif state == "win":
        msg = font.render("Goal reached! Click to continue.", True, GREEN)
        surface.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 20))
    elif state == "dead":
        msg = font.render("Crashed! Press R to retry.", True, RED)
        surface.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 20))
    elif state == "done":
        msg = font.render("You completed all levels!", True, GREEN)
        surface.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 20))

    hint_surf = font.render(hint, True, DARK_GREY)
    surface.blit(hint_surf, (10, 34))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Orbit – Gravity Game")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    # background stars
    random.seed(42)
    stars = [
        (random.randint(0, WIDTH - 1), random.randint(0, HEIGHT - 1), random.randint(80, 255))
        for _ in range(200)
    ]

    levels = make_levels()
    level_idx = 0

    def load_level(idx):
        return build_level(levels[idx])

    bodies, obstacles, ship, goal, hint = load_level(level_idx)

    dragging = False
    drag_start = (0, 0)
    state = "aiming"  # aiming | flying | win | dead | done
    frame_count = 0

    running = True
    while running:
        clock.tick(FPS)
        frame_count += 1

        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_r:
                    bodies, obstacles, ship, goal, hint = load_level(level_idx)
                    state = "aiming"
                elif event.key == pygame.K_n:
                    level_idx = (level_idx + 1) % len(levels)
                    bodies, obstacles, ship, goal, hint = load_level(level_idx)
                    state = "aiming"

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == "win":
                    level_idx += 1
                    if level_idx >= len(levels):
                        state = "done"
                    else:
                        bodies, obstacles, ship, goal, hint = load_level(level_idx)
                        state = "aiming"
                elif state in ("dead", "done"):
                    if state == "done":
                        level_idx = 0
                    bodies, obstacles, ship, goal, hint = load_level(level_idx)
                    state = "aiming"
                elif state == "aiming":
                    if dist(mx, my, ship.x, ship.y) < 40:
                        dragging = True
                        drag_start = (mx, my)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if dragging:
                    dragging = False
                    dx = drag_start[0] - mx
                    dy = drag_start[1] - my
                    power = min(math.hypot(dx, dy), 300) / 300 * 15
                    if power > 0.5:
                        angle = math.atan2(dy, dx)
                        ship.launch(power * math.cos(angle), power * math.sin(angle))
                        state = "flying"

        # ---- update moving objects (always, even while aiming!) ----
        for body in bodies:
            body.update()
        for obs in obstacles:
            obs.update()
        goal.update()

        # ---- update ship ----
        if state == "flying":
            ship.update(bodies, obstacles)
            if not ship.alive:
                state = "dead"
            elif goal.contains(ship.x, ship.y):
                state = "win"

        # ---- draw ----
        screen.fill(BLACK)
        draw_stars(screen, stars)

        for body in bodies:
            body.draw(screen)
        for obs in obstacles:
            obs.draw(screen)

        goal.draw(screen)
        ship.draw(screen)

        # aiming UI
        if dragging:
            dx = drag_start[0] - mx
            dy = drag_start[1] - my
            power = min(math.hypot(dx, dy), 300) / 300 * 15
            angle = math.atan2(dy, dx)
            arrow_end = (
                int(ship.x + power * 12 * math.cos(angle)),
                int(ship.y + power * 12 * math.sin(angle)),
            )
            draw_arrow(screen, (int(ship.x), int(ship.y)), arrow_end, GREEN)

            # trajectory preview (snapshot — doesn't account for movement)
            pvx = power * math.cos(angle)
            pvy = power * math.sin(angle)
            pts = predict_trajectory(ship.x, ship.y, pvx, pvy, bodies, obstacles)
            for i, pt in enumerate(pts):
                if i % 4 == 0:
                    alpha = max(30, 180 - i)
                    dot_surf = pygame.Surface((4, 4), pygame.SRCALPHA)
                    pygame.draw.circle(dot_surf, (100, 255, 100, alpha), (2, 2), 2)
                    screen.blit(dot_surf, (pt[0] - 2, pt[1] - 2))

        draw_hud(screen, font, level_idx, len(levels), hint, state)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
