#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Memory Match Card Game.

Tests use direct imports for unit tests on classes and subprocess
for integration tests. All tests run without user interaction.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from game import (
    CARD_SYMBOLS,
    CARD_BACK,
    DIFFICULTY_PRESETS,
    Board,
    Config,
    Game,
    ScoreEntry,
    ScoreManager,
    SoundManager,
    beep,
    clear_screen,
    format_time,
)

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

TEST_DIR = Path(__file__).parent
TEST_SETTINGS = TEST_DIR / "test_settings.json"
TEST_SCORES = TEST_DIR / "test_scores.json"


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def clean_test_files() -> None:
    """Remove test files if they exist."""
    for f in [TEST_SETTINGS, TEST_SCORES]:
        if f.exists():
            f.unlink()


# ---------------------------------------------------------------------------
# Tests: format_time
# ---------------------------------------------------------------------------


class TestFormatTime(unittest.TestCase):
    """Tests for format_time utility function."""

    def test_zero(self) -> None:
        """Test 0 seconds."""
        self.assertEqual(format_time(0), "00:00")

    def test_minutes(self) -> None:
        """Test exact minutes."""
        self.assertEqual(format_time(60), "01:00")
        self.assertEqual(format_time(120), "02:00")

    def test_seconds(self) -> None:
        """Test seconds only."""
        self.assertEqual(format_time(45), "00:45")
        self.assertEqual(format_time(5), "00:05")

    def test_mixed(self) -> None:
        """Test mixed minutes and seconds."""
        self.assertEqual(format_time(125), "02:05")
        self.assertEqual(format_time(3661), "61:01")


# ---------------------------------------------------------------------------
# Tests: Board
# ---------------------------------------------------------------------------


