# LIU Liangyi (3231234) - CDT501 Lecture 9 - Night Survivors
"""tests/test_rules.py - tests for the rules in rules.py only.

No tests for drawing, pictures or sounds: those you check by playing.
Every number comes from data/game.json, so if you change a number there the
tests check the new number, not an old copy of it.

    python -m unittest
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import rules          # noqa: E402  (it lives in the folder above tests/)


def new_world(seed=1):
    return rules.World(rules.load_config(), seed=seed)


def run_steps(world, steps):
    for _ in range(steps):
        world.update()


class StartTest(unittest.TestCase):
    def test_game_starts_with_twelve_bats(self):
        world = new_world()
        self.assertEqual(world.state, "playing")
        self.assertEqual(len(world.enemies), 12)
        self.assertTrue(all(enemy.kind == "bat" for enemy in world.enemies))
        self.assertEqual(world.hp, world.max_hp)
        self.assertEqual(world.weapons, {"spark_wand": 1})

    def test_every_enemy_starts_off_screen(self):
        world = new_world()
        ring = world.cfg["spawning"]["ring_radius"]
        for enemy in world.enemies:
            distance = rules._length(enemy.x - world.hero_x, enemy.y - world.hero_y)
            self.assertAlmostEqual(distance, ring, places=3)


class SpawningTest(unittest.TestCase):
    def test_at_most_eight_new_enemies_every_second(self):
        world = new_world()
        world.enemies.clear()
        world.spawn_tick()
        self.assertEqual(len(world.enemies), 8)     # the cap of one second
        world.spawn_tick()
        self.assertEqual(len(world.enemies), 12)    # the minimum at 0:00 is reached

    def test_wave_table(self):
        world = new_world()
        expected = [(0, 12), (15, 20), (30, 28), (45, 36), (60, 45), (75, 55), (90, 55), (105, 75)]
        for seconds, minimum in expected:
            world.time = float(seconds)
            self.assertEqual(world.wave_row()["minimum"], minimum)

    def test_new_enemy_types_after_thirty_seconds(self):
        world = new_world()
        world.time = 30.0
        world.enemies.clear()
        for _ in range(4):
            world.spawn_tick()
        kinds = {enemy.kind for enemy in world.enemies}
        self.assertEqual(len(world.enemies), 28)
        self.assertEqual(kinds, {"bat", "slime"})

    def test_enemy_far_behind_is_removed(self):
        world = new_world()
        world.enemies.clear()
        far = world.spawn_enemy("bat", 800, 0)
        run_steps(world, 1)
        self.assertNotIn(far, world.enemies)

    def test_boss_appears_once_at_one_thirty(self):
        world = new_world()
        world.time = 90.0
        world.spawn_tick()
        bosses = [enemy for enemy in world.enemies if enemy.is_boss]
        self.assertEqual(len(bosses), 1)
        world.spawn_tick()
        bosses = [enemy for enemy in world.enemies if enemy.is_boss]
        self.assertEqual(len(bosses), 1)

    def test_never_more_than_max_alive(self):
        world = new_world()
        world.time = 105.0
        for _ in range(40):
            world.spawn_tick()
        self.assertLessEqual(len(world.enemies), world.cfg["spawning"]["max_alive"])


class DamageTest(unittest.TestCase):
    def test_enemy_hurts_the_hero_once_every_half_second(self):
        world = new_world()
        world.enemies.clear()
        # A slime has 30 HP, so it lives through the Spark Wand hits.
        slime = world.spawn_enemy("slime", world.hero_x + 2, world.hero_y)
        start = world.hp

        run_steps(world, 1)
        self.assertEqual(world.hp, start - slime.damage)      # first touch hurts

        run_steps(world, 10)                                 # 0.17 s later
        self.assertEqual(world.hp, start - slime.damage)       # still the same touch

        run_steps(world, 25)                                 # more than 0.5 s in total
        self.assertEqual(world.hp, start - 2 * slime.damage)

    def test_spark_wand_kills_the_nearest_bat(self):
        world = new_world()
        world.enemies.clear()
        bat = world.spawn_enemy("bat", world.hero_x + 120, world.hero_y)
        damage = world.spark_stats(world.weapons["spark_wand"])[0]
        self.assertGreaterEqual(damage, bat.max_hp)

        run_steps(world, 60)
        self.assertEqual(world.kills, 1)
        self.assertNotIn(bat, world.enemies)
        self.assertEqual(len(world.gems), 1)

    def test_hero_dies_at_zero_hp(self):
        world = new_world()
        world.enemies.clear()
        world.spawn_enemy("demon", world.hero_x + 2, world.hero_y)
        world.hp = 5.0
        run_steps(world, 1)
        self.assertEqual(world.hp, 0.0)
        self.assertEqual(world.state, "gameover")


class GrowthTest(unittest.TestCase):
    def test_a_dead_enemy_drops_a_crystal_worth_its_xp(self):
        world = new_world()
        world.enemies.clear()
        slime = world.spawn_enemy("slime", world.hero_x + 60, world.hero_y)
        world.kill_enemy(slime)
        self.assertEqual(len(world.gems), 1)
        self.assertEqual(world.gems[0].value, 2)
        self.assertEqual(world.gems[0].x, slime.x)

    def test_walking_over_a_crystal_gives_xp(self):
        world = new_world()
        world.enemies.clear()
        world.gems.clear()
        world.gems.append(rules.Gem(world.hero_x + 20, world.hero_y, 1))
        run_steps(world, 5)
        self.assertEqual(world.gems, [])
        self.assertEqual(world.xp, 1)

    def test_five_xp_is_level_two_and_the_game_pauses(self):
        world = new_world()
        world.xp = 5
        run_steps(world, 1)
        self.assertEqual(world.level, 2)
        self.assertEqual(world.xp, 0)
        self.assertEqual(world.state, "levelup")
        self.assertEqual(len(world.cards), 3)

    def test_next_level_needs_three_more(self):
        world = new_world()
        needs = []
        for level in range(1, 5):
            world.level = level
            needs.append(world.xp_need)
        self.assertEqual(needs, [5, 8, 11, 14])

    def test_choosing_a_card_makes_the_game_go_on(self):
        world = new_world()
        world.xp = 5
        run_steps(world, 1)
        card = world.cards[0]
        self.assertTrue(world.choose_card(0))
        self.assertEqual(world.state, "playing")
        self.assertEqual(world.cards, [])
        if card["kind"] in ("weapon_new", "weapon_up"):
            self.assertEqual(world.weapons[card["key"]], card["level"])
        elif card["kind"] == "item":
            self.assertEqual(world.items[card["key"]], 1)

    def test_never_offer_something_at_level_five(self):
        world = new_world()
        for key, spec in world.cfg["weapons"].items():
            world.weapons[key] = spec["max_level"]
        for key in world.cfg["items"]:
            world.items[key] = 5
        cards = world.make_cards()
        self.assertEqual(len(cards), 3)
        self.assertTrue(all(card["kind"] == "heal" for card in cards))

    def test_swift_boots_make_the_hero_faster(self):
        world = new_world()
        before = world.speed
        world.items["swift_boots"] = 2
        self.assertAlmostEqual(world.speed, before * 1.2, places=3)

    def test_magnet_pushes_the_pickup_radius_out(self):
        world = new_world()
        before = world.magnet_radius
        world.items["magnet"] = 3
        self.assertAlmostEqual(world.magnet_radius, before + 90.0, places=3)

    def test_holy_ring_gets_a_bigger_radius(self):
        world = new_world()
        small = world.ring_stats(1)[1]
        big = world.ring_stats(5)[1]
        self.assertAlmostEqual(big - small, 4 * world.cfg["weapons"]["holy_ring"]["per_level"]["radius"])

    def test_spark_wand_gets_one_more_spark_at_level_three(self):
        world = new_world()
        self.assertEqual(world.spark_stats(1)[2], 1)
        self.assertEqual(world.spark_stats(2)[2], 1)
        self.assertEqual(world.spark_stats(3)[2], 2)
        self.assertEqual(world.spark_stats(5)[2], 3)


class EndTest(unittest.TestCase):
    def test_two_minutes_is_victory(self):
        world = new_world()
        world.time = world.cfg["goal"]["survive_seconds"] - rules.STEP * 0.5
        run_steps(world, 2)
        self.assertEqual(world.state, "victory")
        self.assertIn("end", world.events)

    def test_play_again_starts_a_new_game(self):
        world = new_world()
        world.state = "gameover"
        world.kills = 7
        world.restart()
        self.assertEqual(world.state, "playing")
        self.assertEqual(world.kills, 0)
        self.assertEqual(world.time, 0.0)
        self.assertEqual(len(world.enemies), 12)


if __name__ == "__main__":
    unittest.main()
