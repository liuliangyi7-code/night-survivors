# LIU Liangyi (3231234) - CDT501 Lecture 9 - Night Survivors
"""main.py - the window, the drawing, the sound and the input.

This file only loads finished files from assets/ and sounds/ and draws them.
It must NOT import PIL, wave, make_assets or make_sounds: those do not work in
a web browser, and a grey page is what you get if you try.

The loop is `async def main()` with `await asyncio.sleep(0)` once per frame, so
pygbag can run the same file in a browser.
"""

import asyncio
import math
import os
import random

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame          # noqa: E402  (after the env var, on purpose)

import rules           # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(HERE, "assets")
SOUND_DIR = os.path.join(HERE, "sounds")

WIDTH = 390
HEIGHT = 700
FPS = 60

# -- colours ---------------------------------------------------------------
NIGHT = (14, 17, 30)
TEXT = (238, 240, 250)
TEXT_DIM = (150, 160, 185)
HP_RED = (230, 74, 90)
HP_BACK = (58, 26, 34)
XP_BLUE = (86, 190, 255)
XP_BACK = (20, 44, 66)
SPARK = (255, 236, 130)
CARD_BG = (26, 31, 48)
CARD_EDGE = (78, 86, 120)
CARD_EDGE_HOT = (120, 210, 255)

# The 3 big cards after a level-up stand here.
CARD_WIDTH = 330
CARD_HEIGHT = 132
CARD_TOPS = (150, 300, 450)


def load_image(name, size=None, colour=(255, 0, 255)):
    """Load assets/<name>.png. If the file is missing, use a coloured square,
    so the game still runs before make_assets.py has been used."""
    path = os.path.join(ASSET_DIR, name + ".png")
    if os.path.isfile(path):
        image = pygame.image.load(path).convert_alpha()
    else:
        width, height = size or (48, 48)
        image = pygame.Surface((width, height), pygame.SRCALPHA)
        image.fill(colour)
    if size is not None and image.get_size() != size:
        image = pygame.transform.scale(image, size)
    return image


def white_copy(image):
    """The same picture painted white, for the little flash when it is hit."""
    copy = image.copy()
    copy.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_ADD)
    return copy


def draw_text(surface, font, message, colour, position, centre=False, shadow=True):
    """Draw one line of text, with a soft shadow so it can be read anywhere."""
    picture = font.render(message, True, colour)
    rect = picture.get_rect()
    if centre:
        rect.center = position
    else:
        rect.topleft = position
    if shadow:
        dark = font.render(message, True, (0, 0, 0))
        dark.set_alpha(130)
        surface.blit(dark, (rect.x + 1, rect.y + 2))
    surface.blit(picture, rect)
    return rect