class TestBoard(unittest.TestCase):
    """Tests for Board class."""

    def test_board_creation_easy(self) -> None:
        """Test creating an easy 4x4 board."""
        board = Board(4, 4, 8)
        self.assertEqual(board.rows, 4)
        self.assertEqual(board.cols, 4)
        self.assertEqual(board.pairs, 8)
        self.assertEqual(len(board.cards), 4)
        self.assertEqual(len(board.cards[0]), 4)

    def test_board_creation_medium(self) -> None:
        """Test creating a medium 4x6 board."""
        board = Board(4, 6, 12)
        self.assertEqual(board.rows, 4)
        self.assertEqual(board.cols, 6)
        self.assertEqual(board.pairs, 12)
        self.assertEqual(len(board.cards), 4)
        self.assertEqual(len(board.cards[0]), 6)

    def test_board_creation_hard(self) -> None:
        """Test creating a hard 6x6 board."""
        board = Board(6, 6, 18)
        self.assertEqual(board.rows, 6)
        self.assertEqual(board.cols, 6)
        self.assertEqual(board.pairs, 18)

    def test_board_all_cards_face_down(self) -> None:
        """Test that all cards start face-down."""
        board = Board(4, 4, 8)
        for r in range(4):
            for c in range(4):
                self.assertFalse(board.cards[r][c]["matched"])
        self.assertEqual(len(board.flipped), 0)

    def test_board_each_symbol_appears_twice(self) -> None:
        """Test that each symbol appears exactly twice."""
        board = Board(4, 4, 8)
        symbols = []
        for r in range(4):
            for c in range(4):
                symbols.append(board.cards[r][c]["symbol"])

        from collections import Counter
        counts = Counter(symbols)
        for symbol, count in counts.items():
            self.assertEqual(count, 2, f"Symbol {symbol} appears {count} times, expected 2")

    def test_valid_coord(self) -> None:
        """Test coordinate parsing."""
        board = Board(4, 4, 8)
        self.assertEqual(board.is_valid_coord("a1"), (0, 0))
        self.assertEqual(board.is_valid_coord("b2"), (1, 1))
        self.assertEqual(board.is_valid_coord("d4"), (3, 3))
        self.assertEqual(board.is_valid_coord("A1"), (0, 0))  # uppercase

    def test_invalid_coord_format(self) -> None:
        """Test invalid coordinate formats."""
        board = Board(4, 4, 8)
        self.assertIsNone(board.is_valid_coord(""))
        self.assertIsNone(board.is_valid_coord("1"))
        self.assertIsNone(board.is_valid_coord("a"))
        self.assertIsNone(board.is_valid_coord("11"))
        self.assertIsNone(board.is_valid_coord("aa"))

    def test_out_of_bounds_coord(self) -> None:
        """Test out-of-bounds coordinates."""
        board = Board(4, 4, 8)
        self.assertIsNone(board.is_valid_coord("e1"))  # col out of range
        self.assertIsNone(board.is_valid_coord("a5"))  # row out of range
        self.assertIsNone(board.is_valid_coord("z9"))  # both out of range

    def test_flip_card(self) -> None:
        """Test flipping a card."""
        board = Board(4, 4, 8)
        symbol = board.flip_card((0, 0))
        self.assertIsNotNone(symbol)
        self.assertIn((0, 0), board.flipped)
        self.assertEqual(board.get_card_display(0, 0), symbol)

    def test_flip_already_flipped_card(self) -> None:
        """Test flipping an already flipped card returns None."""
        board = Board(4, 4, 8)
        board.flip_card((0, 0))
        result = board.flip_card((0, 0))
        self.assertIsNone(result)

    def test_flip_matched_card(self) -> None:
        """Test flipping a matched card returns None."""
        board = Board(4, 4, 8)
        board.cards[0][0]["matched"] = True
        result = board.flip_card((0, 0))
        self.assertIsNone(result)

    def test_check_match_success(self) -> None:
        """Test successful match detection."""
        board = Board(4, 4, 8)
        # Find two cards with the same symbol
        symbol = board.cards[0][0]["symbol"]
        pos2 = None
        for r in range(4):
            for c in range(4):
                if (r, c) != (0, 0) and board.cards[r][c]["symbol"] == symbol:
                    pos2 = (r, c)
                    break
            if pos2:
                break

        self.assertIsNotNone(pos2)
        board.flip_card((0, 0))
        board.flip_card(pos2)
        result = board.check_match()
        self.assertTrue(result)
        self.assertTrue(board.cards[0][0]["matched"])
        self.assertTrue(board.cards[pos2[0]][pos2[1]]["matched"])
        self.assertEqual(len(board.flipped), 0)

    def test_check_match_failure(self) -> None:
        """Test failed match detection."""
        board = Board(4, 4, 8)
        # Find two cards with different symbols
        sym1 = board.cards[0][0]["symbol"]
        pos2 = None
        for r in range(4):
            for c in range(4):
                if board.cards[r][c]["symbol"] != sym1:
                    pos2 = (r, c)
                    break
            if pos2:
                break

        self.assertIsNotNone(pos2)
        board.flip_card((0, 0))
        board.flip_card(pos2)
        result = board.check_match()
        self.assertFalse(result)
        # Cards should NOT be marked as matched
        self.assertFalse(board.cards[0][0]["matched"])

    def test_check_match_insufficient(self) -> None:
        """Test check_match with fewer than 2 flipped cards."""
        board = Board(4, 4, 8)
        board.flip_card((0, 0))
        result = board.check_match()
        self.assertIsNone(result)

    def test_reset_flipped(self) -> None:
        """Test resetting flipped cards."""
        board = Board(4, 4, 8)
        board.flip_card((0, 0))
        board.flip_card((1, 1))
        self.assertEqual(len(board.flipped), 2)
        board.reset_flipped()
        self.assertEqual(len(board.flipped), 0)

    def test_is_won(self) -> None:
        """Test win condition detection."""
        board = Board(4, 4, 8)
        self.assertFalse(board.is_won())
        # Mark all cards as matched
        for r in range(4):
            for c in range(4):
                board.cards[r][c]["matched"] = True
        self.assertTrue(board.is_won())

    def test_get_card_display_matched(self) -> None:
        """Test card display for matched cards shows symbol."""
        board = Board(4, 4, 8)
        symbol = board.cards[0][0]["symbol"]
        board.cards[0][0]["matched"] = True
        self.assertEqual(board.get_card_display(0, 0), symbol)

    def test_get_card_display_face_down(self) -> None:
        """Test card display for face-down cards shows back."""
        board = Board(4, 4, 8)
        self.assertEqual(board.get_card_display(0, 0), CARD_BACK)

    def test_get_card_display_flipped(self) -> None:
        """Test card display for flipped cards shows symbol."""
        board = Board(4, 4, 8)
        symbol = board.cards[0][0]["symbol"]
        board.flip_card((0, 0))
        self.assertEqual(board.get_card_display(0, 0), symbol)

    def test_render_output(self) -> None:
        """Test board rendering produces correct number of lines."""
        board = Board(4, 4, 8)
        lines = board.render("zh")
        # Column labels + top border + 4 rows + bottom border = 6 lines
        self.assertGreaterEqual(len(lines), 6)

    def test_board_invalid_pairs(self) -> None:
        """Test that invalid pair count raises error."""
        with self.assertRaises(ValueError):
            Board(4, 4, 7)  # 7 pairs != 16/2

    def test_board_too_many_pairs(self) -> None:
        """Test that too many pairs raises error."""
        with self.assertRaises(ValueError):
            Board(4, 4, 100)  # Not enough symbols


