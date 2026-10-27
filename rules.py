# LIU Liangyi (3231234) - CDT501 Lecture 9 - Night Survivors
"""rules.py - the rules of the game: the world, its numbers and one fixed step.

Nothing in this file imports pygame, so the tests can run it alone.
Every number comes from data/game.json: change a number there, run again.
"""

import json
import math
import os
import random

STEP = 1.0 / 60.0          # one fixed step = 1/60 of a second
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "data", "game.json")


def load_config(path=DATA_PATH):
    """Read data/game.json into a dict."""
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _length(dx, dy):
    return math.hypot(dx, dy)


class Enemy:
    """One enemy. Its numbers are copied from the config when it is born."""

    __slots__ = ("kind", "x", "y", "hp", "max_hp", "speed", "damage", "xp",
                 "radius", "sprite", "scale", "hurt_timer", "blade_timers", "flash")

    def __init__(self, kind, x, y, data):
        self.kind = kind
        self.x = float(x)
        self.y = float(y)
        self.hp = float(data["hp"])
        self.max_hp = float(data["hp"])
        self.speed = float(data["speed"])
        self.damage = float(data["damage"])
        self.xp = int(data["xp"])
        self.radius = float(data["hit_radius"])
        self.sprite = data.get("sprite", kind)
        self.scale = float(data.get("scale", 1.0))
        self.hurt_timer = 0.0      # seconds until it can hurt the hero again
        self.blade_timers = {}     # blade slot -> seconds until it can be hit again
        self.flash = 0.0           # seconds of white flash after being hit

    @property
    def is_boss(self):
        return self.kind == "demon"

    @property
    def alive(self):
        return self.hp > 0.0


class Spark:
    """A spark from the Spark Wand: it flies in one straight line."""

    __slots__ = ("x", "y", "vx", "vy", "damage", "life")

    def __init__(self, x, y, vx, vy, damage, life):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.damage = float(damage)
        self.life = float(life)


class Gem:
    """A crystal dropped by a dead enemy. XP 1 = blue, XP 2 = pink."""

    __slots__ = ("x", "y", "value", "flying", "spin")

    def __init__(self, x, y, value, spin=0.0):
        self.x = float(x)
        self.y = float(y)
        self.value = int(value)
        self.flying = False
        self.spin = float(spin)


class FloatText:
    """A damage number that floats up and fades out."""

    __slots__ = ("x", "y", "text", "life", "total", "colour")

    def __init__(self, x, y, text, colour, life=0.6):
        self.x = float(x)
        self.y = float(y)
        self.text = str(text)
        self.colour = colour
        self.life = float(life)
        self.total = float(life)


