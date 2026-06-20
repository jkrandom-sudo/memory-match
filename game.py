#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Match Card Game
A console-based memory match game playable entirely in the terminal.
Supports Chinese (default) and English, score persistence, sound effects,
and multiple difficulty levels.
"""

import json
import os
import random
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GAME_VERSION = "1.0.0"
DATA_DIR = Path(__file__).parent
SETTINGS_FILE = DATA_DIR / "settings.json"
SCORES_FILE = DATA_DIR / "scores.json"

# Card symbols (emoji) used for card faces
CARD_SYMBOLS: List[str] = [
    "🍎", "🍊", "🍋", "🍇", "🍓", "🍒", "🍑", "🥝",
    "🍌", "🍉", "🍍", "🥭", "🍈", "🫐", "🥥", "🍅",
    "🌽", "🥕", "🥦", "🥬", "🍄", "🌶️", "🥒", "🧅",
    "🧄", "🥜", "🌰", "🍞", "🧀", "🥚", "🧈", "🥞",
]

# Difficulty presets: (rows, cols, pairs)
DIFFICULTY_PRESETS: Dict[str, Tuple[int, int, int]] = {
    "easy": (4, 4, 8),
    "medium": (4, 6, 12),
    "hard": (6, 6, 18),
}

DIFFICULTY_NAMES_ZH: Dict[str, str] = {"easy": "简单", "medium": "中等", "hard": "困难"}
DIFFICULTY_NAMES_EN: Dict[str, str] = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}

# Box-drawing characters
BOX_H = "─"
BOX_V = "│"
BOX_TL = "┌"
BOX_TR = "┐"
BOX_BL = "└"
BOX_BR = "┘"
BOX_TM = "┬"
BOX_BM = "┴"
BOX_ML = "├"
BOX_MR = "┤"
BOX_MM = "┼"

# Card back display
CARD_BACK = "❓"

# ---------------------------------------------------------------------------
# Language data
# ---------------------------------------------------------------------------

LANG_ZH: Dict[str, str] = {
    "title": "记忆配对游戏 v{}",
    "menu_title": "===== 主菜单 =====",
    "menu_1": "[1] 开始新游戏",
    "menu_2": "[2] 选择难度",
    "menu_3": "[3] 高分榜",
    "menu_4": "[4] 设置",
    "menu_5": "[5] 玩法说明",
    "menu_6": "[6] 退出游戏",
    "prompt_choice": "请选择 (1-6): ",
    "current_difficulty": "当前难度: {}",
    "select_difficulty": "===== 选择难度 =====",
    "diff_1": "[1] 简单 (4×4, 8对)",
    "diff_2": "[2] 中等 (4×6, 12对)",
    "diff_3": "[3] 困难 (6×6, 18对)",
    "diff_0": "[0] 返回主菜单",
    "diff_prompt": "请选择难度 (0-3): ",
    "difficulty_set": "难度已设置为: {}",
    "settings_title": "===== 设置 =====",
    "settings_lang": "[1] 语言切换 (当前: {})",
    "settings_sound": "[2] 声音: {}",
    "settings_volume": "[3] 音量: {}",
    "settings_0": "[0] 返回主菜单",
    "settings_prompt": "请选择 (0-3): ",
    "lang_set": "语言已切换为: {}",
    "sound_on": "开",
    "sound_off": "关",
    "volume_prompt": "请输入音量 (0-100): ",
    "volume_set": "音量已设置为: {}",
    "high_scores_title": "===== 高分榜 (前10) =====",
    "high_scores_empty": "暂无记录，快去玩一局吧！",
    "high_scores_header": "{:<4} {:<12} {:<8} {:<10} {:<6} {:<6} {:<8}",
    "high_scores_row": "{:<4} {:<12} {:<8} {:<10} {:<6} {:<6} {:<8}",
    "high_scores_star": "⭐",
    "high_scores_prompt": "按 Enter 返回主菜单...",
    "how_to_play_title": "===== 玩法说明 =====",
    "how_to_play_rules": [
        "游戏目标: 翻开所有配对的卡片。",
        "每次选择两张卡片，如果图案相同则配对成功，否则翻回背面。",
        "用尽可能少的步数和时间完成所有配对。",
        "",
        "=== 控制说明 ===",
        "选择卡片: 输入行列坐标，如 'a1' 表示第A列第1行",
        "  p / pause  - 暂停/继续游戏",
        "  q / quit   - 退出到主菜单",
        "  h / help   - 显示帮助",
        "  s          - 显示当前状态",
        "  r          - 重新开始当前游戏",
        "",
        "=== 计分规则 ===",
        "基础分 = 1000",
        "每步扣10分，每秒扣2分",
        "最终得分 = max(基础分 - 步数×10 - 秒数×2, 0)",
        "",
        "=== 难度说明 ===",
        "简单 (4×4): 8对，共16张卡片",
        "中等 (4×6): 12对，共24张卡片",
        "困难 (6×6): 18对，共36张卡片",
    ],
    "how_to_play_prompt": "按 Enter 返回主菜单...",
    "game_board_title": "===== 记忆配对游戏 =====",
    "game_stats": "步数: {}  |  已配对: {}/{}  |  时间: {}",
    "game_prompt": "请输入卡片坐标 (如 a1)，或输入 h 查看帮助: ",
    "card_flipped": "已翻开: {} 和 {}",
    "card_match": "🎉 配对成功！",
    "card_mismatch": "❌ 不匹配，请记住它们的位置...",
    "game_paused": "⏸️  游戏已暂停。按 Enter 继续...",
    "game_resumed": "▶️  游戏继续！",
    "game_won_title": "🎊🎊🎊 恭喜通关！ 🎊🎊🎊",
    "game_won_stats": "步数: {}  |  用时: {}  |  得分: {}",
    "game_won_prompt_name": "请输入你的名字 (默认: 玩家): ",
    "game_won_prompt_continue": "按 Enter 返回主菜单...",
    "invalid_input": "输入无效，请重新输入。",
    "invalid_coord": "坐标无效，请使用字母+数字格式，如 a1",
    "out_of_bounds": "坐标超出范围，请重新输入。",
    "already_flipped": "该卡片已翻开，请选择其他卡片。",
    "already_matched": "该卡片已配对成功，请选择其他卡片。",
    "ctrl_c_confirm": "确定要退出游戏吗？(y/n): ",
    "ctrl_c_exit": "再见！",
    "enter_continue": "按 Enter 继续...",
    "sound_label": "声音",
    "volume_label": "音量",
    "language_label": "语言",
    "language_zh": "中文",
    "language_en": "English",
    "error_save_scores": "保存分数时出错: {}",
    "error_load_scores": "加载分数时出错: {}",
    "error_save_settings": "保存设置时出错: {}",
    "error_load_settings": "加载设置时出错: {}",
    "player_name": "玩家",
    "confirm_restart": "确定要重新开始吗？当前进度将丢失。(y/n): ",
    "game_restarted": "游戏已重新开始！",
    "show_scores_cmd": "输入 'show scores' 查看高分榜",
    "no_command": "未知命令。输入 h 查看帮助。",
    "volume_range_error": "音量必须在 0-100 之间。",
    "lang_zh_name": "中文",
    "lang_en_name": "English",
    "exit_confirm": "确定要退出游戏吗？(y/n): ",
    "goodbye": "感谢游玩，再见！",
}

LANG_EN: Dict[str, str] = {
    "title": "Memory Match Game v{}",
    "menu_title": "===== Main Menu =====",
    "menu_1": "[1] New Game",
    "menu_2": "[2] Select Difficulty",
    "menu_3": "[3] High Scores",
    "menu_4": "[4] Settings",
    "menu_5": "[5] How to Play",
    "menu_6": "[6] Exit",
    "prompt_choice": "Choose (1-6): ",
    "current_difficulty": "Current Difficulty: {}",
    "select_difficulty": "===== Select Difficulty =====",
    "diff_1": "[1] Easy (4×4, 8 pairs)",
    "diff_2": "[2] Medium (4×6, 12 pairs)",
    "diff_3": "[3] Hard (6×6, 18 pairs)",
    "diff_0": "[0] Back to Main Menu",
    "diff_prompt": "Choose difficulty (0-3): ",
    "difficulty_set": "Difficulty set to: {}",
    "settings_title": "===== Settings =====",
    "settings_lang": "[1] Language (Current: {})",
    "settings_sound": "[2] Sound: {}",
    "settings_volume": "[3] Volume: {}",
    "settings_0": "[0] Back to Main Menu",
    "settings_prompt": "Choose (0-3): ",
    "lang_set": "Language switched to: {}",
    "sound_on": "ON",
    "sound_off": "OFF",
    "volume_prompt": "Enter volume (0-100): ",
    "volume_set": "Volume set to: {}",
    "high_scores_title": "===== High Scores (Top 10) =====",
    "high_scores_empty": "No records yet. Go play a game!",
    "high_scores_header": "{:<4} {:<12} {:<8} {:<10} {:<6} {:<6} {:<8}",
    "high_scores_row": "{:<4} {:<12} {:<8} {:<10} {:<6} {:<6} {:<8}",
    "high_scores_star": "⭐",
    "high_scores_prompt": "Press Enter to return to main menu...",
    "how_to_play_title": "===== How to Play =====",
    "how_to_play_rules": [
        "Goal: Flip all matching card pairs.",
        "Select two cards each turn. If they match, they stay face-up.",
        "Complete all pairs with as few moves and as little time as possible.",
        "",
        "=== Controls ===",
        "Select card: Enter column+row, e.g. 'a1' = column A, row 1",
        "  p / pause  - Pause/Resume game",
        "  q / quit   - Exit to main menu",
        "  h / help   - Show this help",
        "  s          - Show current stats",
        "  r          - Restart current game",
        "",
        "=== Scoring ===",
        "Base score = 1000",
        "Deduct 10 per move, 2 per second",
        "Final score = max(1000 - moves×10 - seconds×2, 0)",
        "",
        "=== Difficulty ===",
        "Easy (4×4): 8 pairs, 16 cards",
        "Medium (4×6): 12 pairs, 24 cards",
        "Hard (6×6): 18 pairs, 36 cards",
    ],
    "how_to_play_prompt": "Press Enter to return to main menu...",
    "game_board_title": "===== Memory Match Game =====",
    "game_stats": "Moves: {}  |  Matched: {}/{}  |  Time: {}",
    "game_prompt": "Enter card coordinates (e.g. a1), or h for help: ",
    "card_flipped": "Flipped: {} and {}",
    "card_match": "🎉 Match!",
    "card_mismatch": "❌ No match, remember their positions...",
    "game_paused": "⏸️  Game paused. Press Enter to continue...",
    "game_resumed": "▶️  Game resumed!",
    "game_won_title": "🎊🎊🎊 Congratulations! 🎊🎊🎊",
    "game_won_stats": "Moves: {}  |  Time: {}  |  Score: {}",
    "game_won_prompt_name": "Enter your name (default: Player): ",
    "game_won_prompt_continue": "Press Enter to return to main menu...",
    "invalid_input": "Invalid input, please try again.",
    "invalid_coord": "Invalid coordinate. Use letter+number format, e.g. a1",
    "out_of_bounds": "Coordinate out of bounds, please try again.",
    "already_flipped": "Card already flipped, choose another.",
    "already_matched": "Card already matched, choose another.",
    "ctrl_c_confirm": "Are you sure you want to exit? (y/n): ",
    "ctrl_c_exit": "Goodbye!",
    "enter_continue": "Press Enter to continue...",
    "sound_label": "Sound",
    "volume_label": "Volume",
    "language_label": "Language",
    "language_zh": "中文",
    "language_en": "English",
    "error_save_scores": "Error saving scores: {}",
    "error_load_scores": "Error loading scores: {}",
    "error_save_settings": "Error saving settings: {}",
    "error_load_settings": "Error loading settings: {}",
    "player_name": "Player",
    "confirm_restart": "Are you sure you want to restart? Progress will be lost. (y/n): ",
    "game_restarted": "Game restarted!",
    "show_scores_cmd": "Type 'show scores' to view high scores",
    "no_command": "Unknown command. Type h for help.",
    "volume_range_error": "Volume must be between 0-100.",
    "lang_zh_name": "中文",
    "lang_en_name": "English",
    "exit_confirm": "Are you sure you want to exit? (y/n): ",
    "goodbye": "Thanks for playing, goodbye!",
}

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def clear_screen() -> None:
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def format_time(seconds: int) -> str:
    """Format seconds into MM:SS string.

    Args:
        seconds: Total seconds.

    Returns:
        Formatted time string like "03:45".
    """
    m, s = divmod(max(0, seconds), 60)
    return f"{m:02d}:{s:02d}"


def beep(volume: int = 70) -> None:
    """Play a console beep sound.

    Args:
        volume: Volume level 0-100. 0 = silent.
    """
    if volume <= 0:
        return
    # Use system bell character
    try:
        sys.stdout.write("\x07")
        sys.stdout.flush()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Config class
# ---------------------------------------------------------------------------


@dataclass
class Config:
    """Game configuration and settings management.

    Handles persistence of user preferences (language, sound, volume)
    to settings.json.
    """

    language: str = "zh"
    sound_enabled: bool = True
    volume: int = 70
    difficulty: str = "easy"

    @classmethod
    def load(cls) -> "Config":
        """Load settings from settings.json file.

        Returns:
            Config instance with loaded or default values.
        """
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(
                    language=data.get("language", "zh"),
                    sound_enabled=data.get("sound_enabled", True),
                    volume=data.get("volume", 70),
                    difficulty=data.get("difficulty", "easy"),
                )
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading settings: {e}")
        return cls()

    def save(self) -> None:
        """Save current settings to settings.json file."""
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "language": self.language,
                        "sound_enabled": self.sound_enabled,
                        "volume": self.volume,
                        "difficulty": self.difficulty,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except OSError as e:
            print(f"Error saving settings: {e}")

    def get_text(self, key: str) -> str:
        """Get localized text string for the given key.

        Args:
            key: The text key to look up.

        Returns:
            Localized string, or the key itself if not found.
        """
        lang_data = LANG_ZH if self.language == "zh" else LANG_EN
        return lang_data.get(key, key)

    def get_difficulty_name(self, diff: Optional[str] = None) -> str:
        """Get localized difficulty name.

        Args:
            diff: Difficulty key ('easy', 'medium', 'hard'). Defaults to current.

        Returns:
            Localized difficulty name.
        """
        diff = diff or self.difficulty
        if self.language == "zh":
            return DIFFICULTY_NAMES_ZH.get(diff, diff)
        return DIFFICULTY_NAMES_EN.get(diff, diff)


# ---------------------------------------------------------------------------
# LanguageManager
# ---------------------------------------------------------------------------


class LanguageManager:
    """Manages language switching and provides localized strings."""

    def __init__(self, config: Config) -> None:
        """Initialize language manager.

        Args:
            config: Game configuration with language setting.
        """
        self.config = config

    def get_text(self, key: str) -> str:
        """Get localized text.

        Args:
            key: Text key.

        Returns:
            Localized string.
        """
        return self.config.get_text(key)

    @property
    def lang_name(self) -> str:
        """Get the display name of the current language."""
        if self.config.language == "zh":
            return "中文"
        return "English"


# ---------------------------------------------------------------------------
# SoundManager
# ---------------------------------------------------------------------------


class SoundManager:
    """Manages game sound effects with volume control."""

    def __init__(self, config: Config) -> None:
        """Initialize sound manager.

        Args:
            config: Game configuration with sound settings.
        """
        self.config = config

    def play_match(self) -> None:
        """Play sound on successful card match."""
        if self.config.sound_enabled:
            beep(self.config.volume)

    def play_mismatch(self) -> None:
        """Play sound on card mismatch (lower pitch)."""
        if self.config.sound_enabled:
            beep(max(self.config.volume - 20, 0))

    def play_win(self) -> None:
        """Play victory sound (multiple beeps)."""
        if self.config.sound_enabled:
            for _ in range(3):
                beep(self.config.volume)
                time.sleep(0.15)

    def play_menu(self) -> None:
        """Play sound on menu navigation."""
        if self.config.sound_enabled:
            beep(max(self.config.volume - 30, 0))


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------


class Board:
    """Represents the game board with cards.

    Handles card generation, shuffling, flipping, and display.
    """

    def __init__(self, rows: int, cols: int, pairs: int) -> None:
        """Initialize board with given dimensions.

        Args:
            rows: Number of rows.
            cols: Number of columns.
            pairs: Number of matching pairs.

        Raises:
            ValueError: If pairs exceed available symbols or grid capacity.
        """
        self.rows = rows
        self.cols = cols
        self.pairs = pairs
        self.total_cards = rows * cols

        if pairs > len(CARD_SYMBOLS):
            raise ValueError(f"Not enough symbols: need {pairs}, have {len(CARD_SYMBOLS)}")
        if pairs * 2 != self.total_cards:
            raise ValueError(f"Grid size {rows}x{cols}={self.total_cards} doesn't match {pairs} pairs")

        # Card state: each card is a dict with 'symbol' (str) and 'matched' (bool)
        self.cards: List[List[Dict]] = []
        # Track which cards are currently flipped (not yet matched)
        self.flipped: List[Tuple[int, int]] = []
        self._generate_cards()

    def _generate_cards(self) -> None:
        """Generate and shuffle card positions on the board."""
        symbols = random.sample(CARD_SYMBOLS, self.pairs)
        deck = symbols * 2  # Two of each symbol
        random.shuffle(deck)

        self.cards = []
        idx = 0
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                row.append({"symbol": deck[idx], "matched": False})
                idx += 1
            self.cards.append(row)

    def is_valid_coord(self, coord_str: str) -> Optional[Tuple[int, int]]:
        """Parse and validate a coordinate string like 'a1', 'b3'.

        Args:
            coord_str: Coordinate string (e.g. 'a1', 'b3').

        Returns:
            (row, col) tuple if valid, None otherwise.
        """
        coord_str = coord_str.strip().lower()
        if len(coord_str) < 2:
            return None

        col_char = coord_str[0]
        row_part = coord_str[1:]

        if not col_char.isalpha():
            return None
        if not row_part.isdigit():
            return None

        col = ord(col_char) - ord("a")
        row = int(row_part) - 1

        if row < 0 or row >= self.rows or col < 0 or col >= self.cols:
            return None

        return (row, col)

    def flip_card(self, pos: Tuple[int, int]) -> Optional[str]:
        """Flip a card at the given position.

        Args:
            pos: (row, col) tuple.

        Returns:
            Card symbol if successfully flipped, None if already flipped/matched.
        """
        r, c = pos
        card = self.cards[r][c]
        if card["matched"]:
            return None
        if pos in self.flipped:
            return None
        self.flipped.append(pos)
        return card["symbol"]

    def check_match(self) -> Optional[bool]:
        """Check if the two currently flipped cards match.

        Returns:
            True if match, False if mismatch, None if less than 2 flipped.
        """
        if len(self.flipped) < 2:
            return None

        pos1, pos2 = self.flipped[0], self.flipped[1]
        card1 = self.cards[pos1[0]][pos1[1]]
        card2 = self.cards[pos2[0]][pos2[1]]

        if card1["symbol"] == card2["symbol"]:
            card1["matched"] = True
            card2["matched"] = True
            self.flipped.clear()
            return True
        else:
            return False

    def reset_flipped(self) -> None:
        """Clear the flipped cards list (flip them back face-down)."""
        self.flipped.clear()

    def is_won(self) -> bool:
        """Check if all cards are matched.

        Returns:
            True if all pairs have been matched.
        """
        for row in self.cards:
            for card in row:
                if not card["matched"]:
                    return False
        return True

    def get_card_display(self, r: int, c: int) -> str:
        """Get the display string for a card at given position.

        Args:
            r: Row index.
            c: Column index.

        Returns:
            Card symbol if matched or flipped, otherwise card back.
        """
        card = self.cards[r][c]
        if card["matched"] or (r, c) in self.flipped:
            return card["symbol"]
        return CARD_BACK

    def render(self, lang: str = "zh") -> List[str]:
        """Render the board as a list of strings for display.

        Args:
            lang: Language code ('zh' or 'en').

        Returns:
            List of strings representing the board rows.
        """
        lines: List[str] = []

        # Column labels
        col_labels = "   " + " ".join(f" {chr(65 + c)} " for c in range(self.cols))
        lines.append(col_labels)

        # Top border
        top = "  " + BOX_TL + (BOX_TM + BOX_H * 3) * self.cols + BOX_TR
        lines.append(top)

        for r in range(self.rows):
            # Row label + card row
            row_content = f"{r + 1:2d} {BOX_V}"
            for c in range(self.cols):
                display = self.get_card_display(r, c)
                row_content += f" {display} {BOX_V}"
            lines.append(row_content)

            # Bottom border for this row
            if r < self.rows - 1:
                sep = "  " + BOX_ML + (BOX_MM + BOX_H * 3) * self.cols + BOX_MR
                lines.append(sep)
            else:
                bottom = "  " + BOX_BL + (BOX_BM + BOX_H * 3) * self.cols + BOX_BR
                lines.append(bottom)

        return lines


# ---------------------------------------------------------------------------
# ScoreManager
# ---------------------------------------------------------------------------


@dataclass
class ScoreEntry:
    """A single score entry."""

    player: str
    score: int
    date: str
    difficulty: str
    moves: int
    time: int  # seconds


class ScoreManager:
    """Manages high scores persistence to scores.json."""

    def __init__(self) -> None:
        """Initialize score manager."""
        self.scores: List[ScoreEntry] = []
        self.load()

    def load(self) -> None:
        """Load scores from scores.json file."""
        try:
            if SCORES_FILE.exists():
                with open(SCORES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.scores = [
                    ScoreEntry(
                        player=item.get("player", "玩家"),
                        score=item.get("score", 0),
                        date=item.get("date", ""),
                        difficulty=item.get("difficulty", "easy"),
                        moves=item.get("moves", 0),
                        time=item.get("time", 0),
                    )
                    for item in data
                ]
                # Sort by score descending
                self.scores.sort(key=lambda x: x.score, reverse=True)
        except (json.JSONDecodeError, OSError):
            self.scores = []

    def save(self) -> None:
        """Save scores to scores.json file."""
        try:
            data = [
                {
                    "player": s.player,
                    "score": s.score,
                    "date": s.date,
                    "difficulty": s.difficulty,
                    "moves": s.moves,
                    "time": s.time,
                }
                for s in self.scores
            ]
            with open(SCORES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"Error saving scores: {e}")

    def add_score(
        self,
        player: str,
        score: int,
        difficulty: str,
        moves: int,
        time_seconds: int,
    ) -> None:
        """Add a new score entry.

        Args:
            player: Player name.
            score: Calculated score.
            difficulty: Difficulty level.
            moves: Number of moves taken.
            time_seconds: Time in seconds.
        """
        entry = ScoreEntry(
            player=player,
            score=score,
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            difficulty=difficulty,
            moves=moves,
            time=time_seconds,
        )
        self.scores.append(entry)
        self.scores.sort(key=lambda x: x.score, reverse=True)
        self.save()

    def get_top(self, n: int = 10) -> List[ScoreEntry]:
        """Get top N scores.

        Args:
            n: Number of top scores to return.

        Returns:
            List of top ScoreEntry objects.
        """
        return self.scores[:n]

    def clear(self) -> None:
        """Clear all scores."""
        self.scores.clear()
        self.save()


# ---------------------------------------------------------------------------
# Game class
# ---------------------------------------------------------------------------


class Game:
    """Main game class handling game loop, input, and state management."""

    def __init__(self, config: Config) -> None:
        """Initialize game with configuration.

        Args:
            config: Game configuration.
        """
        self.config = config
        self.lang = LanguageManager(config)
        self.sound = SoundManager(config)
        self.score_manager = ScoreManager()
        self.board: Optional[Board] = None
        self.moves: int = 0
        self.start_time: float = 0.0
        self.paused_time: float = 0.0
        self.total_paused: float = 0.0
        self.is_paused: bool = False
        self.running: bool = True
        self.in_game: bool = False

    # ---- Text helpers ----

    def _(self, key: str) -> str:
        """Shorthand for getting localized text.

        Args:
            key: Text key.

        Returns:
            Localized string.
        """
        return self.lang.get_text(key)

    # ---- Sound helpers ----

    def _beep_match(self) -> None:
        """Play match sound."""
        self.sound.play_match()

    def _beep_mismatch(self) -> None:
        """Play mismatch sound."""
        self.sound.play_mismatch()

    def _beep_win(self) -> None:
        """Play win sound."""
        self.sound.play_win()

    def _beep_menu(self) -> None:
        """Play menu navigation sound."""
        self.sound.play_menu()

    # ---- Board management ----

    def _create_board(self) -> None:
        """Create a new board based on current difficulty setting."""
        diff = self.config.difficulty
        rows, cols, pairs = DIFFICULTY_PRESETS[diff]
        self.board = Board(rows, cols, pairs)

    def _reset_game_state(self) -> None:
        """Reset all game state variables for a new game."""
        self.moves = 0
        self.start_time = time.time()
        self.paused_time = 0.0
        self.total_paused = 0.0
        self.is_paused = False
        self.in_game = True

    # ---- Display ----

    def _display_board(self) -> None:
        """Display the current board state with stats."""
        clear_screen()
        assert self.board is not None
        elapsed = self._get_elapsed()
        matched = sum(
            1 for row in self.board.cards for card in row if card["matched"]
        )
        total = self.board.total_cards

        print(f"\n  {self._('game_board_title')}")
        print(
            f"  {self._('game_stats').format(self.moves, matched, total, format_time(elapsed))}"
        )
        print()
        for line in self.board.render(self.config.language):
            print(f"  {line}")
        print()

    def _get_elapsed(self) -> int:
        """Get elapsed game time in seconds (excluding paused time).

        Returns:
            Elapsed seconds.
        """
        if self.start_time == 0:
            return 0
        return int(time.time() - self.start_time - self.total_paused)

    # ---- Game loop ----

    def _parse_input(self, user_input: str) -> Optional[Tuple[int, int]]:
        """Parse user input into board coordinates.

        Args:
            user_input: Raw input string.

        Returns:
            (row, col) tuple or None if invalid.
        """
        assert self.board is not None
        coord = self.board.is_valid_coord(user_input)
        if coord is None:
            print(f"  {self._('invalid_coord')}")
            return None

        r, c = coord
        card = self.board.cards[r][c]
        if card["matched"]:
            print(f"  {self._('already_matched')}")
            return None
        if coord in self.board.flipped:
            print(f"  {self._('already_flipped')}")
            return None

        return coord

    def _handle_game_commands(self, cmd: str) -> Optional[str]:
        """Handle special game commands (p, q, h, s, r).

        Args:
            cmd: The command string.

        Returns:
            'quit' if quitting to menu, 'restart' if restarting, None otherwise.
        """
        cmd = cmd.strip().lower()

        if cmd in ("p", "pause"):
            self._toggle_pause()
            return None

        if cmd in ("q", "quit"):
            return "quit"

        if cmd in ("h", "help"):
            self._show_help()
            input(f"\n  {self._('enter_continue')}")
            return None

        if cmd == "s":
            self._show_stats()
            input(f"\n  {self._('enter_continue')}")
            return None

        if cmd == "r":
            return self._confirm_restart()

        if cmd == "show scores":
            self._show_high_scores()
            input(f"\n  {self._('enter_continue')}")
            return None

        return None

    def _toggle_pause(self) -> None:
        """Toggle pause/resume game state."""
        if not self.is_paused:
            self.is_paused = True
            self.paused_time = time.time()
            print(f"\n  {self._('game_paused')}")
            input()
            self.total_paused += time.time() - self.paused_time
            self.is_paused = False
        else:
            self.is_paused = False
            print(f"\n  {self._('game_resumed')}")

    def _show_stats(self) -> None:
        """Display current game statistics."""
        assert self.board is not None
        elapsed = self._get_elapsed()
        matched = sum(
            1 for row in self.board.cards for card in row if card["matched"]
        )
        total = self.board.total_cards
        diff_name = self.config.get_difficulty_name()
        print(f"\n  {self._('game_board_title')}")
        print(f"  {self._('current_difficulty').format(diff_name)}")
        print(f"  {self._('game_stats').format(self.moves, matched, total, format_time(elapsed))}")

    def _confirm_restart(self) -> Optional[str]:
        """Confirm and restart the game.

        Returns:
            'restart' if confirmed, None otherwise.
        """
        print(f"\n  {self._('confirm_restart')}", end="")
        confirm = input().strip().lower()
        if confirm in ("y", "yes", "是"):
            return "restart"
        return None

    def _show_help(self) -> None:
        """Display the how-to-play / help screen."""
        clear_screen()
        print(f"\n  {self._('how_to_play_title')}")
        print()
        rules = LANG_ZH["how_to_play_rules"] if self.config.language == "zh" else LANG_EN["how_to_play_rules"]
        for line in rules:
            print(f"  {line}")
        print()

    def play(self) -> None:
        """Main game loop."""
        self._create_board()
        self._reset_game_state()

        while self.in_game and self.running:
            self._display_board()

            # Get first card
            first_coord = self._get_card_selection(1)
            if first_coord is None:
                continue
            if isinstance(first_coord, str):
                if first_coord == "quit":
                    self.in_game = False
                    return
                if first_coord == "restart":
                    self._create_board()
                    self._reset_game_state()
                    print(f"\n  {self._('game_restarted')}")
                    time.sleep(0.5)
                    continue
                continue

            # Flip first card
            self.board.flip_card(first_coord)
            self._display_board()

            # Get second card
            second_coord = self._get_card_selection(2)
            if second_coord is None:
                # Unflip first card if cancelled
                self.board.flipped.clear()
                continue
            if isinstance(second_coord, str):
                if second_coord == "quit":
                    self.in_game = False
                    return
                if second_coord == "restart":
                    self._create_board()
                    self._reset_game_state()
                    print(f"\n  {self._('game_restarted')}")
                    time.sleep(0.5)
                    continue
                continue

            # Flip second card
            self.board.flip_card(second_coord)
            self.moves += 1
            self._display_board()

            # Show flipped cards
            sym1 = self.board.cards[first_coord[0]][first_coord[1]]["symbol"]
            sym2 = self.board.cards[second_coord[0]][second_coord[1]]["symbol"]
            print(f"  {self._('card_flipped').format(sym1, sym2)}")

            # Check match
            is_match = self.board.check_match()
            if is_match:
                print(f"  {self._('card_match')}")
                self._beep_match()
            else:
                print(f"  {self._('card_mismatch')}")
                self._beep_mismatch()
                time.sleep(1.0)
                self.board.reset_flipped()

            # Check win
            if self.board.is_won():
                self._handle_win()
                return

            time.sleep(0.3)

    def _get_card_selection(self, card_num: int) -> Optional:
        """Get a card selection from the player.

        Args:
            card_num: Which card (1 or 2) being selected.

        Returns:
            (row, col) tuple, or string command ('quit', 'restart'), or None.
        """
        while True:
            try:
                prompt = f"  [{card_num}] {self._('game_prompt')}"
                user_input = input(prompt).strip().lower()
            except (EOFError, KeyboardInterrupt):
                return "quit"

            if not user_input:
                continue

            # Limit input length to prevent buffer issues
            if len(user_input) > 10:
                print(f"  {self._('invalid_coord')}")
                continue

            # Check for commands
            result = self._handle_game_commands(user_input)
            if result == "quit":
                return "quit"
            if result == "restart":
                return "restart"
            if result is not None:
                continue

            # Parse as coordinate
            coord = self._parse_input(user_input)
            if coord is not None:
                return coord

    def _handle_win(self) -> None:
        """Handle game win: show victory screen, calculate score, save."""
        self._beep_win()
        elapsed = self._get_elapsed()
        score = self._calculate_score()

        clear_screen()
        print(f"\n  {self._('game_won_title')}")
        print()
        self._display_board()
        print()
        print(f"  {self._('game_won_stats').format(self.moves, format_time(elapsed), score)}")
        print()

        # Get player name
        try:
            name_input = input(f"  {self._('game_won_prompt_name')}").strip()
        except (EOFError, KeyboardInterrupt):
            name_input = ""

        # Limit name length to prevent display issues
        if name_input:
            name_input = name_input[:20]
        player_name = name_input if name_input else self._("player_name")

        # Save score
        self.score_manager.add_score(
            player=player_name,
            score=score,
            difficulty=self.config.difficulty,
            moves=self.moves,
            time_seconds=elapsed,
        )

        print(f"\n  {self._('game_won_prompt_continue')}")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass

        self.in_game = False

    def _calculate_score(self) -> int:
        """Calculate game score.

        Score = max(1000 - moves * 10 - seconds * 2, 0)

        Returns:
            Calculated score.
        """
        elapsed = self._get_elapsed()
        return max(1000 - self.moves * 10 - elapsed * 2, 0)


# ---------------------------------------------------------------------------
# Menu system
# ---------------------------------------------------------------------------


def main_menu(game: Game) -> None:
    """Display and handle the main menu.

    Args:
        game: Game instance.
    """
    while game.running:
        clear_screen()
        diff_name = game.config.get_difficulty_name()
        print(f"\n  {game._('title').format(GAME_VERSION)}")
        print(f"  {'=' * 30}")
        print()
        print(f"  {game._('menu_title')}")
        print(f"  {game._('current_difficulty').format(diff_name)}")
        print()
        print(f"  {game._('menu_1')}")
        print(f"  {game._('menu_2')}")
        print(f"  {game._('menu_3')}")
        print(f"  {game._('menu_4')}")
        print(f"  {game._('menu_5')}")
        print(f"  {game._('menu_6')}")
        print()

        try:
            choice = input(f"  {game._('prompt_choice')}").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "6"

        game._beep_menu()

        if choice == "1":
            game.play()
        elif choice == "2":
            difficulty_menu(game)
        elif choice == "3":
            show_high_scores(game)
        elif choice == "4":
            settings_menu(game)
        elif choice == "5":
            show_how_to_play(game)
        elif choice == "6":
            confirm_exit(game)
        else:
            print(f"\n  {game._('invalid_input')}")
            time.sleep(1.0)


def difficulty_menu(game: Game) -> None:
    """Display and handle the difficulty selection menu.

    Args:
        game: Game instance.
    """
    while True:
        clear_screen()
        print(f"\n  {game._('select_difficulty')}")
        print()
        print(f"  {game._('diff_1')}")
        print(f"  {game._('diff_2')}")
        print(f"  {game._('diff_3')}")
        print(f"  {game._('diff_0')}")
        print()

        try:
            choice = input(f"  {game._('diff_prompt')}").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "0"

        game._beep_menu()

        if choice == "1":
            game.config.difficulty = "easy"
            game.config.save()
            print(f"\n  {game._('difficulty_set').format(game.config.get_difficulty_name())}")
            time.sleep(1.0)
            return
        elif choice == "2":
            game.config.difficulty = "medium"
            game.config.save()
            print(f"\n  {game._('difficulty_set').format(game.config.get_difficulty_name())}")
            time.sleep(1.0)
            return
        elif choice == "3":
            game.config.difficulty = "hard"
            game.config.save()
            print(f"\n  {game._('difficulty_set').format(game.config.get_difficulty_name())}")
            time.sleep(1.0)
            return
        elif choice == "0":
            return
        else:
            print(f"\n  {game._('invalid_input')}")
            time.sleep(1.0)


def settings_menu(game: Game) -> None:
    """Display and handle the settings menu.

    Args:
        game: Game instance.
    """
    while True:
        clear_screen()
        sound_status = game._("sound_on") if game.config.sound_enabled else game._("sound_off")
        lang_name = game._("language_zh") if game.config.language == "zh" else game._("language_en")

        print(f"\n  {game._('settings_title')}")
        print()
        print(f"  {game._('settings_lang').format(lang_name)}")
        print(f"  {game._('settings_sound').format(sound_status)}")
        print(f"  {game._('settings_volume').format(game.config.volume)}")
        print(f"  {game._('settings_0')}")
        print()

        try:
            choice = input(f"  {game._('settings_prompt')}").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "0"

        game._beep_menu()

        if choice == "1":
            # Toggle language
            game.config.language = "en" if game.config.language == "zh" else "zh"
            game.config.save()
            lang_name = game._("language_zh") if game.config.language == "zh" else game._("language_en")
            print(f"\n  {game._('lang_set').format(lang_name)}")
            time.sleep(1.0)

        elif choice == "2":
            # Toggle sound
            game.config.sound_enabled = not game.config.sound_enabled
            game.config.save()
            sound_status = game._("sound_on") if game.config.sound_enabled else game._("sound_off")
            print(f"\n  {game._('settings_sound').format(sound_status)}")
            time.sleep(1.0)

        elif choice == "3":
            # Volume
            try:
                vol_input = input(f"  {game._('volume_prompt')}").strip()
                vol = int(vol_input)
                if 0 <= vol <= 100:
                    game.config.volume = vol
                    game.config.save()
                    print(f"\n  {game._('volume_set').format(vol)}")
                else:
                    print(f"\n  {game._('volume_range_error')}")
                time.sleep(1.0)
            except (ValueError, EOFError, KeyboardInterrupt):
                print(f"\n  {game._('invalid_input')}")
                time.sleep(1.0)

        elif choice == "0":
            return
        else:
            print(f"\n  {game._('invalid_input')}")
            time.sleep(1.0)


def show_high_scores(game: Game) -> None:
    """Display the high scores screen.

    Args:
        game: Game instance.
    """
    clear_screen()
    print(f"\n  {game._('high_scores_title')}")
    print()

    top_scores = game.score_manager.get_top(10)
    if not top_scores:
        print(f"  {game._('high_scores_empty')}")
    else:
        # Header
        diff_header = game._("current_difficulty").split(":")[0] if game.config.language == "zh" else "Diff"
        if game.config.language == "zh":
            print(f"  {'排名':<4} {'玩家':<12} {'分数':<8} {'难度':<10} {'步数':<6} {'用时':<6} {'日期':<12}")
        else:
            print(f"  {'Rank':<4} {'Player':<12} {'Score':<8} {'Difficulty':<10} {'Moves':<6} {'Time':<6} {'Date':<12}")
        print(f"  {'-' * 60}")

        for i, entry in enumerate(top_scores):
            rank = f"{i + 1}"
            if i == 0:
                rank = f"{game._('high_scores_star')}{i + 1}"

            diff_display = game.config.get_difficulty_name(entry.difficulty)
            time_display = format_time(entry.time)

            print(
                f"  {rank:<4} {entry.player:<12} {entry.score:<8} {diff_display:<10} "
                f"{entry.moves:<6} {time_display:<6} {entry.date:<12}"
            )

    print()
    try:
        input(f"  {game._('high_scores_prompt')}")
    except (EOFError, KeyboardInterrupt):
        pass


def show_how_to_play(game: Game) -> None:
    """Display the how-to-play screen.

    Args:
        game: Game instance.
    """
    clear_screen()
    print(f"\n  {game._('how_to_play_title')}")
    print()
    rules = LANG_ZH["how_to_play_rules"] if game.config.language == "zh" else LANG_EN["how_to_play_rules"]
    for line in rules:
        print(f"  {line}")
    print()
    try:
        input(f"  {game._('how_to_play_prompt')}")
    except (EOFError, KeyboardInterrupt):
        pass


def confirm_exit(game: Game) -> None:
    """Handle exit confirmation.

    Args:
        game: Game instance.
    """
    print(f"\n  {game._('exit_confirm')}", end="")
    try:
        confirm = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        confirm = "y"

    if confirm in ("y", "yes", "是"):
        print(f"\n  {game._('goodbye')}")
        game.running = False
    else:
        print(f"\n  {game._('enter_continue')}")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass


# ---------------------------------------------------------------------------
# Signal handler
# ---------------------------------------------------------------------------


def signal_handler(sig: int, frame) -> None:
    """Handle Ctrl+C gracefully during input.

    Args:
        sig: Signal number.
        frame: Current stack frame.
    """
    # Just raise KeyboardInterrupt which is caught in input() calls
    raise KeyboardInterrupt


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for the Memory Match game."""
    signal.signal(signal.SIGINT, signal_handler)

    config = Config.load()
    game = Game(config)

    try:
        main_menu(game)
    except KeyboardInterrupt:
        print(f"\n  {game._('goodbye')}")
    except Exception as e:
        print(f"\n  Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