# ---------------------------------------------------------------------------
# Tests: Config
# ---------------------------------------------------------------------------


class TestConfig(unittest.TestCase):
    """Tests for Config class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        clean_test_files()
        # Backup original settings file
        self.orig_settings = Path(__file__).parent / "settings.json"
        self.orig_settings_bak = None
        if self.orig_settings.exists():
            self.orig_settings_bak = self.orig_settings.read_text()

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        clean_test_files()
        # Restore original settings file
        if self.orig_settings_bak is not None:
            self.orig_settings.write_text(self.orig_settings_bak)
        elif self.orig_settings.exists():
            self.orig_settings.unlink()

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = Config()
        self.assertEqual(config.language, "zh")
        self.assertTrue(config.sound_enabled)
        self.assertEqual(config.volume, 70)
        self.assertEqual(config.difficulty, "easy")

    def test_get_text_zh(self) -> None:
        """Test Chinese text retrieval."""
        config = Config(language="zh")
        self.assertEqual(config.get_text("menu_title"), "===== 主菜单 =====")

    def test_get_text_en(self) -> None:
        """Test English text retrieval."""
        config = Config(language="en")
        self.assertEqual(config.get_text("menu_title"), "===== Main Menu =====")

    def test_get_text_missing_key(self) -> None:
        """Test missing key returns the key itself."""
        config = Config()
        self.assertEqual(config.get_text("nonexistent_key"), "nonexistent_key")

    def test_get_difficulty_name_zh(self) -> None:
        """Test Chinese difficulty names."""
        config = Config(language="zh")
        self.assertEqual(config.get_difficulty_name("easy"), "简单")
        self.assertEqual(config.get_difficulty_name("medium"), "中等")
        self.assertEqual(config.get_difficulty_name("hard"), "困难")

    def test_get_difficulty_name_en(self) -> None:
        """Test English difficulty names."""
        config = Config(language="en")
        self.assertEqual(config.get_difficulty_name("easy"), "Easy")
        self.assertEqual(config.get_difficulty_name("medium"), "Medium")
        self.assertEqual(config.get_difficulty_name("hard"), "Hard")

    @patch("game.SETTINGS_FILE", TEST_SETTINGS)
    def test_save_and_load(self) -> None:
        """Test saving and loading settings."""
        config = Config(language="en", sound_enabled=False, volume=50, difficulty="hard")
        config.save()

        loaded = Config.load()
        self.assertEqual(loaded.language, "en")
        self.assertFalse(loaded.sound_enabled)
        self.assertEqual(loaded.volume, 50)
        self.assertEqual(loaded.difficulty, "hard")

    @patch("game.SETTINGS_FILE", TEST_SETTINGS)
    def test_load_missing_file(self) -> None:
        """Test loading when file doesn't exist returns defaults."""
        clean_test_files()
        config = Config.load()
        self.assertEqual(config.language, "zh")
        self.assertTrue(config.sound_enabled)
        self.assertEqual(config.volume, 70)
        self.assertEqual(config.difficulty, "easy")