class World:
    """The whole game state. Call update() 60 times a second."""

    def __init__(self, config=None, seed=None):
        self.cfg = config if config is not None else load_config()
        self.rng = random.Random(seed)
        self.restart()

    # -- setup -------------------------------------------------------------

    def restart(self):
        """Start a new game with the same rules."""
        hero = self.cfg["hero"]
        self.time = 0.0
        self.state = "playing"          # playing / levelup / victory / gameover
        self.kills = 0
        self.level = 1
        self.xp = 0

        self.hero_x = 0.0
        self.hero_y = 0.0
        self.max_hp = float(hero["max_hp"])
        self.hp = self.max_hp

        self.weapons = {"spark_wand": 1}    # always start with the Spark Wand
        self.items = {}

        self.enemies = []
        self.sparks = []
        self.gems = []
        self.floats = []
        self.flashes = []               # little rings where an enemy died
        self.events = []                # "hit", "gem", ... -> main.py plays a sound
        self.cards = []                 # the 3 cards after a level-up

        self.pointer = None             # where the mouse or the finger is
        self.pointer_active = False

        self.spark_timer = 0.0
        self.blade_angle = 0.0
        self.ring_timer = 0.0
        self.ring_pulse = 0.0
        self.spawn_timer = 0.0
        self.shake = 0.0
        self.boss_spawned = False
        self.hit_flash = 0.0

        self.spawn_tick(capped=False)   # 12 bats at 0:00, so the game starts full

    # -- numbers that grow with the build --------------------------------

    @property
    def speed(self):
        bonus = self.cfg["items"]["swift_boots"]["speed_bonus"]
        return float(self.cfg["hero"]["speed"]) * (1.0 + bonus * self.items.get("swift_boots", 0))

    @property
    def magnet_radius(self):
        bonus = self.cfg["items"]["magnet"]["magnet_bonus"]
        return float(self.cfg["hero"]["magnet_radius"]) + bonus * self.items.get("magnet", 0)

    @property
    def xp_need(self):
        return self.cfg["xp"]["first_level"] + self.cfg["xp"]["per_level"] * (self.level - 1)

    def weapon_levels(self):
        """[(short name, level)] of the weapons you have, in a fixed order."""
        rows = []
        for key, spec in self.cfg["weapons"].items():
            level = self.weapons.get(key, 0)
            if level > 0:
                rows.append((spec["short"], level))
        return rows

    def item_levels(self):
        """[(short name, level)] of the passive items you have."""
        rows = []
        for key, spec in self.cfg["items"].items():
            level = self.items.get(key, 0)
            if level > 0:
                rows.append((spec["short"], level))
        return rows

    def spark_stats(self, level):
        """damage, cooldown, number of sparks for a given level."""
        spec = self.cfg["weapons"]["spark_wand"]
        damage = spec["level1"]["damage"] + spec["per_level"]["damage"] * (level - 1)
        cooldown = spec["level1"]["cooldown"] - spec["per_level"]["cooldown"] * (level - 1)
        sparks = spec["level1"]["sparks"]
        for step in spec["extra_spark_levels"]:
            if level >= step:
                sparks += 1
        return damage, max(0.15, cooldown), sparks

    def blade_stats(self, level):
        """number of blades, damage for a given level."""
        spec = self.cfg["weapons"]["spin_blades"]
        damage = spec["level1"]["damage"] + spec["per_level"]["damage"] * (level - 1)
        blades = spec["level1"]["blades"]
        for step in spec["extra_blade_levels"]:
            if level >= step:
                blades += 1
        return blades, damage

    def ring_stats(self, level):
        """damage, radius, cooldown for a given level."""
        spec = self.cfg["weapons"]["holy_ring"]
        damage = spec["level1"]["damage"] + spec["per_level"]["damage"] * (level - 1)
        radius = spec["level1"]["radius"] + spec["per_level"]["radius"] * (level - 1)
        return damage, radius, spec["level1"]["cooldown"]

    # -- input -------------------------------------------------------------

    def set_pointer(self, x, y):
        """The mouse or the finger is here, in world coordinates."""
        self.pointer = (float(x), float(y))
        self.pointer_active = True

    def release_pointer(self):
        """The finger was lifted: stop walking."""
        self.pointer_active = False

    # -- one fixed step ----------------------------------------------------

    def update(self):
        """Advance the world by exactly STEP seconds."""
        self._tick_effects()
        if self.state == "levelup":
            return
        if self.state != "playing":
            return

        self.time += STEP
        self._check_level_up()
        if self.state != "playing":
            return

        self._move_hero()
        self._fire_weapons()
        self._move_sparks()
        self._move_enemies()
        self._collect_gems()
        self._spawn_if_needed()

        if self.state == "playing" and self.time >= self.cfg["goal"]["survive_seconds"]:
            self.state = "victory"
            self.events.append("end")

    def _tick_effects(self):
        self.shake = max(0.0, self.shake - STEP)
        self.hit_flash = max(0.0, self.hit_flash - STEP)
        self.ring_pulse = max(0.0, self.ring_pulse - STEP)
        for text in self.floats:
            text.y -= 28.0 * STEP
            text.life -= STEP
        self.floats = [t for t in self.floats if t.life > 0]
        for flash in self.flashes:
            flash[2] -= STEP
        self.flashes = [f for f in self.flashes if f[2] > 0]
        for enemy in self.enemies:
            if enemy.hurt_timer > 0:
                enemy.hurt_timer -= STEP
            if enemy.flash > 0:
                enemy.flash -= STEP
            if enemy.blade_timers:
                for slot in list(enemy.blade_timers):
                    enemy.blade_timers[slot] -= STEP
                    if enemy.blade_timers[slot] <= 0:
                        del enemy.blade_timers[slot]

    def _move_hero(self):
        if not self.pointer_active or self.pointer is None:
            return
        dx = self.pointer[0] - self.hero_x
        dy = self.pointer[1] - self.hero_y
        dist = _length(dx, dy)
        if dist <= self.cfg["hero"]["stop_distance"] or dist == 0.0:
            return
        step = min(self.speed * STEP, dist)
        self.hero_x += dx / dist * step
        self.hero_y += dy / dist * step

    def _fire_weapons(self):
        cfg = self.cfg

        # 1. Spark Wand: shoot the nearest enemy.
        level = self.weapons.get("spark_wand", 0)
        if level:
            self.spark_timer -= STEP
            if self.spark_timer <= 0.0:
                target = self.nearest_enemy()
                if target is not None:
                    damage, cooldown, sparks = self.spark_stats(level)
                    self.spark_timer = cooldown
                    aim = math.atan2(target.y - self.hero_y, target.x - self.hero_x)
                    speed = cfg["weapons"]["spark_wand"]["speed"]
                    for index in range(sparks):
                        spread = (index - (sparks - 1) * 0.5) * 0.16
                        angle = aim + spread
                        self.sparks.append(Spark(
                            self.hero_x, self.hero_y,
                            math.cos(angle) * speed, math.sin(angle) * speed,
                            damage, cfg["combat"]["spark_linger"]))
                    self.events.append("shoot")

        # 2. Spin Blades: blades turn around the hero and hit what they touch.
        level = self.weapons.get("spin_blades", 0)
        if level:
            spec = cfg["weapons"]["spin_blades"]
            blades, damage = self.blade_stats(level)
            self.blade_angle = (self.blade_angle + math.tau * STEP / spec["turn_seconds"]) % math.tau
            radius = spec["orbit_radius"]
            reach = radius + 24.0
            for slot in range(blades):
                angle = self.blade_angle + slot * math.tau / blades
                bx = self.hero_x + math.cos(angle) * radius
                by = self.hero_y + math.sin(angle) * radius
                for enemy in self.enemies:
                    if (enemy.x - self.hero_x) ** 2 + (enemy.y - self.hero_y) ** 2 > reach * reach:
                        continue
                    if enemy.blade_timers.get(slot, 0.0) > 0.0:
                        continue
                    if _length(enemy.x - bx, enemy.y - by) <= enemy.radius + 14.0:
                        enemy.blade_timers[slot] = spec["hit_cooldown"]
                        self.hit_enemy(enemy, damage)

        # 3. Holy Ring: hurt everything inside a circle, again and again.
        level = self.weapons.get("holy_ring", 0)
        if level:
            self.ring_timer -= STEP
            if self.ring_timer <= 0.0:
                damage, radius, cooldown = self.ring_stats(level)
                self.ring_timer = cooldown
                self.ring_pulse = cooldown
                for enemy in list(self.enemies):
                    if _length(enemy.x - self.hero_x, enemy.y - self.hero_y) <= radius + enemy.radius:
                        self.hit_enemy(enemy, damage)

        self.enemies = [e for e in self.enemies if e.alive]

    def _move_sparks(self):
        linger = self.cfg["combat"]["spark_linger"]
        keep = []
        for spark in self.sparks:
            spark.x += spark.vx * STEP
            spark.y += spark.vy * STEP
            spark.life -= STEP
            hit = None
            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                if _length(enemy.x - spark.x, enemy.y - spark.y) <= enemy.radius + 5.0:
                    hit = enemy
                    break
            if hit is not None:
                self.hit_enemy(hit, spark.damage)
            elif spark.life > 0.0:
                keep.append(spark)
        self.sparks = keep
        self.enemies = [e for e in self.enemies if e.alive]

    def _move_enemies(self):
        cfg = self.cfg["spawning"]
        hero_r = self.cfg["hero"]["hit_radius"]
        keep = []
        for enemy in self.enemies:
            dx = self.hero_x - enemy.x
            dy = self.hero_y - enemy.y
            dist = _length(dx, dy)
            if dist > 0.0:
                step = min(enemy.speed * STEP, dist)
                enemy.x += dx / dist * step
                enemy.y += dy / dist * step

            if enemy.is_boss:
                # The boss is never removed: it is put back on the ring instead.
                if dist > cfg["boss_return_distance"]:
                    self._place_on_ring(enemy)
                    dist = cfg["ring_radius"]
            elif dist > cfg["despawn_distance"]:
                continue        # far behind: forget it, new ones will come

            if dist <= enemy.radius + hero_r and enemy.hurt_timer <= 0.0:
                self.hurt_hero(enemy.damage)
                enemy.hurt_timer = self.cfg["combat"]["enemy_hit_cooldown"]
                if self.state != "playing":
                    return

            keep.append(enemy)
        self.enemies = [e for e in keep if e.alive]

    def _collect_gems(self):
        cfg = self.cfg["gems"]
        keep = []
        for gem in self.gems:
            gem.spin += STEP * 4.0
            dx = self.hero_x - gem.x
            dy = self.hero_y - gem.y
            dist = _length(dx, dy)
            if dist <= self.magnet_radius:
                gem.flying = True
            if gem.flying and dist > 0.0:
                step = min(cfg["fly_speed"] * STEP, dist)
                gem.x += dx / dist * step
                gem.y += dy / dist * step
                dist = max(0.0, dist - step)
            if dist <= cfg["pickup_radius"]:
                self.xp += gem.value
                self.events.append("gem")
                self.floats.append(FloatText(self.hero_x + 8, self.hero_y - 18,
                                             "+%d" % gem.value, (130, 220, 255), 0.5))
                continue
            keep.append(gem)
        self.gems = keep

    def _spawn_if_needed(self):
        self.spawn_timer -= STEP
        if self.spawn_timer <= 0.0:
            self.spawn_tick()

    # -- spawning ----------------------------------------------------------

    def wave_row(self):
        """The row of the wave table that is true right now."""
        row = self.cfg["waves"][0]
        for entry in self.cfg["waves"]:
            if self.time >= entry["from"]:
                row = entry
        return row

    def spawn_tick(self, capped=True):
        """Top the enemies up to the minimum of the current wave.

        capped=True is the rule "at most 8 new enemies every second";
        at 0:00 the game fills up in one go, so restart() uses capped=False.
        """
        cfg = self.cfg["spawning"]
        self.spawn_timer = cfg["check_interval"]
        row = self.wave_row()

        if row.get("boss") and not self.boss_spawned:
            self.boss_spawned = True
            self.spawn_enemy("demon")

        cap = cfg["max_per_check"] if capped else cfg["max_alive"]
        added = 0
        while len(self.enemies) < row["minimum"] and added < cap:
            if len(self.enemies) >= cfg["max_alive"]:
                break
            self.spawn_enemy(self.rng.choice(row["types"]))
            added += 1

    def spawn_enemy(self, kind, x=None, y=None):
        """Put one enemy on the ring 380 px away, or exactly at (x, y)."""
        data = self.cfg["enemies"][kind]
        enemy = Enemy(kind, 0.0, 0.0, data)
        if x is None or y is None:
            self._place_on_ring(enemy)
        else:
            enemy.x, enemy.y = float(x), float(y)
        self.enemies.append(enemy)
        return enemy

    def _place_on_ring(self, enemy):
        angle = self.rng.random() * math.tau
        radius = self.cfg["spawning"]["ring_radius"]
        enemy.x = self.hero_x + math.cos(angle) * radius
        enemy.y = self.hero_y + math.sin(angle) * radius

    # -- damage ------------------------------------------------------------

    def nearest_enemy(self):
        best = None
        best_dist = 0.0
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            dist = _length(enemy.x - self.hero_x, enemy.y - self.hero_y)
            if best is None or dist < best_dist:
                best = enemy
                best_dist = dist
        return best

    def hit_enemy(self, enemy, damage):
        """Take damage away from one enemy; it may die."""
        if not enemy.alive:
            return
        enemy.hp -= damage
        enemy.flash = 0.08
        self.floats.append(FloatText(enemy.x, enemy.y - enemy.radius, "%d" % round(damage),
                                     (255, 236, 140)))
        self.events.append("hit")
        if enemy.hp <= 0.0:
            self.kill_enemy(enemy)

    def kill_enemy(self, enemy):
        """The enemy dies: a crystal falls, a flash appears.

        The dead enemy stays in the list until the next filter (hp <= 0),
        so the loops that are running right now do not skip their neighbours.
        """
        enemy.hp = 0.0
        self.kills += 1
        self.flashes.append([enemy.x, enemy.y, 0.22, enemy.radius + 6.0])
        if enemy.xp > 0:
            self.gems.append(Gem(enemy.x, enemy.y, enemy.xp, self.rng.random() * math.tau))

    def hurt_hero(self, damage):
        """The hero loses HP. At 0 the game is over."""
        self.hp -= damage
        self.shake = 0.25
        self.hit_flash = 0.18
        self.events.append("hurt")
        self.floats.append(FloatText(self.hero_x, self.hero_y - 24,
                                     "-%d" % round(damage), (255, 120, 120)))
        if self.hp <= 0.0:
            self.hp = 0.0
            self.state = "gameover"
            self.events.append("end")

    # -- XP and level-up ---------------------------------------------------

    def _check_level_up(self):
        if self.state != "playing":
            return
        while self.xp >= self.xp_need:
            self.xp -= self.xp_need
            self.level += 1
            self.events.append("levelup")
            self.cards = self.make_cards()
            self.state = "levelup"
            return

    def make_cards(self):
        """3 random things you may take: a new weapon, a better weapon, an item."""
        cfg = self.cfg
        pool = []
        for key, spec in cfg["weapons"].items():
            level = self.weapons.get(key, 0)
            if level == 0:
                if len(self.weapons) < cfg["max_weapons"]:
                    pool.append(("weapon_new", key))
            elif level < spec["max_level"]:
                pool.append(("weapon_up", key))
        for key, spec in cfg["items"].items():
            if self.items.get(key, 0) < spec.get("max_level", 5):
                pool.append(("item", key))

        self.rng.shuffle(pool)
        wanted = cfg["xp"]["cards"]
        cards = [self._make_card(kind, key) for kind, key in pool[:wanted]]
        while len(cards) < wanted:
            cards.append({
                "kind": "heal",
                "key": "heal",
                "title": "Heal %d HP" % round(cfg["xp"]["heal_amount"]),
                "level": 0,
                "text": "Get some health back",
            })
        return cards

    def _make_card(self, kind, key):
        cfg = self.cfg
        if kind == "weapon_new":
            spec = cfg["weapons"][key]
            return {"kind": kind, "key": key, "title": spec["name"], "level": 1,
                    "text": spec.get("text_first", "A new weapon")}
        if kind == "weapon_up":
            spec = cfg["weapons"][key]
            level = self.weapons[key] + 1
            return {"kind": kind, "key": key, "title": spec["name"], "level": level,
                    "text": self._upgrade_text(key, level)}
        spec = cfg["items"][key]
        return {"kind": kind, "key": key, "title": spec["name"],
                "level": self.items.get(key, 0) + 1, "text": spec.get("text", "")}

    def _upgrade_text(self, key, level):
        """Build the one line of text from the numbers in data/game.json."""
        spec = self.cfg["weapons"][key]
        per = spec.get("per_level", {})
        parts = []
        if "damage" in per:
            parts.append("+%d damage" % round(per["damage"]))
        if "cooldown" in per:
            parts.append("%.2f s faster" % per["cooldown"])
        if "radius" in per:
            parts.append("+%d px radius" % round(per["radius"]))
        if level in spec.get("extra_spark_levels", []):
            parts.append("+1 spark")
        if level in spec.get("extra_blade_levels", []):
            parts.append("+1 blade")
        return ", ".join(parts) if parts else "Stronger"

    def choose_card(self, index):
        """The player clicked card number `index`."""
        if self.state != "levelup" or not (0 <= index < len(self.cards)):
            return False
        card = self.cards[index]
        kind = card["kind"]
        if kind in ("weapon_new", "weapon_up"):
            self.weapons[card["key"]] = card["level"]
        elif kind == "item":
            key = card["key"]
            self.items[key] = self.items.get(key, 0) + 1
            if key == "big_heart":
                spec = self.cfg["items"]["big_heart"]
                self.max_hp += spec["max_hp_bonus"]
                self.hp = min(self.max_hp, self.hp + spec["heal"])
        elif kind == "heal":
            self.hp = min(self.max_hp, self.hp + self.cfg["xp"]["heal_amount"])

        self.cards = []
        self.state = "playing"
        self._check_level_up()      # one big crystal can fill the bar twice
        return True