class Game:
    """Everything that is not a rule: pictures, fonts, sounds, the screen."""

    def __init__(self):
        self.cfg = rules.load_config()
        self.world = rules.World(self.cfg)

        size = int(self.cfg["sprite"]["size"])
        self.images = {
            "hero": load_image("hero", (size, size)),
            "bat": load_image("bat", (size, size)),
            "slime": load_image("slime", (size, size)),
            "ghost": load_image("ghost", (size, size)),
            "demon": load_image("demon", (size, size)),
            "sword": load_image("sword", (size, size)),
            "floor": load_image("floor", (size, size)),
            "gem_blue": load_image("gem_blue", (32, 32)),
            "gem_pink": load_image("gem_pink", (40, 40)),
        }
        self.white = {key: white_copy(image) for key, image in self.images.items() if key != "floor"}

        self.font_tiny = pygame.font.Font(None, 19)
        self.font_small = pygame.font.Font(None, 23)
        self.font_mid = pygame.font.Font(None, 30)
        self.font_big = pygame.font.Font(None, 62)

        self.night_tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.night_tint.fill((6, 9, 30, 186))
        self.strip = pygame.Surface((WIDTH, 52), pygame.SRCALPHA)
        self.strip.fill((10, 12, 24, 205))
        self.foot = pygame.Surface((WIDTH, 52), pygame.SRCALPHA)
        self.foot.fill((10, 12, 24, 235))
        self.glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.shadow = self.make_shadow()
        self.shadows = {}
        self.sounds = self.load_sounds()

        self.paused = False
        self.shake_x = 0.0
        self.shake_y = 0.0
        self.touch = False
        self.rng = random.Random(5)

    # -- pictures and sounds ---------------------------------------------

    def make_shadow(self):
        """A soft dark oval drawn under every character, so the floor looks deeper."""
        surface = pygame.Surface((44, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(surface, (0, 0, 0, 90), surface.get_rect())
        return surface

    def load_sounds(self):
        """Load sounds/<name>.wav or .ogg, whichever exists. Use whichever exists."""
        found = {}
        if not pygame.mixer.get_init():
            return found
        for name in ("hit", "gem", "hurt", "levelup", "end"):
            for extension in (".ogg", ".wav"):
                path = os.path.join(SOUND_DIR, name + extension)
                if os.path.isfile(path):
                    try:
                        found[name] = pygame.mixer.Sound(path)
                    except pygame.error:
                        pass
                    break
        return found

    def play(self, name):
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    def drain_events(self):
        """rules.py only writes words; here a word becomes a sound."""
        sounds = self.world.events
        self.world.events = []
        hits = 0
        for name in sounds:
            if name == "hit":
                hits += 1
                if hits > 3:            # do not stack 20 knocks in one frame
                    continue
            self.play(name)

    # -- input -------------------------------------------------------------

    def to_world(self, pos):
        """A point on the screen -> the same point in the world."""
        return (pos[0] - WIDTH * 0.5 + self.world.hero_x,
                pos[1] - HEIGHT * 0.5 + self.world.hero_y)

    def card_rects(self):
        return [pygame.Rect((WIDTH - CARD_WIDTH) // 2, top, CARD_WIDTH, CARD_HEIGHT)
                for top in CARD_TOPS]

    def restart(self):
        self.world.restart()
        self.paused = False

    def handle_event(self, event):
        """Return False when the window should close."""
        world = self.world

        if event.type == pygame.QUIT:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key == pygame.K_p and world.state == "playing":
                self.paused = not self.paused
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                if world.state in ("victory", "gameover"):
                    self.restart()

        elif event.type == pygame.MOUSEMOTION:
            if not self.touch:
                world.set_pointer(*self.to_world(event.pos))

        elif event.type == pygame.MOUSEBUTTONDOWN:
            world.set_pointer(*self.to_world(event.pos))
            self.click(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP:
            # On a computer the mouse stays where it is: the hero keeps walking.
            self.touch = False

        elif event.type == pygame.FINGERDOWN or event.type == pygame.FINGERMOTION:
            # A finger gives 0..1 positions, not pixels.
            pos = (int(event.x * WIDTH), int(event.y * HEIGHT))
            self.touch = True
            world.set_pointer(*self.to_world(pos))
            if event.type == pygame.FINGERDOWN:
                self.click(pos)

        elif event.type == pygame.FINGERUP:
            # Lift the finger: stop walking.
            self.touch = False
            world.release_pointer()

        return True

    def click(self, pos):
        world = self.world
        if world.state == "levelup":
            for index, rect in enumerate(self.card_rects()):
                if rect.collidepoint(pos):
                    world.choose_card(index)
                    self.play("levelup")
                    return
        elif world.state in ("victory", "gameover"):
            self.restart()

    # -- drawing -----------------------------------------------------------

    def draw_floor(self, screen):
        """One tile repeated forever: the map has no edges."""
        tile = self.images["floor"]
        step = tile.get_width()
        offset_x = int((-self.world.hero_x + WIDTH * 0.5 + self.shake_x) % step) - step
        offset_y = int((-self.world.hero_y + HEIGHT * 0.5 + self.shake_y) % step) - step
        for y in range(offset_y, HEIGHT + step, step):
            for x in range(offset_x, WIDTH + step, step):
                screen.blit(tile, (x, y))
        screen.blit(self.night_tint, (0, 0))

    def place(self, x, y):
        """World position -> pixel on the screen."""
        return (int(x - self.world.hero_x + WIDTH * 0.5 + self.shake_x),
                int(y - self.world.hero_y + HEIGHT * 0.5 + self.shake_y))

    def blit_centred(self, screen, image, x, y):
        screen.blit(image, (int(x - image.get_width() * 0.5),
                            int(y - image.get_height() * 0.5)))

    def get_shadow(self, width):
        """One shadow picture per size, made once and kept."""
        if width not in self.shadows:
            self.shadows[width] = pygame.transform.scale(self.shadow, (width, max(6, int(width * 0.34))))
        return self.shadows[width]

    def draw_world(self, screen):
        world = self.world

        # 1. Holy Ring: the area it covers, and a pulse when it hurts.
        level = world.weapons.get("holy_ring", 0)
        if level:
            _damage, radius, cooldown = world.ring_stats(level)
            centre = self.place(world.hero_x, world.hero_y)
            self.glow.fill((0, 0, 0, 0))
            pygame.draw.circle(self.glow, (110, 175, 255, 22), centre, int(radius))
            pygame.draw.circle(self.glow, (150, 205, 255, 120), centre, int(radius), 2)
            if world.ring_pulse > 0.0:
                pulse = int(radius * (1.0 - world.ring_pulse / cooldown) * 0.8)
                pygame.draw.circle(self.glow, (200, 240, 255, 160), centre,
                                   max(4, int(radius - pulse)), 3)
            screen.blit(self.glow, (0, 0))

        # 2. Crystals on the floor.
        for gem in world.gems:
            picture = self.images["gem_pink"] if gem.value > 1 else self.images["gem_blue"]
            gx, gy = self.place(gem.x, gem.y + math.sin(gem.spin) * 2.0)
            self.blit_centred(screen, picture, gx, gy)

        # 3. Sparks flying out of the wand.
        for spark in world.sparks:
            head = self.place(spark.x, spark.y)
            tail = self.place(spark.x - spark.vx * 0.03, spark.y - spark.vy * 0.03)
            pygame.draw.line(screen, (255, 170, 60), tail, head, 4)
            pygame.draw.circle(screen, SPARK, head, 4)

        # 4. Blades turning around the hero.
        level = world.weapons.get("spin_blades", 0)
        if level:
            blades, _damage = world.blade_stats(level)
            radius = self.cfg["weapons"]["spin_blades"]["orbit_radius"]
            centre = self.place(world.hero_x, world.hero_y)
            pygame.draw.circle(screen, (52, 58, 82), centre, int(radius), 1)
            for slot in range(blades):
                angle = world.blade_angle + slot * math.tau / blades
                bx, by = self.place(world.hero_x + math.cos(angle) * radius,
                                    world.hero_y + math.sin(angle) * radius)
                blade = pygame.transform.rotate(self.images["sword"], -(math.degrees(angle) + 90))
                self.blit_centred(screen, blade, bx, by)

        # 5. Enemies (with a shadow, and a white flash when freshly hit).
        for enemy in world.enemies:
            sx, sy = self.place(enemy.x, enemy.y)
            size = int(self.cfg["sprite"]["size"] * enemy.scale)
            shadow = self.get_shadow(int(size * 0.9))
            screen.blit(shadow, (int(sx - shadow.get_width() * 0.5), int(sy + size * 0.32)))
            picture = self.images.get(enemy.sprite)
            if picture is None:
                pygame.draw.circle(screen, (200, 80, 80), (sx, sy), int(enemy.radius))
                continue
            if enemy.flash > 0.0:
                picture = self.white.get(enemy.sprite, picture)
            if enemy.scale != 1.0:
                picture = pygame.transform.scale(picture, (size, size))
            self.blit_centred(screen, picture, sx, sy)
            if enemy.is_boss:
                width = 70
                left = sx - width // 2
                top = sy - size // 2 - 12
                pygame.draw.rect(screen, (50, 20, 26), (left, top, width, 6))
                filled = int(width * max(0.0, enemy.hp) / enemy.max_hp)
                pygame.draw.rect(screen, (255, 92, 92), (left, top, filled, 6))

        # 6. The hero.
        hx, hy = self.place(world.hero_x, world.hero_y)
        size = int(self.cfg["sprite"]["size"])
        shadow = self.get_shadow(int(size * 0.9))
        screen.blit(shadow, (int(hx - shadow.get_width() * 0.5), int(hy + size * 0.32)))
        hero = self.white["hero"] if world.hit_flash > 0.0 else self.images["hero"]
        self.blit_centred(screen, hero, hx, hy)

        # 7. Rings where enemies died (a quick flash).
        for x, y, life, radius in world.flashes:
            px, py = self.place(x, y)
            step = 1.0 - life / 0.22
            pygame.draw.circle(screen, (255, 230, 160), (px, py),
                               int(radius + step * 14.0), 2)

        # 8. Damage numbers floating up.
        for text in world.floats:
            alpha = max(0.0, min(1.0, text.life / text.total))
            colour = tuple(int(c * (0.45 + 0.55 * alpha)) for c in text.colour)
            px, py = self.place(text.x, text.y)
            draw_text(screen, self.font_small, text.text, colour, (px, py), centre=True)

    def draw_hud(self, screen):
        world = self.world

        screen.blit(self.strip, (0, 0))

        # HP bar and XP bar, top left.
        pygame.draw.rect(screen, HP_BACK, (12, 12, 150, 15), border_radius=4)
        filled = int(150 * max(0.0, world.hp) / world.max_hp)
        pygame.draw.rect(screen, HP_RED, (12, 12, filled, 15), border_radius=4)
        pygame.draw.rect(screen, XP_BACK, (12, 33, 150, 9), border_radius=3)
        filled = int(150 * min(1.0, world.xp / max(1, world.xp_need)))
        pygame.draw.rect(screen, XP_BLUE, (12, 33, filled, 9), border_radius=3)
        draw_text(screen, self.font_small, "Lv %d" % world.level, TEXT, (170, 12))
        draw_text(screen, self.font_tiny, "%d / %d HP" % (round(world.hp), round(world.max_hp)),
                  TEXT_DIM, (170, 34), shadow=False)

        # Timer, top right: the player always knows the goal.
        goal = int(self.cfg["goal"]["survive_seconds"])
        clock_text = "%d:%02d / %d:%02d" % (int(world.time) // 60, int(world.time) % 60,
                                            goal // 60, goal % 60)
        picture = self.font_small.render(clock_text, True, TEXT)
        screen.blit(picture, (WIDTH - 12 - picture.get_width(), 14))

        # Bottom: what you have, weapons on one line, items on the next.
        screen.blit(self.foot, (0, HEIGHT - 52))
        weapons = world.weapon_levels()
        items = world.item_levels()
        draw_text(screen, self.font_tiny,
                  "   ".join("%s %d" % row for row in weapons) or "no weapons",
                  TEXT, (WIDTH // 2, HEIGHT - 40), centre=True, shadow=False)
        if items:
            draw_text(screen, self.font_tiny,
                      "   ".join("%s %d" % row for row in items),
                      TEXT_DIM, (WIDTH // 2, HEIGHT - 20), centre=True, shadow=False)

    def draw_levelup(self, screen):
        world = self.world
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((8, 10, 22, 205))
        screen.blit(shade, (0, 0))

        draw_text(screen, self.font_big, "LEVEL %d" % world.level, TEXT,
                  (WIDTH // 2, 90), centre=True)
        draw_text(screen, self.font_small, "Pick one card", TEXT_DIM,
                  (WIDTH // 2, 122), centre=True, shadow=False)

        for index, rect in enumerate(self.card_rects()):
            if index >= len(world.cards):
                break
            card = world.cards[index]
            pygame.draw.rect(screen, CARD_BG, rect, border_radius=10)
            pygame.draw.rect(screen, CARD_EDGE, rect, 2, border_radius=10)
            pygame.draw.rect(screen, CARD_EDGE_HOT, (rect.x, rect.y + 12, 5, CARD_HEIGHT - 24),
                             border_radius=3)

            draw_text(screen, self.font_mid, card["title"], TEXT, (rect.x + 20, rect.y + 16))
            if card["kind"] == "heal":
                badge = "HEAL"
            elif card["level"] > 1:
                badge = "LEVEL %d" % card["level"]
            else:
                badge = "NEW"
            label = self.font_tiny.render(badge, True, CARD_EDGE_HOT)
            screen.blit(label, (rect.right - label.get_width() - 18, rect.y + 22))
            draw_text(screen, self.font_small, card["text"], TEXT_DIM,
                      (rect.x + 20, rect.y + 72), shadow=False)

        draw_text(screen, self.font_tiny, "Click or tap a card", (110, 120, 150),
                  (WIDTH // 2, 620), centre=True, shadow=False)

    def draw_end(self, screen):
        world = self.world
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((8, 10, 22, 190))
        screen.blit(shade, (0, 0))

        win = world.state == "victory"
        title = "VICTORY" if win else "GAME OVER"
        colour = (255, 226, 120) if win else (255, 110, 110)
        draw_text(screen, self.font_big, title, colour, (WIDTH // 2, 290), centre=True)

        minutes = int(world.time) // 60
        seconds = int(world.time) % 60
        draw_text(screen, self.font_mid, "You survived %d:%02d" % (minutes, seconds),
                  TEXT, (WIDTH // 2, 350), centre=True)
        draw_text(screen, self.font_small,
                  "%d enemies killed   ·   Level %d" % (world.kills, world.level),
                  TEXT_DIM, (WIDTH // 2, 386), centre=True, shadow=False)
        draw_text(screen, self.font_small, "Click or tap to play again", (150, 200, 240),
                  (WIDTH // 2, 450), centre=True, shadow=False)

    def draw(self, screen):
        world = self.world

        # A small shake when the hero is hurt.
        power = 4.0 * (world.shake / 0.25) if world.shake > 0.0 else 0.0
        self.shake_x = self.rng.uniform(-power, power)
        self.shake_y = self.rng.uniform(-power, power)

        screen.fill(NIGHT)
        self.draw_floor(screen)
        self.draw_world(screen)
        self.draw_hud(screen)

        if world.state == "levelup":
            self.draw_levelup(screen)
        elif world.state in ("victory", "gameover"):
            self.draw_end(screen)
        elif self.paused:
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((8, 10, 22, 150))
            screen.blit(shade, (0, 0))
            draw_text(screen, self.font_big, "PAUSED", TEXT, (WIDTH // 2, 330), centre=True)
            draw_text(screen, self.font_small, "Press P to go on", TEXT_DIM,
                      (WIDTH // 2, 380), centre=True, shadow=False)


# -- the loop --------------------------------------------------------------

# Two switches for one job: testing the game with no window (SDL_VIDEODRIVER=dummy).
# Nobody needs them to play: leave them unset and they do nothing.
HEADLESS_FRAMES = int(os.environ.get("NIGHT_HEADLESS_FRAMES", "0"))
SHOT_PATH = os.environ.get("NIGHT_SHOT", "")
SHOT_FRAME = int(os.environ.get("NIGHT_SHOT_FRAME", "90"))


def post_fake_input(frame):
    """Fake mouse moves, clicks and finger touches, so the input code runs too."""
    if frame == 20:
        pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(300, 500),
                                             rel=(0, 0), buttons=(0, 0, 0)))
    elif frame == 40:
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(300, 160), button=1))
    elif frame == 60:
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(300, 160), button=1))
    elif frame == 80:
        pygame.event.post(pygame.event.Event(pygame.FINGERDOWN, touch_id=0, finger_id=0,
                                             x=0.30, y=0.75, dx=0.0, dy=0.0))
    elif frame == 100:
        pygame.event.post(pygame.event.Event(pygame.FINGERMOTION, touch_id=0, finger_id=0,
                                             x=0.70, y=0.30, dx=0.0, dy=0.0))
    elif frame == 120:
        pygame.event.post(pygame.event.Event(pygame.FINGERUP, touch_id=0, finger_id=0,
                                             x=0.70, y=0.30, dx=0.0, dy=0.0))


def start_pygame():
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        pass                       # no sound card: the game still plays
    pygame.display.set_caption("Night Survivors - CDT501")
    return pygame.display.set_mode((WIDTH, HEIGHT))


async def main():
    screen = start_pygame()
    clock = pygame.time.Clock()
    game = Game()
    accumulator = 0.0
    running = True
    frames = 0

    while running:
        frame_seconds = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if not game.handle_event(event):
                running = False

        if game.paused or game.world.state != "playing":
            accumulator = 0.0
        else:
            accumulator += min(frame_seconds, 0.25)   # never more than a few steps at once
            while accumulator >= rules.STEP:
                game.world.update()
                accumulator -= rules.STEP

        game.drain_events()
        game.draw(screen)
        pygame.display.flip()

        frames += 1
        if SHOT_PATH and frames == SHOT_FRAME:
            pygame.image.save(screen, SHOT_PATH)
        if HEADLESS_FRAMES:
            post_fake_input(frames)
            if frames >= HEADLESS_FRAMES:
                world = game.world
                print("headless run: %d frames, state=%s, hp=%.0f, level=%d, "
                      "enemies=%d, kills=%d, time=%.1fs"
                      % (frames, world.state, world.hp, world.level,
                         len(world.enemies), world.kills, world.time))
                running = False

        await asyncio.sleep(0)          # let the browser breathe: pygbag needs this

    pygame.quit()


asyncio.run(main())