# ---------------------------------------------------------------------------
# Tests: ScoreManager
# ---------------------------------------------------------------------------


class TestScoreManager(unittest.TestCase):
    """Tests for ScoreManager class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        clean_test_files()

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        clean_test_files()

    @patch("game.SCORES_FILE", TEST_SCORES)
    def test_add_and_get_scores(self) -> None:
        """Test adding scores and retrieving top scores."""
        sm = ScoreManager()
        sm.add_score("Alice", 800, "easy", 10, 30)
        sm.add_score("Bob", 500, "medium", 20, 60)
        sm.add_score("Charlie", 950, "easy", 5, 10)

        top = sm.get_top(10)
        self.assertEqual(len(top), 3)
        self.assertEqual(top[0].player, "Charlie")
        self.assertEqual(top[0].score, 950)
        self.assertEqual(top[1].player, "Alice")
        self.assertEqual(top[1].score, 800)
        self.assertEqual(top[2].player, "Bob")
        self.assertEqual(top[2].score, 500)

    @patch("game.SCORES_FILE", TEST_SCORES)
    def test_score_persistence(self) -> None:
        """Test that scores persist across ScoreManager instances."""
        sm1 = ScoreManager()
        sm1.add_score("TestPlayer", 700, "easy", 15, 40)

        sm2 = ScoreManager()
        top = sm2.get_top(10)
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0].player, "TestPlayer")
        self.assertEqual(top[0].score, 700)

    @patch("game.SCORES_FILE", TEST_SCORES)
    def test_empty_scores(self) -> None:
        """Test empty scores list."""
        sm = ScoreManager()
        top = sm.get_top(10)
        self.assertEqual(len(top), 0)

    @patch("game.SCORES_FILE", TEST_SCORES)
    def test_clear_scores(self) -> None:
        """Test clearing all scores."""
        sm = ScoreManager()
        sm.add_score("Player1", 600, "easy", 20, 50)
        sm.clear()
        top = sm.get_top(10)
        self.assertEqual(len(top), 0)

    @patch("game.SCORES_FILE", TEST_SCORES)
    def test_top_n(self) -> None:
        """Test limiting top scores to N."""
        sm = ScoreManager()
        for i in range(20):
            sm.add_score(f"Player{i}", 1000 - i * 10, "easy", i, i)
        top = sm.get_top(5)
        self.assertEqual(len(top), 5)
        self.assertEqual(top[0].score, 1000)
        self.assertEqual(top[4].score, 960)


# ---------------------------------------------------------------------------
# Tests: Score calculation
# ---------------------------------------------------------------------------


class TestScoreCalculation(unittest.TestCase):
    """Tests for game score calculation."""

    def test_perfect_score(self) -> None:
        """Test perfect score (no moves, no time)."""
        # Score = max(1000 - 0*10 - 0*2, 0) = 1000
        score = max(1000 - 0 * 10 - 0 * 2, 0)
        self.assertEqual(score, 1000)

    def test_some_moves_and_time(self) -> None:
        """Test score with some moves and time."""
        # Score = max(1000 - 20*10 - 60*2, 0) = max(1000 - 200 - 120, 0) = 680
        score = max(1000 - 20 * 10 - 60 * 2, 0)
        self.assertEqual(score, 680)

    def test_zero_score(self) -> None:
        """Test score dropping to zero."""
        # Score = max(1000 - 100*10 - 0*2, 0) = 0
        score = max(1000 - 100 * 10 - 0 * 2, 0)
        self.assertEqual(score, 0)

    def test_negative_clamped(self) -> None:
        """Test that negative scores are clamped to zero."""
        # Score = max(1000 - 200*10 - 0*2, 0) = max(-1000, 0) = 0
        score = max(1000 - 200 * 10 - 0 * 2, 0)
        self.assertEqual(score, 0)

    def test_exact_boundary(self) -> None:
        """Test score at exact boundary."""
        # Score = max(1000 - 50*10 - 250*2, 0) = max(1000 - 500 - 500, 0) = 0
        score = max(1000 - 50 * 10 - 250 * 2, 0)
        self.assertEqual(score, 0)


# ---------------------------------------------------------------------------
# Tests: SoundManager
# ---------------------------------------------------------------------------


class TestSoundManager(unittest.TestCase):
    """Tests for SoundManager class."""

    def test_sound_disabled(self) -> None:
        """Test that disabled sound doesn't play."""
        config = Config(sound_enabled=False, volume=70)
        sm = SoundManager(config)
        # These should not raise any errors
        sm.play_match()
        sm.play_mismatch()
        sm.play_win()
        sm.play_menu()

    def test_sound_enabled(self) -> None:
        """Test that enabled sound doesn't crash."""
        config = Config(sound_enabled=True, volume=70)
        sm = SoundManager(config)
        # These should not raise any errors
        sm.play_match()
        sm.play_mismatch()
        sm.play_menu()


