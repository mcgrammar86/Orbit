"""
Orbit - A gravitational attractor game.

Launch your spaceship and use the gravity of planets to reach the goal.
Click and drag from the spaceship to set launch direction and power,
then release to launch. Reach the green goal zone to advance levels.

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
TRAIL_COLOR = (100, 180, 255)

G = 800  # gravitational constant (tuned for fun, not physics)

MAX_TRAIL = 600


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def dist(ax, ay, bx, by):
    return math.hypot(bx - ax, by - ay)


# ---------------------------------------------------------------------------
# Game objects
# ---------------------------------------------------------------------------
class Body:
    """A massive gravitational attractor (planet / star)."""

    def __init__(self, x, y, mass, radius, color=YELLOW):
        self.x = x
        self.y = y
        self.mass = mass
        self.radius = radius
        self.color = color

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        # subtle glow
        glow = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(
            glow,
            (*self.color, 30),
            (self.radius * 2, self.radius * 2),
            self.radius * 2,
        )
        surface.blit(
            glow, (int(self.x) - self.radius * 2, int(self.y) - self.radius * 2)
        )


class Goal:
    """Target zone the spaceship must reach."""

    def __init__(self, x, y, radius=24):
        self.x = x
        self.y = y
        self.radius = radius
        self._pulse = 0

    def draw(self, surface):
        self._pulse = (self._pulse + 2) % 360
        r = self.radius + 4 * math.sin(math.radians(self._pulse))
        pygame.draw.circle(surface, GREEN, (int(self.x), int(self.y)), int(r), 3)
        pygame.draw.circle(surface, GREEN, (int(self.x), int(self.y)), int(r * 0.5))

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

    def update(self, bodies):
        if not self.launched or not self.alive:
            return

        # accumulate gravity from all bodies
        ax, ay = 0.0, 0.0
        for body in bodies:
            dx = body.x - self.x
            dy = body.y - self.y
            r = math.hypot(dx, dy)
            if r < body.radius:
                self.alive = False
                return
            force = G * body.mass / (r * r)
            ax += force * dx / r
            ay += force * dy / r

        self.vx += ax * DT
        self.vy += ay * DT
        self.x += self.vx * DT
        self.y += self.vy * DT

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
        # trail
        if len(self.trail) > 1:
            for i in range(1, len(self.trail)):
                alpha = int(255 * i / len(self.trail))
                color = (
                    TRAIL_COLOR[0],
                    TRAIL_COLOR[1],
                    TRAIL_COLOR[2],
                    max(10, alpha),
                )
                start = (int(self.trail[i - 1][0]), int(self.trail[i - 1][1]))
                end = (int(self.trail[i][0]), int(self.trail[i][1]))
                trail_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                pygame.draw.line(trail_surf, color, start, end, 2)
                surface.blit(trail_surf, (0, 0))

        if not self.alive:
            return

        # ship body
        angle = math.atan2(self.vy, self.vx) if self.launched else 0
        size = 10
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        pts = [
            (self.x + size * cos_a, self.y + size * sin_a),
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


# ---------------------------------------------------------------------------
# Levels
# ---------------------------------------------------------------------------
def make_levels():
    levels = []

    # Level 1 – single planet, straight-ish shot
    levels.append(
        {
            "bodies": [Body(450, 350, 50, 28, YELLOW)],
            "ship": (100, 350),
            "goal": (800, 350),
            "hint": "Aim past the planet and let gravity curve your path.",
        }
    )

    # Level 2 – two planets forming a corridor
    levels.append(
        {
            "bodies": [
                Body(350, 250, 40, 24, ORANGE),
                Body(550, 450, 40, 24, ORANGE),
            ],
            "ship": (80, 600),
            "goal": (820, 100),
            "hint": "Thread the gap between the two planets.",
        }
    )

    # Level 3 – slingshot around a big star
    levels.append(
        {
            "bodies": [Body(450, 350, 120, 40, RED)],
            "ship": (100, 600),
            "goal": (100, 100),
            "hint": "Use the star's gravity to slingshot around it.",
        }
    )

    # Level 4 – three-body maze
    levels.append(
        {
            "bodies": [
                Body(300, 200, 35, 22, BLUE),
                Body(600, 350, 50, 28, YELLOW),
                Body(300, 500, 35, 22, BLUE),
            ],
            "ship": (60, 350),
            "goal": (840, 350),
            "hint": "Navigate the gravitational maze.",
        }
    )

    # Level 5 – tight orbit required
    levels.append(
        {
            "bodies": [
                Body(450, 350, 80, 34, RED),
                Body(200, 150, 30, 20, ORANGE),
                Body(700, 550, 30, 20, ORANGE),
            ],
            "ship": (80, 650),
            "goal": (820, 50),
            "hint": "A tricky trajectory through heavy gravity.",
        }
    )

    return levels


# ---------------------------------------------------------------------------
# Prediction (dotted trajectory preview)
# ---------------------------------------------------------------------------
def predict_trajectory(ship_x, ship_y, vx, vy, bodies, steps=300):
    """Simulate future positions for a trajectory preview."""
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

    if state == "aiming":
        msg = font.render("Click & drag from ship to launch", True, GREY)
        surface.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT - 30))
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
    surface.blit(hint_surf, (10, 40))


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
    import random

    random.seed(42)
    stars = [(random.randint(0, WIDTH - 1), random.randint(0, HEIGHT - 1), random.randint(80, 255)) for _ in range(200)]

    levels = make_levels()
    level_idx = 0

    def load_level(idx):
        lv = levels[idx]
        ship = Spaceship(*lv["ship"])
        goal = Goal(*lv["goal"])
        return lv["bodies"], ship, goal, lv["hint"]

    bodies, ship, goal, hint = load_level(level_idx)

    dragging = False
    drag_start = (0, 0)
    state = "aiming"  # aiming | flying | win | dead | done

    running = True
    while running:
        clock.tick(FPS)

        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_r:
                    ship.reset()
                    state = "aiming"
                elif event.key == pygame.K_n:
                    level_idx = (level_idx + 1) % len(levels)
                    bodies, ship, goal, hint = load_level(level_idx)
                    state = "aiming"

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == "win":
                    level_idx += 1
                    if level_idx >= len(levels):
                        state = "done"
                    else:
                        bodies, ship, goal, hint = load_level(level_idx)
                        state = "aiming"
                elif state in ("dead", "done"):
                    if state == "done":
                        level_idx = 0
                    ship.reset() if state == "dead" else None
                    bodies, ship, goal, hint = load_level(level_idx)
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

        # ---- update ----
        if state == "flying":
            ship.update(bodies)
            if not ship.alive:
                state = "dead"
            elif goal.contains(ship.x, ship.y):
                state = "win"

        # ---- draw ----
        screen.fill(BLACK)
        draw_stars(screen, stars)

        for body in bodies:
            body.draw(screen)

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

            # trajectory preview
            pvx = power * math.cos(angle)
            pvy = power * math.sin(angle)
            pts = predict_trajectory(ship.x, ship.y, pvx, pvy, bodies)
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