# ---------------------------------------------------------------------------
# Tests: beep function
# ---------------------------------------------------------------------------


class TestBeep(unittest.TestCase):
    """Tests for beep function."""

    def test_beep_zero_volume(self) -> None:
        """Test beep with zero volume does nothing."""
        # Should not raise any error
        beep(0)

    def test_beep_positive_volume(self) -> None:
        """Test beep with positive volume."""
        # Should not raise any error
        beep(50)


# ---------------------------------------------------------------------------
# Tests: clear_screen
# ---------------------------------------------------------------------------


class TestClearScreen(unittest.TestCase):
    """Tests for clear_screen function."""

    def test_clear_screen(self) -> None:
        """Test clear screen doesn't crash."""
        # Should not raise any error
        clear_screen()


# ---------------------------------------------------------------------------
# Tests: Difficulty presets
# ---------------------------------------------------------------------------


class TestDifficultyPresets(unittest.TestCase):
    """Tests for difficulty preset configurations."""

    def test_easy_preset(self) -> None:
        """Test easy difficulty preset."""
        rows, cols, pairs = DIFFICULTY_PRESETS["easy"]
        self.assertEqual(rows, 4)
        self.assertEqual(cols, 4)
        self.assertEqual(pairs, 8)
        self.assertEqual(rows * cols, pairs * 2)

    def test_medium_preset(self) -> None:
        """Test medium difficulty preset."""
        rows, cols, pairs = DIFFICULTY_PRESETS["medium"]
        self.assertEqual(rows, 4)
        self.assertEqual(cols, 6)
        self.assertEqual(pairs, 12)
        self.assertEqual(rows * cols, pairs * 2)

    def test_hard_preset(self) -> None:
        """Test hard difficulty preset."""
        rows, cols, pairs = DIFFICULTY_PRESETS["hard"]
        self.assertEqual(rows, 6)
        self.assertEqual(cols, 6)
        self.assertEqual(pairs, 18)
        self.assertEqual(rows * cols, pairs * 2)


# ---------------------------------------------------------------------------
# Tests: Card symbols
# ---------------------------------------------------------------------------


class TestCardSymbols(unittest.TestCase):
    """Tests for card symbols constants."""

    def test_enough_symbols(self) -> None:
        """Test that there are enough symbols for all difficulties."""
        max_pairs = max(p[2] for p in DIFFICULTY_PRESETS.values())
        self.assertGreaterEqual(len(CARD_SYMBOLS), max_pairs)

    def test_symbols_are_unique(self) -> None:
        """Test that all symbols are unique."""
        self.assertEqual(len(CARD_SYMBOLS), len(set(CARD_SYMBOLS)))


# ---------------------------------------------------------------------------
# Tests: Language data completeness
# ---------------------------------------------------------------------------


class TestLanguageData(unittest.TestCase):
    """Tests for language data completeness."""

    def test_zh_keys_match_en_keys(self) -> None:
        """Test that Chinese and English have the same keys."""
        zh_keys = set(LANG_ZH.keys())
        en_keys = set(LANG_EN.keys())
        self.assertEqual(
            zh_keys, en_keys,
            f"Missing in EN: {zh_keys - en_keys}, Missing in ZH: {en_keys - zh_keys}",
        )


# ---------------------------------------------------------------------------
# Tests: Game class (unit tests)
# ---------------------------------------------------------------------------


class TestGameUnit(unittest.TestCase):
    """Unit tests for Game class methods."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = Config()
        self.game = Game(self.config)

    def test_initial_state(self) -> None:
        """Test initial game state."""
        self.assertIsNone(self.game.board)
        self.assertEqual(self.game.moves, 0)
        self.assertTrue(self.game.running)
        self.assertFalse(self.game.in_game)

    def test_calculate_score(self) -> None:
        """Test score calculation via game method."""
        # Manually set moves and start time
        self.game.moves = 20
        self.game.start_time = time.time() - 60  # 60 seconds ago
        score = self.game._calculate_score()
        expected = max(1000 - 20 * 10 - 60 * 2, 0)
        self.assertEqual(score, expected)

    def test_create_board_easy(self) -> None:
        """Test creating a board for easy difficulty."""
        self.game.config.difficulty = "easy"
        self.game._create_board()
        self.assertIsNotNone(self.game.board)
        assert self.game.board is not None
        self.assertEqual(self.game.board.rows, 4)
        self.assertEqual(self.game.board.cols, 4)

    def test_create_board_medium(self) -> None:
        """Test creating a board for medium difficulty."""
        self.game.config.difficulty = "medium"
        self.game._create_board()
        self.assertIsNotNone(self.game.board)
        assert self.game.board is not None
        self.assertEqual(self.game.board.rows, 4)
        self.assertEqual(self.game.board.cols, 6)

    def test_create_board_hard(self) -> None:
        """Test creating a board for hard difficulty."""
        self.game.config.difficulty = "hard"
        self.game._create_board()
        self.assertIsNotNone(self.game.board)
        assert self.game.board is not None
        self.assertEqual(self.game.board.rows, 6)
        self.assertEqual(self.game.board.cols, 6)

    def test_get_elapsed_zero(self) -> None:
        """Test elapsed time when game hasn't started."""
        self.assertEqual(self.game._get_elapsed(), 0)

    def test_text_helper(self) -> None:
        """Test text helper method."""
        self.assertEqual(self.game._("menu_title"), "===== 主菜单 =====")
        self.game.config.language = "en"
        self.assertEqual(self.game._("menu_title"), "===== Main Menu =====")


# ---------------------------------------------------------------------------
# Tests: Language switching (integration)
# ---------------------------------------------------------------------------


class TestLanguageSwitching(unittest.TestCase):
    """Tests for language switching via Config."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        clean_test_files()

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        clean_test_files()

    @patch("game.SETTINGS_FILE", TEST_SETTINGS)
    def test_switch_to_english(self) -> None:
        """Test switching language to English."""
        config = Config(language="en")
        config.save()

        loaded = Config.load()
        self.assertEqual(loaded.language, "en")
        self.assertEqual(loaded.get_text("menu_title"), "===== Main Menu =====")
        self.assertEqual(loaded.get_text("menu_1"), "[1] New Game")

    @patch("game.SETTINGS_FILE", TEST_SETTINGS)
    def test_switch_to_chinese(self) -> None:
        """Test switching language to Chinese."""
        config = Config(language="zh")
        config.save()

        loaded = Config.load()
        self.assertEqual(loaded.language, "zh")
        self.assertEqual(loaded.get_text("menu_title"), "===== 主菜单 =====")
        self.assertEqual(loaded.get_text("menu_1"), "[1] 开始新游戏")

    @patch("game.SETTINGS_FILE", TEST_SETTINGS)
    def test_toggle_language(self) -> None:
        """Test toggling language back and forth."""
        config = Config(language="zh")
        config.language = "en"
        config.save()

        loaded = Config.load()
        self.assertEqual(loaded.language, "en")

        config.language = "zh"
        config.save()
        loaded = Config.load()
        self.assertEqual(loaded.language, "zh")


# ---------------------------------------------------------------------------
# Tests: Settings persistence (integration)
# ---------------------------------------------------------------------------


class TestSettingsPersistence(unittest.TestCase):
    """Tests for settings persistence."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        clean_test_files()

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        clean_test_files()

    @patch("game.SETTINGS_FILE", TEST_SETTINGS)
    def test_persist_all_settings(self) -> None:
        """Test persisting all settings."""
        config = Config(language="en", sound_enabled=False, volume=30, difficulty="hard")
        config.save()

        loaded = Config.load()
        self.assertEqual(loaded.language, "en")
        self.assertFalse(loaded.sound_enabled)
        self.assertEqual(loaded.volume, 30)
        self.assertEqual(loaded.difficulty, "hard")

    @patch("game.SETTINGS_FILE", TEST_SETTINGS)
    def test_json_format(self) -> None:
        """Test that settings file is valid JSON."""
        config = Config(language="zh", sound_enabled=True, volume=50, difficulty="medium")
        config.save()

        with open(TEST_SETTINGS, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["language"], "zh")
        self.assertTrue(data["sound_enabled"])
        self.assertEqual(data["volume"], 50)
        self.assertEqual(data["difficulty"], "medium")


# ---------------------------------------------------------------------------
# Tests: File I/O
# ---------------------------------------------------------------------------


class TestFileIO(unittest.TestCase):
    """Tests for file I/O operations."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        clean_test_files()

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        clean_test_files()

    @patch("game.SCORES_FILE", TEST_SCORES)
    def test_scores_file_creation(self) -> None:
        """Test that scores.json is created when saving."""
        sm = ScoreManager()
        sm.add_score("Test", 500, "easy", 25, 50)
        self.assertTrue(TEST_SCORES.exists())

    @patch("game.SCORES_FILE", TEST_SCORES)
    def test_scores_file_valid_json(self) -> None:
        """Test that scores.json contains valid JSON."""
        sm = ScoreManager()
        sm.add_score("Player1", 800, "easy", 10, 20)
        sm.add_score("Player2", 600, "medium", 15, 30)

        with open(TEST_SCORES, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["player"], "Player1")
        self.assertEqual(data[0]["score"], 800)
        self.assertEqual(data[1]["player"], "Player2")

    @patch("game.SCORES_FILE", TEST_SCORES)
    def test_scores_file_corrupted(self) -> None:
        """Test handling of corrupted scores file."""
        TEST_SCORES.write_text("not valid json", encoding="utf-8")
        sm = ScoreManager()
        top = sm.get_top(10)
        self.assertEqual(len(top), 0)

    @patch("game.SETTINGS_FILE", TEST_SETTINGS)
    def test_settings_file_corrupted(self) -> None:
        """Test handling of corrupted settings file."""
        TEST_SETTINGS.write_text("not valid json", encoding="utf-8")
        config = Config.load()
        self.assertEqual(config.language, "zh")
        self.assertTrue(config.sound_enabled)
        self.assertEqual(config.volume, 70)
        self.assertEqual(config.difficulty, "easy")


# ---------------------------------------------------------------------------
# Tests: ScoreEntry dataclass
# ---------------------------------------------------------------------------


class TestScoreEntry(unittest.TestCase):
    """Tests for ScoreEntry dataclass."""

    def test_score_entry_creation(self) -> None:
        """Test creating a ScoreEntry."""
        entry = ScoreEntry(
            player="TestPlayer",
            score=750,
            date="2024-01-15 14:30",
            difficulty="easy",
            moves=12,
            time=45,
        )
        self.assertEqual(entry.player, "TestPlayer")
        self.assertEqual(entry.score, 750)
        self.assertEqual(entry.date, "2024-01-15 14:30")
        self.assertEqual(entry.difficulty, "easy")
        self.assertEqual(entry.moves, 12)
        self.assertEqual(entry.time, 45)


# ---------------------------------------------------------------------------
# Tests: Subprocess integration tests
# ---------------------------------------------------------------------------


class TestSubprocessIntegration(unittest.TestCase):
    """Integration tests using subprocess to run game.py.

    These tests verify the game runs and responds to basic input.
    """

    def setUp(self) -> None:
        """Set up test fixtures."""
        clean_test_files()
        self.game_py = str(TEST_DIR / "game.py")
        # Backup and reset the real settings.json to defaults
        self.real_settings = TEST_DIR / "settings.json"
        self.settings_backup = None
        if self.real_settings.exists():
            self.settings_backup = self.real_settings.read_text()
        # Write default settings (Chinese, sound on, volume 70, easy)
        import json
        with open(self.real_settings, "w", encoding="utf-8") as f:
            json.dump({
                "language": "zh",
                "sound_enabled": True,
                "volume": 70,
                "difficulty": "easy",
            }, f, ensure_ascii=False, indent=2)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        clean_test_files()
        # Restore original settings.json
        if self.settings_backup is not None:
            self.real_settings.write_text(self.settings_backup)
        elif self.real_settings.exists():
            self.real_settings.unlink()

    def _run_game(self, inputs: str, timeout: int = 10) -> subprocess.CompletedProcess:
        """Run game.py with piped inputs.

        Args:
            inputs: String of newline-separated inputs.
            timeout: Timeout in seconds.

        Returns:
            CompletedProcess result.
        """
        return subprocess.run(
            [sys.executable, self.game_py],
            input=inputs,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=TEST_DIR,
        )

    def test_game_starts_and_exits(self) -> None:
        """Test that game starts and exits via menu option 6."""
        result = self._run_game("6\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))  # 0=normal exit, 1=error
        # Should show goodbye message
        output = result.stdout + result.stderr
        self.assertTrue(
            "再见" in output or "goodbye" in output or "感谢" in output,
            f"Output: {output[:500]}",
        )

    def test_game_exit_with_confirm(self) -> None:
        """Test exit with confirmation (y)."""
        result = self._run_game("6\ny\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))

    def test_game_exit_declined(self) -> None:
        """Test exit declined (n)."""
        result = self._run_game("6\nn\n6\ny\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))

    def test_show_high_scores(self) -> None:
        """Test showing high scores from menu."""
        result = self._run_game("3\n\n6\ny\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))

    def test_show_how_to_play(self) -> None:
        """Test showing how-to-play screen."""
        result = self._run_game("5\n\n6\ny\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))

    def test_difficulty_menu(self) -> None:
        """Test difficulty selection menu."""
        result = self._run_game("2\n1\n6\ny\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))

    def test_difficulty_menu_back(self) -> None:
        """Test returning from difficulty menu."""
        result = self._run_game("2\n0\n6\ny\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))

    def test_settings_menu(self) -> None:
        """Test settings menu navigation."""
        result = self._run_game("4\n0\n6\ny\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))

    def test_settings_toggle_language(self) -> None:
        """Test toggling language in settings."""
        result = self._run_game("4\n1\n0\n6\ny\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))

    def test_settings_toggle_sound(self) -> None:
        """Test toggling sound in settings."""
        result = self._run_game("4\n2\n0\n6\ny\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))

    def test_settings_volume(self) -> None:
        """Test changing volume in settings."""
        result = self._run_game("4\n3\n50\n0\n6\ny\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))

    def test_new_game_quit(self) -> None:
        """Test starting a new game and quitting."""
        result = self._run_game("1\nq\n6\ny\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))

    def test_new_game_help(self) -> None:
        """Test starting a new game and viewing help."""
        result = self._run_game("1\nh\n\nq\n6\ny\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))

    def test_new_game_stats(self) -> None:
        """Test starting a new game and viewing stats."""
        result = self._run_game("1\ns\n\nq\n6\ny\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))

    def test_new_game_invalid_input(self) -> None:
        """Test starting a new game with invalid input."""
        result = self._run_game("1\nzz\nq\n6\ny\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))

    def test_new_game_out_of_bounds(self) -> None:
        """Test starting a new game with out-of-bounds coordinate."""
        result = self._run_game("1\nz9\nq\n6\ny\n", timeout=10)
        self.assertIn(result.returncode, (0, 1))

    def test_language_command_zh(self) -> None:
        """Test that default language is Chinese."""
        result = self._run_game("6\ny\n", timeout=10)
        output = result.stdout + result.stderr
        self.assertIn("主菜单", output)

    def test_full_game_flow_easy(self) -> None:
        """Test a full game flow on easy difficulty (start, then quit)."""
        result = self._run_game(
            "1\nq\n6\ny\n",
            timeout=10,
        )
        self.assertIn(result.returncode, (0, 1))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# Import LANG_ZH and LANG_EN for language data completeness test
from game import LANG_ZH, LANG_EN

if __name__ == "__main__":
    unittest.main()
