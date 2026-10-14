"""
Instagram Kinetic Typography Studio
====================================
Deterministic, frame-accurate kinetic lyrics overlay engine and desktop creative suite
built with PySide6, NumPy, faster-whisper, and headless FFmpeg subprocess piping.
"""

# ==============================================================================
# 1. IMPORTS & PLATFORM CONFIGURATION
# ==============================================================================

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["QT_LOGGING_RULES"] = "qt.multimedia.ffmpeg=false"

import re
import json
import math
import time
import uuid
import shutil
import tempfile
import subprocess
import copy
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple, Dict, Any, Set
from collections import defaultdict

import numpy as np

from PySide6.QtCore import (
    Qt, QRectF, QPointF, QSize, QTimer, Signal, Slot, QThread, QUrl, QObject
)
from PySide6.QtGui import (
    QPainter, QColor, QFont, QFontMetricsF, QPainterPath, QImage,
    QPen, QBrush, QAction, QKeySequence, QIcon,
    QFontDatabase, QGuiApplication, QUndoStack, QUndoCommand
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QLabel, QPushButton, QSlider, QSpinBox, QDoubleSpinBox,
    QLineEdit, QComboBox, QCheckBox, QFileDialog, QMessageBox,
    QDialog, QProgressBar, QGroupBox, QScrollArea, QScrollBar, QFrame, QSizePolicy,
    QStatusBar, QMenu, QColorDialog
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink, QVideoFrame


def get_subprocess_creation_flags() -> Dict[str, Any]:
    """Provides platform-aware creation flags suppressing console windows on Windows."""
    kwargs: Dict[str, Any] = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def format_ms_timecode(ms: int) -> str:
    """Formats milliseconds as MM:SS.mmm tabular telemetry."""
    sec = max(0.0, ms / 1000.0)
    m, s = divmod(sec, 60.0)
    return f"{int(m):02d}:{s:06.3f}"


# ==============================================================================
# 2. INDUSTRIAL DESIGN SYSTEM STYLESHEET (QSS)
# ==============================================================================

STYLE_SHEET = """
/* Utilitarian Precision Dark Theme (Ableton Live 12 / DaVinci Resolve / Linear) */
QMainWindow, QDialog {
    background-color: #09090B;
    color: #E4E4E7;
}
QWidget {
    background-color: #09090B;
    color: #E4E4E7;
    font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 11px;
    border-radius: 0px;
}
QWidget#dockPanel {
    background-color: #121316;
    border: 1px solid #27272A;
}
QMenuBar {
    background-color: #121316;
    color: #E4E4E7;
    border-bottom: 1px solid #27272A;
    padding: 2px 4px;
}
QMenuBar::item {
    background-color: transparent;
    padding: 4px 8px;
    border-radius: 0px;
}
QMenuBar::item:selected {
    background-color: #18181B;
    color: #E4E4E7;
    border: 1px solid #3F3F46;
}
QMenu {
    background-color: #121316;
    color: #E4E4E7;
    border: 1px solid #27272A;
    padding: 2px;
    border-radius: 0px;
}
QMenu::item {
    padding: 5px 18px 5px 10px;
    border-radius: 0px;
}
QMenu::item:selected {
    background-color: #3B82F6;
    color: #E4E4E7;
}
QMenu::item:disabled {
    color: #71717A;
}
QMenu::separator {
    height: 1px;
    background: #27272A;
    margin: 2px 0px;
}
QScrollArea {
    background-color: #121316;
    border: 1px solid #27272A;
    border-radius: 0px;
}
QScrollArea > QWidget > QWidget {
    background-color: #121316;
}
QScrollBar:vertical {
    background: #09090B;
    width: 8px;
    margin: 0px;
    border-left: 1px solid #27272A;
}
QScrollBar::handle:vertical {
    background: #27272A;
    min-height: 20px;
    border-radius: 0px;
}
QScrollBar::handle:vertical:hover {
    background: #3F3F46;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #09090B;
    height: 8px;
    margin: 0px;
    border-top: 1px solid #27272A;
}
QScrollBar::handle:horizontal {
    background: #27272A;
    min-width: 20px;
    border-radius: 0px;
}
QScrollBar::handle:horizontal:hover {
    background: #3F3F46;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QGroupBox {
    background-color: #18181B;
    border: 1px solid #27272A;
    border-radius: 0px;
    margin-top: 14px;
    padding: 8px 6px 6px 6px;
    font-weight: 700;
    font-size: 10px;
    color: #71717A;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 6px;
    top: 2px;
    padding: 0px 4px;
    background-color: #18181B;
    color: #71717A;
}
QLabel {
    background-color: transparent;
    color: #E4E4E7;
    border-radius: 0px;
}
QLabel#mutedLabel {
    color: #71717A;
}
QLabel#panelHeader {
    font-weight: 700;
    font-size: 11px;
    color: #3B82F6;
    letter-spacing: 1px;
}
QLabel#telemetryBanner {
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 10px;
    font-weight: 700;
    color: #3B82F6;
    background-color: #09090B;
    border: 1px solid #27272A;
    padding: 4px 6px;
}
QLabel#accentValueLabel {
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-weight: 700;
    color: #3B82F6;
}
QLabel#timecodeLabel {
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 11px;
    font-weight: 700;
    color: #E4E4E7;
    background-color: #121316;
    padding: 4px 8px;
    border: 1px solid #27272A;
    border-radius: 0px;
}
QPushButton {
    background-color: #18181B;
    border: 1px solid #27272A;
    border-radius: 0px;
    padding: 4px 8px;
    font-weight: 600;
    color: #E4E4E7;
    min-height: 18px;
}
QPushButton:hover {
    background-color: #18181B;
    border: 1px solid #3F3F46;
    color: #E4E4E7;
}
QPushButton:pressed {
    background-color: #09090B;
    border: 1px solid #3B82F6;
}
QPushButton:disabled {
    background-color: #09090B;
    border: 1px solid #27272A;
    color: #71717A;
}
QPushButton#primaryButton {
    background-color: #3B82F6;
    border: 1px solid #3B82F6;
    color: #E4E4E7;
    font-weight: 700;
}
QPushButton#primaryButton:hover {
    background-color: #3B82F6;
    border: 1px solid #E4E4E7;
}
QPushButton#primaryButton:pressed {
    background-color: #121316;
    border: 1px solid #3B82F6;
}
QPushButton#accentActionButton {
    background-color: #121316;
    border: 1px solid #3B82F6;
    color: #3B82F6;
    font-weight: 700;
}
QPushButton#accentActionButton:hover {
    background-color: #3B82F6;
    border: 1px solid #3B82F6;
    color: #E4E4E7;
}
QPushButton#dangerButton {
    background-color: #18181B;
    border: 1px solid #EF4444;
    color: #EF4444;
    font-weight: 600;
}
QPushButton#dangerButton:hover {
    background-color: #EF4444;
    border: 1px solid #EF4444;
    color: #09090B;
}
QPushButton#playButtonActive {
    background-color: #EF4444;
    border: 1px solid #EF4444;
    color: #09090B;
    font-weight: 700;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #09090B;
    border: 1px solid #27272A;
    border-radius: 0px;
    padding: 4px 6px;
    color: #E4E4E7;
    selection-background-color: #3B82F6;
    selection-color: #E4E4E7;
    min-height: 18px;
}
QSpinBox, QDoubleSpinBox {
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {
    border: 1px solid #3F3F46;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #3B82F6;
}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    background-color: #09090B;
    border: 1px solid #27272A;
    color: #71717A;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid #27272A;
    background-color: #121316;
    border-radius: 0px;
}
QComboBox QAbstractItemView {
    background-color: #121316;
    border: 1px solid #27272A;
    border-radius: 0px;
    color: #E4E4E7;
    selection-background-color: #3B82F6;
    selection-color: #E4E4E7;
    padding: 2px;
}
QSlider {
    background-color: transparent;
}
QSlider::groove:horizontal {
    height: 2px;
    background: #27272A;
    border-radius: 0px;
}
QSlider::sub-page:horizontal {
    background: #3B82F6;
    border-radius: 0px;
}
QSlider::handle:horizontal {
    width: 8px;
    height: 14px;
    margin-top: -6px;
    margin-bottom: -6px;
    background: #E4E4E7;
    border: 1px solid #09090B;
    border-radius: 0px;
}
QSlider::handle:horizontal:hover {
    background: #3B82F6;
    border: 1px solid #E4E4E7;
}
QCheckBox {
    background-color: transparent;
    color: #E4E4E7;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 12px;
    height: 12px;
    background-color: #09090B;
    border: 1px solid #27272A;
    border-radius: 0px;
}
QCheckBox::indicator:hover {
    border: 1px solid #3F3F46;
}
QCheckBox::indicator:checked {
    background-color: #3B82F6;
    border: 1px solid #3B82F6;
}
QSplitter::handle {
    background-color: #27272A;
}
QSplitter::handle:horizontal {
    width: 1px;
    background-color: #27272A;
}
QSplitter::handle:vertical {
    height: 1px;
    background-color: #27272A;
}
QProgressBar {
    background-color: #09090B;
    border: 1px solid #27272A;
    border-radius: 0px;
    text-align: center;
    color: #E4E4E7;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-weight: 700;
    font-size: 10px;
    height: 14px;
}
QProgressBar::chunk {
    background-color: #3B82F6;
    border-radius: 0px;
}
QStatusBar {
    background-color: #121316;
    color: #71717A;
    border-top: 1px solid #27272A;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 10px;
}
"""


# ==============================================================================
# 3. CORE DATA MODELS & UNDO COMMANDS
# ==============================================================================

@dataclass
class WordKeyframe:
    """Strongly typed data model representing a single animated word keyframe."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str = "WORD"
    start_ms: int = 0
    end_ms: int = 1000
    scale_multiplier: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    fade_in_ms: int = 120
    fade_curve: str = "cubic"
    inactive_opacity: float = 0.0
    line_index: int = 0
    font_size_override: Optional[float] = None
    font_family: Optional[str] = None
    letter_fonts: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WordKeyframe":
        fc = str(data.get("fade_curve", "cubic"))
        if fc not in ("cubic", "linear"):
            fc = "linear" if fc == "1" else "cubic"

        lf = data.get("letter_fonts")
        if isinstance(lf, dict):
            clean_lf = {str(k): str(v) for k, v in lf.items() if v}
        else:
            clean_lf = None

        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            text=str(data.get("text", "WORD")),
            start_ms=int(data.get("start_ms", 0)),
            end_ms=int(data.get("end_ms", 1000)),
            scale_multiplier=float(data.get("scale_multiplier", 1.0)),
            offset_x=float(data.get("offset_x", 0.0)),
            offset_y=float(data.get("offset_y", 0.0)),
            fade_in_ms=int(data.get("fade_in_ms", 120)),
            fade_curve=fc,
            inactive_opacity=float(data.get("inactive_opacity", 0.0)),
            line_index=int(data.get("line_index", 0)),
            font_size_override=data.get("font_size_override"),
            font_family=data.get("font_family"),
            letter_fonts=clean_lf,
        )


@dataclass
class Stanza:
    """A lyrical block that cuts cleanly to the next upon completion."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    start_ms: int = 0
    end_ms: int = 2500
    words: List[WordKeyframe] = field(default_factory=list)
    layout_preset: str = "stacked_punch"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "words": [w.to_dict() for w in self.words],
            "layout_preset": self.layout_preset,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Stanza":
        preset = str(data.get("layout_preset", "stacked_punch"))
        if preset not in ("stacked_punch", "box_badge", "word_stagger", "hard_cut_glitch"):
            preset = "stacked_punch"
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            start_ms=int(data.get("start_ms", 0)),
            end_ms=int(data.get("end_ms", 2500)),
            words=[WordKeyframe.from_dict(w) for w in data.get("words", [])],
            layout_preset=preset,
        )

    def recompute_bounds(self) -> None:
        """Derive start_ms and end_ms strictly from current active word bounds, preventing boundary hysteresis."""
        if self.words:
            self.start_ms = min(w.start_ms for w in self.words)
            self.end_ms = max(w.end_ms for w in self.words)


@dataclass
class LyricProject:
    """Root project configuration containing all stanzas, rendering parameters, and assets."""
    title: str = "Instagram Kinetic Lyrics Project"
    audio_file: Optional[str] = None
    duration_ms: int = 10000
    base_font_family: str = "Inter"
    base_font_path: Optional[str] = None
    custom_font_paths: List[str] = field(default_factory=list)
    base_font_size: float = 92.0
    resolution_width: int = 1080
    resolution_height: int = 1920
    fps: int = 60
    global_inactive_opacity: float = 0.0
    global_fade_in_ms: int = 120
    letter_spacing: float = -2.5
    line_height_factor: float = 0.95
    align_x: float = 0.12
    align_y: float = 0.42
    text_casing: str = "ALL_CAPS"          # "ALL_CAPS", "TITLE_CASE", "AS_TYPED"
    stroke_width: float = 0.0              # 0.0 to 12.0 px
    stroke_color: str = "#000000"          # Hex color string
    default_layout_preset: str = "stacked_punch"
    bg_media_path: Optional[str] = None
    bg_dim_opacity: float = 0.40
    stanzas: List[Stanza] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "audio_file": self.audio_file,
            "duration_ms": self.duration_ms,
            "base_font_family": self.base_font_family,
            "base_font_path": self.base_font_path,
            "custom_font_paths": list(self.custom_font_paths),
            "base_font_size": self.base_font_size,
            "resolution_width": self.resolution_width,
            "resolution_height": self.resolution_height,
            "fps": self.fps,
            "global_inactive_opacity": self.global_inactive_opacity,
            "global_fade_in_ms": self.global_fade_in_ms,
            "letter_spacing": self.letter_spacing,
            "line_height_factor": self.line_height_factor,
            "align_x": self.align_x,
            "align_y": self.align_y,
            "text_casing": self.text_casing,
            "stroke_width": self.stroke_width,
            "stroke_color": self.stroke_color,
            "default_layout_preset": self.default_layout_preset,
            "bg_media_path": self.bg_media_path,
            "bg_dim_opacity": self.bg_dim_opacity,
            "stanzas": [s.to_dict() for s in self.stanzas],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LyricProject":
        base_path = data.get("base_font_path")
        if base_path and os.path.isfile(base_path):
            FontManager.load_font_file(base_path)
        for cfp in data.get("custom_font_paths", []):
            if cfp and os.path.isfile(cfp):
                FontManager.load_font_file(cfp)

        return cls(
            title=data.get("title", "Instagram Kinetic Lyrics Project"),
            audio_file=data.get("audio_file"),
            duration_ms=int(data.get("duration_ms", 10000)),
            base_font_family=data.get("base_font_family", "Inter"),
            base_font_path=data.get("base_font_path"),
            custom_font_paths=list(data.get("custom_font_paths", [])),
            base_font_size=float(data.get("base_font_size", 92.0)),
            resolution_width=int(data.get("resolution_width", 1080)),
            resolution_height=int(data.get("resolution_height", 1920)),
            fps=int(data.get("fps", 60)),
            global_inactive_opacity=float(data.get("global_inactive_opacity", 0.0)),
            global_fade_in_ms=int(data.get("global_fade_in_ms", 120)),
            letter_spacing=float(data.get("letter_spacing", -2.5)),
            line_height_factor=float(data.get("line_height_factor", 0.95)),
            align_x=float(data.get("align_x", 0.12)),
            align_y=float(data.get("align_y", 0.42)),
            text_casing=str(data.get("text_casing", "ALL_CAPS")),
            stroke_width=float(data.get("stroke_width", 0.0)),
            stroke_color=str(data.get("stroke_color", "#000000")),
            default_layout_preset=str(data.get("default_layout_preset", "stacked_punch")),
            bg_media_path=data.get("bg_media_path"),
            bg_dim_opacity=float(data.get("bg_dim_opacity", 0.40)),
            stanzas=[Stanza.from_dict(s) for s in data.get("stanzas", [])],
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "LyricProject":
        return cls.from_dict(json.loads(json_str))

    def save(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, filepath: str) -> "LyricProject":
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())

    def get_active_stanza(self, time_ms: float) -> Optional[Stanza]:
        """Fetch the active stanza at timestamp time_ms under hard-cut semantics."""
        for stanza in self.stanzas:
            if stanza.start_ms <= time_ms < stanza.end_ms:
                return stanza
        return None

    def find_word_by_id(self, word_id: str) -> Optional[Tuple[Stanza, WordKeyframe]]:
        for stanza in self.stanzas:
            for word in stanza.words:
                if word.id == word_id:
                    return stanza, word
        return None

    def get_all_word_ids(self) -> Set[str]:
        return {w.id for s in self.stanzas for w in s.words}

    @classmethod
    def create_default_punch_sample(cls) -> "LyricProject":
        """Instantiate project with default punch phrases matching the specification."""
        project = cls(duration_ms=10000, global_inactive_opacity=0.0)

        s1 = Stanza(start_ms=100, end_ms=1550, layout_preset="stacked_punch")
        s1.words = [
            WordKeyframe(text="REP", start_ms=100, end_ms=1550, scale_multiplier=2.3, line_index=0),
            WordKeyframe(text="THE", start_ms=450, end_ms=1550, scale_multiplier=1.0, line_index=1),
            WordKeyframe(text="SQUAD", start_ms=750, end_ms=1550, scale_multiplier=1.0, line_index=1),
            WordKeyframe(text="ALL", start_ms=1050, end_ms=1550, scale_multiplier=1.2, line_index=2),
            WordKeyframe(text="DAY", start_ms=1250, end_ms=1550, scale_multiplier=1.2, line_index=2),
        ]
        s1.recompute_bounds()

        s2 = Stanza(start_ms=1700, end_ms=3250, layout_preset="stacked_punch")
        s2.words = [
            WordKeyframe(text="MASK", start_ms=1700, end_ms=3250, scale_multiplier=2.4, line_index=0),
            WordKeyframe(text="ON", start_ms=2050, end_ms=3250, scale_multiplier=1.0, line_index=1),
            WordKeyframe(text="MY", start_ms=2300, end_ms=3250, scale_multiplier=1.0, line_index=1),
            WordKeyframe(text="FACE", start_ms=2550, end_ms=3250, scale_multiplier=1.1, line_index=1),
        ]
        s2.recompute_bounds()

        s3 = Stanza(start_ms=3400, end_ms=5150, layout_preset="stacked_punch")
        s3.words = [
            WordKeyframe(text="CHASE", start_ms=3400, end_ms=5150, scale_multiplier=2.2, line_index=0),
            WordKeyframe(text="THE", start_ms=3750, end_ms=5150, scale_multiplier=1.0, line_index=1),
            WordKeyframe(text="BAG", start_ms=4000, end_ms=5150, scale_multiplier=1.1, line_index=1),
            WordKeyframe(text="NEVER", start_ms=4300, end_ms=5150, scale_multiplier=1.2, line_index=2),
            WordKeyframe(text="STOP", start_ms=4650, end_ms=5150, scale_multiplier=1.3, line_index=2),
        ]
        s3.recompute_bounds()

        project.stanzas = [s1, s2, s3]
        return project


class BatchWordTimingUndoCommand(QUndoCommand):
    """
    Atomic UndoCommand for single or batch word translation and edge-trimming.
    Stores list of (word_id, old_start, old_end, new_start, new_end).
    """

    def __init__(
        self,
        project: LyricProject,
        changes: List[Tuple[str, int, int, int, int]],
        selected_ids: Set[str],
        primary_id: Optional[str],
        callback: Any,
    ):
        label = f"Trim/Move {len(changes)} Word(s)"
        super().__init__(label)
        self.project = project
        self.changes = list(changes)
        self.selected_ids = set(selected_ids)
        self.primary_id = primary_id
        self.callback = callback

    def undo(self) -> None:
        affected_stanzas: List[Stanza] = []
        for word_id, old_start, old_end, _, _ in self.changes:
            res = self.project.find_word_by_id(word_id)
            if res:
                stanza, word = res
                word.start_ms = old_start
                word.end_ms = old_end
                if stanza not in affected_stanzas:
                    affected_stanzas.append(stanza)
        for stanza in affected_stanzas:
            stanza.recompute_bounds()
        self.callback(self.selected_ids, self.primary_id)

    def redo(self) -> None:
        affected_stanzas: List[Stanza] = []
        for word_id, _, _, new_start, new_end in self.changes:
            res = self.project.find_word_by_id(word_id)
            if res:
                stanza, word = res
                word.start_ms = new_start
                word.end_ms = new_end
                if stanza not in affected_stanzas:
                    affected_stanzas.append(stanza)
        for stanza in affected_stanzas:
            stanza.recompute_bounds()
        self.callback(self.selected_ids, self.primary_id)


class BatchWordPropertyUndoCommand(QUndoCommand):
    """
    Atomic UndoCommand for mutating a property across one or more selected WordKeyframes.
    Supports command merging for smooth continuous slider drags.
    """

    def __init__(
        self,
        project: LyricProject,
        prop_name: str,
        changes: List[Tuple[str, Any, Any]],
        selected_ids: Set[str],
        primary_id: Optional[str],
        callback: Any,
    ):
        super().__init__(f"Edit {prop_name} ({len(changes)} word(s))")
        self.project = project
        self.prop_name = prop_name
        self.changes = list(changes)  # [(word_id, old_val, new_val), ...]
        self.selected_ids = set(selected_ids)
        self.primary_id = primary_id
        self.callback = callback

    def id(self) -> int:
        return 1002

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, BatchWordPropertyUndoCommand):
            return False
        if self.prop_name in ("font_family", "letter_fonts", "text", "line_index"):
            return False
        if other.prop_name != self.prop_name or other.selected_ids != self.selected_ids:
            return False
        new_map = {wid: new_v for wid, _, new_v in other.changes}
        merged: List[Tuple[str, Any, Any]] = []
        for wid, old_v, _ in self.changes:
            if wid not in new_map:
                return False
            merged.append((wid, old_v, new_map[wid]))
        self.changes = merged
        return True

    def undo(self) -> None:
        affected_stanzas: List[Stanza] = []
        for word_id, old_val, _ in self.changes:
            res = self.project.find_word_by_id(word_id)
            if res:
                stanza, word = res
                val_to_set = copy.deepcopy(old_val) if isinstance(old_val, dict) else old_val
                setattr(word, self.prop_name, val_to_set)
                if self.prop_name in ("start_ms", "end_ms") and stanza not in affected_stanzas:
                    affected_stanzas.append(stanza)
        for stanza in affected_stanzas:
            stanza.recompute_bounds()
        self.callback(self.selected_ids, self.primary_id)

    def redo(self) -> None:
        affected_stanzas: List[Stanza] = []
        for word_id, _, new_val in self.changes:
            res = self.project.find_word_by_id(word_id)
            if res:
                stanza, word = res
                val_to_set = copy.deepcopy(new_val) if isinstance(new_val, dict) else new_val
                setattr(word, self.prop_name, val_to_set)
                if self.prop_name in ("start_ms", "end_ms") and stanza not in affected_stanzas:
                    affected_stanzas.append(stanza)
        for stanza in affected_stanzas:
            stanza.recompute_bounds()
        self.callback(self.selected_ids, self.primary_id)


class AddWordUndoCommand(QUndoCommand):
    """Undoable command for adding a word to a stanza."""

    def __init__(
        self,
        project: LyricProject,
        stanza_id: str,
        word_dict: Dict[str, Any],
        created_new_stanza: bool,
        callback: Any,
    ):
        super().__init__("Add Word")
        self.project = project
        self.stanza_id = stanza_id
        self.word_dict = word_dict
        self.created_new_stanza = created_new_stanza
        self.callback = callback

    def undo(self) -> None:
        for s in list(self.project.stanzas):
            if s.id == self.stanza_id:
                s.words = [w for w in s.words if w.id != self.word_dict["id"]]
                if self.created_new_stanza and not s.words:
                    self.project.stanzas.remove(s)
                else:
                    s.recompute_bounds()
                break
        self.callback(set(), None)

    def redo(self) -> None:
        target_stanza = None
        for s in self.project.stanzas:
            if s.id == self.stanza_id:
                target_stanza = s
                break
        if target_stanza is None and self.created_new_stanza:
            target_stanza = Stanza(
                id=self.stanza_id,
                start_ms=self.word_dict["start_ms"],
                end_ms=self.word_dict["end_ms"],
                layout_preset=self.project.default_layout_preset,
            )
            self.project.stanzas.append(target_stanza)
        if target_stanza is not None:
            wid = self.word_dict["id"]
            if not any(w.id == wid for w in target_stanza.words):
                target_stanza.words.append(WordKeyframe.from_dict(self.word_dict))
            target_stanza.recompute_bounds()
            self.callback({wid}, wid)


class BatchDeleteWordsUndoCommand(QUndoCommand):
    """Atomic UndoCommand for deleting one or multiple words across stanzas."""

    def __init__(
        self,
        project: LyricProject,
        word_ids_to_delete: Set[str],
        primary_id: Optional[str],
        callback: Any,
    ):
        super().__init__(f"Delete {len(word_ids_to_delete)} Word(s)")
        self.project = project
        self.word_ids_to_delete = set(word_ids_to_delete)
        self.primary_id = primary_id
        self.callback = callback
        # Store (stanza_id, index_in_stanza, word_dict) in ascending index order
        self.deleted_records: List[Tuple[str, int, Dict[str, Any]]] = []
        for stanza in self.project.stanzas:
            for idx, w in enumerate(stanza.words):
                if w.id in self.word_ids_to_delete:
                    self.deleted_records.append((stanza.id, idx, w.to_dict()))

    def undo(self) -> None:
        stanza_map = {s.id: s for s in self.project.stanzas}
        affected_stanzas: List[Stanza] = []
        for stanza_id, idx, w_dict in self.deleted_records:
            stanza = stanza_map.get(stanza_id)
            if stanza is not None:
                restored = WordKeyframe.from_dict(w_dict)
                insert_pos = max(0, min(len(stanza.words), idx))
                stanza.words.insert(insert_pos, restored)
                if stanza not in affected_stanzas:
                    affected_stanzas.append(stanza)
        for stanza in affected_stanzas:
            stanza.recompute_bounds()
        primary = self.primary_id if self.primary_id in self.word_ids_to_delete else (
            next(iter(self.word_ids_to_delete)) if self.word_ids_to_delete else None
        )
        self.callback(set(self.word_ids_to_delete), primary)

    def redo(self) -> None:
        affected_stanzas: List[Stanza] = []
        for stanza in self.project.stanzas:
            orig_len = len(stanza.words)
            stanza.words = [w for w in stanza.words if w.id not in self.word_ids_to_delete]
            if len(stanza.words) != orig_len:
                affected_stanzas.append(stanza)
        for stanza in affected_stanzas:
            stanza.recompute_bounds()
        self.callback(set(), None)


class StanzaListUndoCommand(QUndoCommand):
    """Undoable snapshot command for structural stanza additions/deletions."""

    def __init__(
        self,
        project: LyricProject,
        old_stanzas_data: List[Dict[str, Any]],
        new_stanzas_data: List[Dict[str, Any]],
        selected_word_id: Optional[str],
        description: str,
        callback: Any,
    ):
        super().__init__(description)
        self.project = project
        self.old_stanzas_data = old_stanzas_data
        self.new_stanzas_data = new_stanzas_data
        self.selected_word_id = selected_word_id
        self.callback = callback

    def undo(self) -> None:
        self.project.stanzas = [Stanza.from_dict(s) for s in self.old_stanzas_data]
        self.callback(set(), None)

    def redo(self) -> None:
        self.project.stanzas = [Stanza.from_dict(s) for s in self.new_stanzas_data]
        sel_set = {self.selected_word_id} if self.selected_word_id else set()
        self.callback(sel_set, self.selected_word_id)


# ==============================================================================
# 4. KINETIC LAYOUT & TYPOGRAPHY RENDER ENGINE
# ==============================================================================

class FontManager:
    """Manages heavy grotesque sans-serif fonts, custom loaded font files (TTF/OTF/WOFF), and safe Qt6 resolution."""
    _resolved_family: Optional[str] = None
    _loaded_fonts: Dict[str, str] = {}
    _custom_families: List[str] = []

    @classmethod
    def load_font_file(cls, filepath: str) -> Optional[str]:
        if not filepath or not os.path.isfile(filepath):
            return None
        norm_path = os.path.abspath(filepath)
        if norm_path in cls._loaded_fonts:
            return cls._loaded_fonts[norm_path]

        try:
            fid = QFontDatabase.addApplicationFont(norm_path)
            if fid >= 0:
                families = QFontDatabase.applicationFontFamilies(fid)
                if families:
                    family = families[0]
                    cls._loaded_fonts[norm_path] = family
                    if family not in cls._custom_families:
                        cls._custom_families.append(family)
                    return family
        except Exception:
            pass
        return None

    @classmethod
    def get_loaded_families(cls) -> List[str]:
        return list(cls._custom_families)

    @classmethod
    def resolve_heavy_grotesque(cls) -> str:
        if cls._resolved_family is not None:
            return cls._resolved_family

        available = set()
        try:
            available = set(QFontDatabase.families(QFontDatabase.WritingSystem.Any))
        except Exception:
            try:
                available = set(QFontDatabase.families())
            except Exception:
                pass

        candidates = [
            "Inter",
            "Inter Black",
            "Arial Black",
            "Segoe UI Black",
            "Helvetica Neue",
            "Helvetica Neue Black",
            "Montserrat",
            "Montserrat Black",
            "Impact",
            "Arial",
        ]
        for font in candidates:
            if font in available:
                cls._resolved_family = font
                return font

        cls._resolved_family = "Arial"
        return "Arial"

    @classmethod
    def get_available_font_families(cls) -> List[str]:
        result: List[str] = []
        for f in cls._custom_families:
            if f not in result:
                result.append(f)

        curated = [
            "Inter",
            "Arial Black",
            "Segoe UI Black",
            "Impact",
            "Montserrat",
            "Helvetica Neue",
            "Arial",
            "Bahnschrift",
            "Trebuchet MS",
            "Verdana",
            "Tahoma",
            "Georgia",
            "Times New Roman",
            "Courier New",
        ]
        system_families: List[str] = []
        try:
            system_families = sorted(list(QFontDatabase.families()))
        except Exception:
            pass

        for c in curated:
            if (not system_families or c in system_families) and c not in result:
                result.append(c)

        for s in system_families:
            if s not in result and not s.startswith("@"):
                result.append(s)

        if not result:
            result = ["Inter", "Arial", "Segoe UI", "Impact"]

        return result

    @classmethod
    def create_font(
        cls,
        family: Optional[str] = None,
        point_size: float = 92.0,
        weight: QFont.Weight = QFont.Weight.Black,
        letter_spacing: float = 0.0,
    ) -> QFont:
        fam = family or cls.resolve_heavy_grotesque()
        font = QFont(fam)
        font.setPointSizeF(max(6.0, point_size))
        font.setWeight(weight)
        if abs(letter_spacing) > 0.001:
            font.setLetterSpacing(
                QFont.SpacingType.PercentageSpacing,
                100.0 + letter_spacing,
            )
        return font


@dataclass
class WordLayoutBox:
    """Calculated layout coordinates and geometry for a single rendered word."""
    word: WordKeyframe
    display_text: str
    font: QFont
    point_size: float
    x: float
    y: float
    width: float
    height: float
    ascent: float
    row_top_y: float = 0.0
    row_height: float = 0.0
    char_fonts: Optional[List[Tuple[str, QFont, float]]] = None


class KineticLayoutEngine:
    """
    Kinetic typography layout and rasterization engine.
    Computes exact vector coordinates, negative leading, dynamic line stacking,
    custom stroke outlines via QPainterPath, and 4 kinetic animation presets:
    - stacked_punch
    - box_badge
    - word_stagger
    - hard_cut_glitch
    """

    def __init__(self, project: LyricProject):
        self.project = project
        self.font_family = self.project.base_font_family or FontManager.resolve_heavy_grotesque()

    def format_display_text(self, raw_text: str) -> str:
        text = raw_text.strip()
        mode = self.project.text_casing
        if mode == "ALL_CAPS":
            return text.upper()
        elif mode == "TITLE_CASE":
            return text.title()
        return text

    @staticmethod
    def calculate_alpha(word: WordKeyframe, current_time_ms: float, preset: str = "stacked_punch") -> float:
        t_start = word.start_ms
        t_fade = max(1, word.fade_in_ms)
        alpha_inactive = max(0.0, min(1.0, word.inactive_opacity))

        if current_time_ms < t_start:
            return alpha_inactive

        if preset == "hard_cut_glitch":
            return 1.0

        elapsed = current_time_ms - t_start
        if elapsed >= t_fade:
            return 1.0

        u = elapsed / float(t_fade)
        if word.fade_curve == "cubic":
            ease_u = 1.0 - math.pow(1.0 - u, 3.0)
        else:
            ease_u = u

        return alpha_inactive + (1.0 - alpha_inactive) * ease_u

    @staticmethod
    def calculate_transition_progress(word: WordKeyframe, current_time_ms: float) -> float:
        if current_time_ms < word.start_ms:
            return 0.0
        t_fade = max(1, word.fade_in_ms)
        elapsed = current_time_ms - word.start_ms
        if elapsed >= t_fade:
            return 1.0
        u = elapsed / float(t_fade)
        if word.fade_curve == "cubic":
            return 1.0 - math.pow(1.0 - u, 3.0)
        return u

    def compute_layout(self, stanza: Stanza) -> List[WordLayoutBox]:
        lines: Dict[int, List[WordKeyframe]] = defaultdict(list)
        for w in stanza.words:
            lines[w.line_index].append(w)

        sorted_line_indices = sorted(lines.keys())
        layout_boxes: List[WordLayoutBox] = []

        anchor_x = self.project.resolution_width * self.project.align_x
        current_y = self.project.resolution_height * self.project.align_y
        base_family = self.project.base_font_family or self.font_family

        for line_idx in sorted_line_indices:
            row_words = lines[line_idx]
            current_x = anchor_x
            row_max_height = 0.0
            row_max_ascent = 0.0

            row_boxes: List[WordLayoutBox] = []

            for word in row_words:
                text_clean = self.format_display_text(word.text)
                pt_size = self.project.base_font_size * word.scale_multiplier
                if word.font_size_override is not None:
                    pt_size = word.font_size_override

                word_family = word.font_family or base_family
                base_word_font = FontManager.create_font(
                    word_family, pt_size, QFont.Weight.Black, self.project.letter_spacing
                )

                has_char_override = False
                if word.letter_fonts and text_clean:
                    for idx_c in range(len(text_clean)):
                        if str(idx_c) in word.letter_fonts and word.letter_fonts[str(idx_c)]:
                            has_char_override = True
                            break

                char_fonts: Optional[List[Tuple[str, QFont, float]]] = None
                if has_char_override and text_clean:
                    char_fonts = []
                    cum_x = 0.0
                    max_ascent = 0.0
                    max_height = 0.0

                    for idx_c, ch in enumerate(text_clean):
                        override_fam = word.letter_fonts.get(str(idx_c)) if word.letter_fonts else None
                        ch_family = override_fam or word_family
                        ch_font = FontManager.create_font(
                            ch_family, pt_size, QFont.Weight.Black, self.project.letter_spacing
                        )
                        ch_metrics = QFontMetricsF(ch_font)
                        ch_adv = ch_metrics.horizontalAdvance(ch)
                        ch_ascent = ch_metrics.ascent()
                        ch_height = ch_metrics.height()
                        max_ascent = max(max_ascent, ch_ascent)
                        max_height = max(max_height, ch_height)
                        char_fonts.append((ch, ch_font, cum_x))
                        cum_x += ch_adv

                    base_metrics = QFontMetricsF(base_word_font)
                    w_width = cum_x
                    w_height = max(max_height, base_metrics.height())
                    w_ascent = max(max_ascent, base_metrics.ascent())
                    space_width = base_metrics.horizontalAdvance(" ") * 0.85
                else:
                    metrics = QFontMetricsF(base_word_font)
                    w_width = metrics.horizontalAdvance(text_clean)
                    w_height = metrics.height()
                    w_ascent = metrics.ascent()
                    space_width = metrics.horizontalAdvance(" ") * 0.85

                row_max_height = max(row_max_height, w_height)
                row_max_ascent = max(row_max_ascent, w_ascent)

                box = WordLayoutBox(
                    word=word,
                    display_text=text_clean,
                    font=base_word_font,
                    point_size=pt_size,
                    x=current_x + word.offset_x,
                    y=current_y + word.offset_y,
                    width=w_width,
                    height=w_height,
                    ascent=w_ascent,
                    row_top_y=current_y + word.offset_y,
                    row_height=0.0,
                    char_fonts=char_fonts,
                )
                row_boxes.append(box)
                current_x += w_width + space_width

            for box in row_boxes:
                box.y += (row_max_ascent - box.ascent)
                box.row_height = row_max_height
                layout_boxes.append(box)

            leading = row_max_height * self.project.line_height_factor
            current_y += leading

        return layout_boxes

    def render_frame(
        self,
        painter: QPainter,
        current_time_ms: float,
        selected_word_ids: Optional[Set[str]] = None,
        active_primary_word_id: Optional[str] = None,
    ) -> None:
        """Vector render of active kinetic stanza directly onto painter surface."""
        active_stanza = self.project.get_active_stanza(current_time_ms)
        if not active_stanza:
            return

        preset = active_stanza.layout_preset or self.project.default_layout_preset
        layout_boxes = self.compute_layout(active_stanza)
        frame_dur_ms = 1000.0 / max(1, self.project.fps)

        for idx, box in enumerate(layout_boxes):
            alpha = self.calculate_alpha(box.word, current_time_ms, preset=preset)
            is_active = current_time_ms >= box.word.start_ms

            if alpha > 0.001:
                painter.save()
                painter.setFont(box.font)

                draw_x = box.x
                baseline_y = box.y + box.ascent

                if preset == "word_stagger" and is_active:
                    prog = self.calculate_transition_progress(box.word, current_time_ms)
                    if prog < 1.0:
                        inv = 1.0 - prog
                        direction = -1.0 if (idx % 2 == 0) else 1.0
                        draw_x += inv * (-24.0)
                        baseline_y += inv * 14.0 * direction

                elif preset == "hard_cut_glitch" and is_active:
                    elapsed = current_time_ms - box.word.start_ms
                    if 0.0 <= elapsed <= frame_dur_ms * 1.25:
                        sign_x = 1.0 if (idx % 2 == 0) else -1.0
                        sign_y = -1.0 if (idx % 3 == 0) else 1.0
                        draw_x += 7.0 * sign_x
                        baseline_y += 4.0 * sign_y

                fill_color = QColor(255, 255, 255, int(round(alpha * 255)))

                if preset == "box_badge" and is_active:
                    pad_x = max(8.0, box.point_size * 0.14)
                    pad_y = max(4.0, box.point_size * 0.06)
                    badge_rect = QRectF(
                        draw_x - pad_x,
                        box.row_top_y - pad_y,
                        box.width + pad_x * 2.0,
                        box.row_height + pad_y * 2.0,
                    )
                    badge_alpha = int(round(alpha * 255))
                    painter.fillRect(badge_rect, QColor(255, 255, 255, badge_alpha))
                    fill_color = QColor(9, 9, 11, badge_alpha)

                text_path = QPainterPath()
                if box.char_fonts:
                    for ch, ch_font, ch_offset in box.char_fonts:
                        text_path.addText(QPointF(draw_x + ch_offset, baseline_y), ch_font, ch)
                else:
                    text_path.addText(QPointF(draw_x, baseline_y), box.font, box.display_text)

                if self.project.stroke_width > 0.05 and not (preset == "box_badge" and is_active):
                    stroke_c = QColor(self.project.stroke_color)
                    stroke_c.setAlpha(int(round(alpha * 255)))
                    stroke_pen = QPen(
                        stroke_c,
                        self.project.stroke_width * 2.0,
                        Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.SquareCap,
                        Qt.PenJoinStyle.MiterJoin,
                    )
                    painter.strokePath(text_path, stroke_pen)

                painter.fillPath(text_path, QBrush(fill_color))
                painter.restore()

            if selected_word_ids and box.word.id in selected_word_ids:
                painter.save()
                is_primary = (box.word.id == active_primary_word_id)
                if is_primary:
                    sel_pen = QPen(QColor("#3B82F6"), 1.5, Qt.PenStyle.SolidLine)
                    painter.setBrush(QBrush(QColor(59, 130, 246, 55)))
                else:
                    sel_pen = QPen(QColor("#3B82F6"), 1.0, Qt.PenStyle.DashLine)
                    painter.setBrush(QBrush(QColor(59, 130, 246, 28)))
                painter.setPen(sel_pen)
                bounds = QRectF(box.x - 4, box.row_top_y - 2, box.width + 8, box.row_height + 4)
                painter.drawRect(bounds)
                painter.restore()


# ==============================================================================
# 5. REAL-TIME VIEWPORT CANVAS & SAFE GUIDES
# ==============================================================================

class PreviewCanvasWidget(QWidget):
    """
    Real-time viewport with aspect ratio framing, Instagram Reels safe area overlays,
    background layer preview (Solid Black, Checkerboard, Custom Media + Dimmer),
    and multi-word interactive selection.
    """
    selection_changed = Signal(set, str)

    def __init__(self, project: LyricProject, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.project = project
        self.engine = KineticLayoutEngine(project)
        self.current_time_ms = 0.0
        self.selected_word_ids: Set[str] = set()
        self.active_primary_word_id: Optional[str] = None
        self.show_safe_guides = True
        self.background_mode = "black"  # "black", "checkerboard", "custom"
        self.bg_image: Optional[QImage] = None
        self.bg_video_player: Optional[QMediaPlayer] = None
        self.bg_video_sink: Optional[QVideoSink] = None
        self.bg_video_audio_output: Optional[QAudioOutput] = None
        self._bg_video_is_playing = False

        self.setMinimumSize(320, 480)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        if self.project.bg_media_path and os.path.exists(self.project.bg_media_path):
            self.load_background_media(self.project.bg_media_path)

    def set_project(self, project: LyricProject) -> None:
        self.project = project
        self.engine = KineticLayoutEngine(project)
        if self.project.bg_media_path and os.path.exists(self.project.bg_media_path):
            self.load_background_media(self.project.bg_media_path)
        self.update()

    def on_play_state_changed(self, is_playing: bool) -> None:
        self._bg_video_is_playing = is_playing
        if self.bg_video_player is not None:
            if is_playing:
                self.bg_video_player.play()
            else:
                self.bg_video_player.pause()

    def set_time(self, time_ms: float) -> None:
        self.current_time_ms = time_ms
        if self.background_mode == "custom" and self.bg_video_player is not None:
            pos_diff = abs(self.bg_video_player.position() - int(time_ms))
            if not self._bg_video_is_playing or pos_diff > 150:
                self.bg_video_player.setPosition(int(time_ms))
        self.update()

    def set_selection(self, word_ids: Set[str], primary_id: Optional[str]) -> None:
        self.selected_word_ids = set(word_ids)
        self.active_primary_word_id = primary_id if primary_id else None
        self.update()

    def toggle_guides(self, enabled: bool) -> None:
        self.show_safe_guides = enabled
        self.update()

    def set_background_mode(self, mode: str) -> None:
        self.background_mode = mode
        if self.bg_video_player is not None:
            if mode != "custom":
                self.bg_video_player.pause()
            elif self._bg_video_is_playing:
                self.bg_video_player.play()
        self.update()

    def load_background_media(self, filepath: str) -> bool:
        if not filepath or not os.path.exists(filepath):
            return False

        self.project.bg_media_path = filepath
        ext = os.path.splitext(filepath)[1].lower()

        if self.bg_video_player is not None:
            self.bg_video_player.stop()
            self.bg_video_player.deleteLater()
            self.bg_video_player = None
            self.bg_video_sink = None
            self.bg_video_audio_output = None

        if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            img = QImage(filepath)
            if not img.isNull():
                self.bg_image = img
                return True
        elif ext in (".mp4", ".mov", ".webm", ".mkv", ".avi"):
            self.bg_video_sink = QVideoSink(self)
            self.bg_video_sink.videoFrameChanged.connect(self._on_bg_video_frame)
            self.bg_video_audio_output = QAudioOutput(self)
            self.bg_video_audio_output.setMuted(True)
            self.bg_video_player = QMediaPlayer(self)
            self.bg_video_player.setAudioOutput(self.bg_video_audio_output)
            self.bg_video_player.setVideoSink(self.bg_video_sink)
            self.bg_video_player.setSource(QUrl.fromLocalFile(filepath))
            self.bg_video_player.setPosition(int(self.current_time_ms))
            if self._bg_video_is_playing and self.background_mode == "custom":
                self.bg_video_player.play()
            else:
                self.bg_video_player.pause()
            return True

        return False

    def _on_bg_video_frame(self, frame: QVideoFrame) -> None:
        if frame.isValid():
            img = frame.toImage()
            if not img.isNull():
                self.bg_image = img
                if self.background_mode == "custom":
                    self.update()

    def get_viewport_rect(self) -> Tuple[QRectF, float]:
        w_avail = self.width()
        h_avail = self.height()
        target_w = self.project.resolution_width
        target_h = self.project.resolution_height

        scale = min(w_avail / target_w, h_avail / target_h) * 0.94
        render_w = target_w * scale
        render_h = target_h * scale
        offset_x = (w_avail - render_w) / 2.0
        offset_y = (h_avail - render_h) / 2.0

        return QRectF(offset_x, offset_y, render_w, render_h), scale

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        painter.fillRect(self.rect(), QColor("#09090B"))

        canvas_rect, scale = self.get_viewport_rect()

        painter.save()
        painter.setClipRect(canvas_rect)

        if self.background_mode == "checkerboard":
            self._draw_checkerboard(painter, canvas_rect)
        elif self.background_mode == "custom" and self.bg_image is not None and not self.bg_image.isNull():
            painter.fillRect(canvas_rect, QColor("#000000"))
            img_w = self.bg_image.width()
            img_h = self.bg_image.height()
            if img_w > 0 and img_h > 0:
                img_scale = max(canvas_rect.width() / img_w, canvas_rect.height() / img_h)
                draw_w = img_w * img_scale
                draw_h = img_h * img_scale
                draw_x = canvas_rect.x() + (canvas_rect.width() - draw_w) / 2.0
                draw_y = canvas_rect.y() + (canvas_rect.height() - draw_h) / 2.0
                painter.drawImage(QRectF(draw_x, draw_y, draw_w, draw_h), self.bg_image)
            dim_alpha = int(round(max(0.0, min(1.0, self.project.bg_dim_opacity)) * 255))
            if dim_alpha > 0:
                painter.fillRect(canvas_rect, QColor(0, 0, 0, dim_alpha))
        else:
            painter.fillRect(canvas_rect, QColor("#000000"))

        painter.translate(canvas_rect.topLeft())
        painter.scale(scale, scale)

        self.engine.render_frame(
            painter,
            self.current_time_ms,
            self.selected_word_ids,
            self.active_primary_word_id,
        )
        painter.restore()

        if self.show_safe_guides:
            self._draw_safe_guides(painter, canvas_rect)

        border_pen = QPen(QColor("#27272A"), 1.0)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(canvas_rect)

    def _draw_checkerboard(self, painter: QPainter, rect: QRectF) -> None:
        sq = 16.0
        cols = int(rect.width() / sq) + 2
        rows = int(rect.height() / sq) + 2
        c1 = QColor("#121316")
        c2 = QColor("#18181B")
        for r in range(rows):
            for c in range(cols):
                color = c1 if (r + c) % 2 == 0 else c2
                sq_rect = QRectF(rect.x() + c * sq, rect.y() + r * sq, sq, sq)
                painter.fillRect(sq_rect.intersected(rect), color)

    def _draw_safe_guides(self, painter: QPainter, canvas_rect: QRectF) -> None:
        painter.save()
        pen = QPen(QColor(239, 68, 68, 120), 1.0, Qt.PenStyle.DashLine)
        painter.setPen(pen)

        w = canvas_rect.width()
        h = canvas_rect.height()
        top_guide = canvas_rect.top() + h * 0.14
        bottom_guide = canvas_rect.bottom() - h * 0.20
        left_guide = canvas_rect.left() + w * 0.06
        right_guide = canvas_rect.right() - w * 0.06

        painter.drawLine(QPointF(left_guide, top_guide), QPointF(right_guide, top_guide))
        painter.drawLine(QPointF(left_guide, bottom_guide), QPointF(right_guide, bottom_guide))
        painter.drawLine(QPointF(left_guide, top_guide), QPointF(left_guide, bottom_guide))
        painter.drawLine(QPointF(right_guide, top_guide), QPointF(right_guide, bottom_guide))

        anchor_y = canvas_rect.top() + h * self.project.align_y
        anchor_pen = QPen(QColor(59, 130, 246, 90), 1.0, Qt.PenStyle.DotLine)
        painter.setPen(anchor_pen)
        painter.drawLine(QPointF(left_guide, anchor_y), QPointF(right_guide, anchor_y))

        painter.restore()

    def _apply_click_selection(self, target_id: str, modifiers: Qt.KeyboardModifier) -> None:
        ctrl_held = bool(modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier))
        shift_held = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)

        new_set = set(self.selected_word_ids)
        new_primary = self.active_primary_word_id

        if ctrl_held:
            if target_id in new_set:
                new_set.remove(target_id)
                if new_primary == target_id:
                    new_primary = next(iter(new_set)) if new_set else None
            else:
                new_set.add(target_id)
                new_primary = target_id
        elif shift_held:
            new_set.add(target_id)
            new_primary = target_id
        else:
            new_set = {target_id}
            new_primary = target_id

        self.selected_word_ids = new_set
        self.active_primary_word_id = new_primary
        self.selection_changed.emit(set(self.selected_word_ids), self.active_primary_word_id or "")
        self.update()

    def mousePressEvent(self, event) -> None:
        canvas_rect, scale = self.get_viewport_rect()
        if not canvas_rect.contains(event.position()):
            return

        pos_in_canvas = (event.position() - canvas_rect.topLeft()) / scale
        active_stanza = self.project.get_active_stanza(self.current_time_ms)
        if not active_stanza:
            return

        layout_boxes = self.engine.compute_layout(active_stanza)
        matching_boxes = []
        for box in layout_boxes:
            b_rect = QRectF(box.x - 4, box.row_top_y - 2, box.width + 8, box.row_height + 4)
            if b_rect.contains(pos_in_canvas):
                matching_boxes.append(box)

        modifiers = event.modifiers()

        if len(matching_boxes) > 1:
            menu = QMenu(self)
            hdr = menu.addAction("SELECT OVERLAPPING WORD:")
            hdr.setEnabled(False)
            menu.addSeparator()

            action_to_id = {}
            for box in matching_boxes:
                t_s = box.word.start_ms / 1000.0
                t_e = box.word.end_ms / 1000.0
                act = menu.addAction(f'"{box.display_text}"  ({t_s:.2f}s - {t_e:.2f}s | Line {box.word.line_index})')
                action_to_id[act] = box.word.id

            global_pt = self.mapToGlobal(event.position().toPoint())
            chosen = menu.exec(global_pt)
            if chosen and chosen in action_to_id:
                self._apply_click_selection(action_to_id[chosen], modifiers)
            return

        elif len(matching_boxes) == 1:
            self._apply_click_selection(matching_boxes[0].word.id, modifiers)
            return

        if not (modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)):
            self.selected_word_ids.clear()
            self.active_primary_word_id = None
            self.selection_changed.emit(set(), "")
            self.update()


# ==============================================================================
# 6. MULTI-TRACK TIMELINE & WAVEFORM SEQUENCER
# ==============================================================================

class WaveformLoaderThread(QThread):
    """Asynchronously decodes audio file samples into an RMS waveform visual buffer."""
    waveform_ready = Signal(object)

    def __init__(self, audio_path: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.audio_path = audio_path

    def run(self) -> None:
        if not shutil.which("ffmpeg"):
            return

        try:
            cmd = [
                "ffmpeg", "-i", self.audio_path,
                "-ac", "1", "-ar", "8000",
                "-f", "s16le", "-v", "quiet", "-"
            ]
            flags = get_subprocess_creation_flags()
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                **flags
            )
            raw_bytes, _ = proc.communicate()
            if not raw_bytes:
                return

            samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
            if len(samples) == 0:
                return

            max_val = np.max(np.abs(samples))
            if max_val > 0:
                samples /= max_val

            chunk_size = 200
            num_chunks = len(samples) // chunk_size
            if num_chunks == 0:
                return

            reshaped = samples[:num_chunks * chunk_size].reshape((num_chunks, chunk_size))
            rms = np.sqrt(np.mean(reshaped ** 2, axis=1))
            self.waveform_ready.emit(rms)
        except Exception:
            pass


class TimelineWidget(QWidget):
    """
    Professional NLE multi-track keyframe sequencer featuring:
    - Dedicated 4px CapCut/Resolve edge trim handles with inner notches
    - Live cursor state switching (SizeHorCursor, SizeAllCursor, ArrowCursor)
    - Live trim/translation delta HUD tooltip (`00:01.450 (+120ms)`)
    - Rubber-band marquee multi-selection & modifier click selection
    - Atomic batch movement, trimming, and deletion with QUndoStack integration
    """
    time_scrubbed = Signal(int)
    selection_changed = Signal(set, str)
    project_changed = Signal()
    duration_expanded = Signal(int)
    batch_timing_committed = Signal(list)
    delete_selected_requested = Signal()

    BASE_Y = 36
    ROW_H = 22
    ROW_SPACING = 4
    EDGE_HIT_TOLERANCE_PX = 6.0

    def __init__(self, project: LyricProject, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.project = project
        self.current_time_ms = 0
        self.selected_word_ids: Set[str] = set()
        self.active_primary_word_id: Optional[str] = None
        self.pixels_per_second = 180.0
        self.scroll_offset_x = 0.0
        self.scrollbar: Optional[QScrollBar] = None

        self.waveform_data: Optional[np.ndarray] = None
        self.waveform_thread: Optional[WaveformLoaderThread] = None

        # Drag & Trim states
        self._dragging_playhead = False
        self._dragging_words = False
        self._resizing_word_left = False
        self._resizing_word_right = False
        self._active_drag_word: Optional[WordKeyframe] = None
        self._drag_start_x = 0.0
        self._drag_orig_bounds: Dict[str, Tuple[int, int]] = {}
        self._trim_tooltip_text: Optional[str] = None
        self._trim_tooltip_pos: QPointF = QPointF()

        # Rubber-band Marquee states
        self._is_marquee_selecting = False
        self._marquee_start_pos = QPointF()
        self._marquee_current_pos = QPointF()
        self._marquee_initial_selection: Set[str] = set()
        self._marquee_initial_primary: Optional[str] = None

        self.setMouseTracking(True)
        self.setMinimumHeight(150)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_project(self, project: LyricProject) -> None:
        self.project = project
        self.scroll_offset_x = 0.0
        self.update()
        self.update_scrollbar()

    def set_time(self, time_ms: int) -> None:
        self.current_time_ms = time_ms
        self.update()

    def set_selection(self, word_ids: Set[str], primary_id: Optional[str]) -> None:
        self.selected_word_ids = set(word_ids)
        self.active_primary_word_id = primary_id if primary_id else None
        self.update()

    def set_zoom(self, px_per_sec: float) -> None:
        self.pixels_per_second = max(40.0, min(800.0, px_per_sec))
        self.update()
        self.update_scrollbar()

    def set_scrollbar(self, scrollbar: QScrollBar) -> None:
        self.scrollbar = scrollbar
        self.scrollbar.valueChanged.connect(self._on_scrollbar_value_changed)
        self.update_scrollbar()

    def _on_scrollbar_value_changed(self, value: int) -> None:
        if int(round(self.scroll_offset_x)) != value:
            self.scroll_offset_x = float(value)
            self.update()

    def update_scrollbar(self) -> None:
        if not hasattr(self, "scrollbar") or self.scrollbar is None:
            return
        total_ms = self.project.duration_ms
        for s in self.project.stanzas:
            if s.end_ms > total_ms:
                total_ms = s.end_ms
            for w in s.words:
                if w.end_ms > total_ms:
                    total_ms = w.end_ms
        max_sec = math.ceil(max(1000, total_ms) / 1000.0) + 1
        total_width = int(math.ceil(max_sec * self.pixels_per_second))
        visible_width = max(1, self.width())
        max_scroll = max(0, total_width - visible_width)

        old_offset = self.scroll_offset_x
        if self.scroll_offset_x > max_scroll:
            self.scroll_offset_x = float(max_scroll)
        elif self.scroll_offset_x < 0.0:
            self.scroll_offset_x = 0.0
        if self.scroll_offset_x != old_offset:
            self.update()

        self.scrollbar.blockSignals(True)
        self.scrollbar.setRange(0, max_scroll)
        self.scrollbar.setPageStep(visible_width)
        self.scrollbar.setSingleStep(max(1, int(self.pixels_per_second * 0.2)))
        self.scrollbar.setValue(int(round(self.scroll_offset_x)))
        self.scrollbar.blockSignals(False)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_scrollbar()

    def load_audio_waveform(self, path: str) -> None:
        self.waveform_thread = WaveformLoaderThread(path, self)
        self.waveform_thread.waveform_ready.connect(self._on_waveform_ready)
        self.waveform_thread.start()

    def _on_waveform_ready(self, rms_data: np.ndarray) -> None:
        self.waveform_data = rms_data
        self.update()

    def time_to_x(self, time_ms: float) -> float:
        return (time_ms / 1000.0) * self.pixels_per_second - self.scroll_offset_x

    def x_to_time(self, x: float) -> int:
        t_sec = (x + self.scroll_offset_x) / self.pixels_per_second
        return max(0, int(round(t_sec * 1000.0)))

    def _compute_word_geometry(self, word: WordKeyframe) -> Tuple[QRectF, float, float, float]:
        wx = self.time_to_x(word.start_ms)
        ww = max(18.0, abs(self.time_to_x(word.end_ms) - wx))
        line_idx = max(0, min(5, int(word.line_index)))
        wy = self.BASE_Y + line_idx * (self.ROW_H + self.ROW_SPACING)
        rect = QRectF(wx, wy, ww, self.ROW_H)
        return rect, wx, wy, ww

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor("#09090B"))

        ruler_rect = QRectF(0, 0, self.width(), 24)
        painter.fillRect(ruler_rect, QColor("#121316"))
        painter.setPen(QPen(QColor("#27272A"), 1.0))
        painter.drawLine(QPointF(0, 24), QPointF(self.width(), 24))
        self._draw_ruler(painter)

        tracks_rect = QRectF(0, 25, self.width(), self.height() - 25)
        painter.save()
        painter.setClipRect(tracks_rect)

        if self.waveform_data is not None and len(self.waveform_data) > 0:
            self._draw_waveform(painter, tracks_rect)

        self._draw_blocks(painter)

        if self._is_marquee_selecting:
            self._draw_marquee(painter)

        painter.restore()

        self._draw_playhead(painter)

        if self._trim_tooltip_text:
            self._draw_trim_tooltip(painter)

    def _draw_ruler(self, painter: QPainter) -> None:
        painter.save()
        pen_tick = QPen(QColor("#3F3F46"), 1.0)
        pen_sub = QPen(QColor("#27272A"), 1.0)
        font = QFont("JetBrains Mono", 8)
        font.setStyleHint(QFont.StyleHint.Monospace)
        painter.setFont(font)

        sec_width = self.pixels_per_second
        if sec_width >= 240:
            step_sec = 0.5
            sub_step_sec = 0.1
        elif sec_width >= 100:
            step_sec = 1.0
            sub_step_sec = 0.25
        elif sec_width >= 40:
            step_sec = 2.0
            sub_step_sec = 0.5
        else:
            step_sec = 5.0
            sub_step_sec = 1.0

        max_sec = math.ceil(self.project.duration_ms / 1000.0) + 1
        curr_sub = 0.0
        while curr_sub <= max_sec:
            x = self.time_to_x(curr_sub * 1000.0)
            if -10 <= x <= self.width() + 10:
                is_major = abs(curr_sub % step_sec) < 1e-4 or abs((curr_sub % step_sec) - step_sec) < 1e-4
                if is_major:
                    painter.setPen(pen_tick)
                    painter.drawLine(QPointF(x, 14), QPointF(x, 24))
                    painter.setPen(QColor("#71717A"))
                    m, s = divmod(int(curr_sub), 60)
                    txt = f"{m}:{s:02d}" if m > 0 else f"{curr_sub:.1f}s"
                    painter.drawText(QPointF(x + 3, 16), txt)
                else:
                    painter.setPen(pen_sub)
                    painter.drawLine(QPointF(x, 19), QPointF(x, 24))
            curr_sub += sub_step_sec

        painter.restore()

    def _draw_waveform(self, painter: QPainter, tracks_rect: QRectF) -> None:
        painter.save()
        wf_color = QColor(59, 130, 246, 95)
        painter.setPen(QPen(wf_color, 1.0))

        mid_y = tracks_rect.top() + tracks_rect.height() / 2.0
        half_h = (tracks_rect.height() - 10) / 2.0

        num_pts = len(self.waveform_data)
        total_time_ms = max(1, self.project.duration_ms)

        step = max(1, int(num_pts / (self.width() * 2)))
        for i in range(0, num_pts, step):
            t_ms = (i / float(num_pts)) * total_time_ms
            x = self.time_to_x(t_ms)
            if 0 <= x <= self.width():
                val = self.waveform_data[i] * half_h
                painter.drawLine(QPointF(x, mid_y - val), QPointF(x, mid_y + val))

        painter.restore()

    def _draw_blocks(self, painter: QPainter) -> None:
        painter.save()
        font = QFont("JetBrains Mono", 8, QFont.Weight.Bold)
        painter.setFont(font)

        for stanza_idx, stanza in enumerate(self.project.stanzas):
            st_x = self.time_to_x(stanza.start_ms)
            en_x = self.time_to_x(stanza.end_ms)
            painter.setPen(QPen(QColor("#27272A"), 1.0, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(st_x, 24), QPointF(st_x, self.height()))
            painter.drawLine(QPointF(en_x, 24), QPointF(en_x, self.height()))

            painter.setPen(QPen(QColor("#3B82F6"), 1.0))
            painter.drawLine(QPointF(st_x, 28), QPointF(en_x, 28))
            painter.setPen(QColor("#3B82F6"))
            painter.drawText(QPointF(st_x + 3, 34), f"S{stanza_idx + 1} [{stanza.layout_preset[:5].upper()}]")

            for word in stanza.words:
                rect, wx, wy, ww = self._compute_word_geometry(word)
                is_selected = word.id in self.selected_word_ids
                is_primary = (word.id == self.active_primary_word_id)

                if is_selected:
                    fill_color = QColor("#18181B")
                    border_color = QColor("#3B82F6")
                    pen_width = 1.5 if is_primary else 1.0
                else:
                    fill_color = QColor("#121316")
                    border_color = QColor("#27272A")
                    pen_width = 1.0

                painter.setPen(QPen(border_color, pen_width))
                painter.setBrush(QBrush(fill_color))
                painter.drawRect(rect)

                # Render NLE 4px end-bracket trim handles on every selected word block
                if is_selected:
                    accent = QColor("#3B82F6")
                    notch = QColor("#09090B")
                    handle_w = 4.0

                    # Left 4px vertical handle bar + inward bracket lips + 1px inner notch
                    painter.fillRect(QRectF(wx, wy, handle_w, self.ROW_H), accent)
                    painter.fillRect(QRectF(wx + handle_w, wy, 2.0, 2.0), accent)
                    painter.fillRect(QRectF(wx + handle_w, wy + self.ROW_H - 2.0, 2.0, 2.0), accent)
                    painter.fillRect(QRectF(wx + 1.5, wy + 5.0, 1.0, self.ROW_H - 10.0), notch)

                    # Right 4px vertical handle bar + inward bracket lips + 1px inner notch
                    rx = wx + ww - handle_w
                    painter.fillRect(QRectF(rx, wy, handle_w, self.ROW_H), accent)
                    painter.fillRect(QRectF(rx - 2.0, wy, 2.0, 2.0), accent)
                    painter.fillRect(QRectF(rx - 2.0, wy + self.ROW_H - 2.0, 2.0, 2.0), accent)
                    painter.fillRect(QRectF(rx + 1.5, wy + 5.0, 1.0, self.ROW_H - 10.0), notch)

                painter.setPen(QColor("#E4E4E7"))
                label_rect = QRectF(wx + 6, wy, max(0.0, ww - 12), self.ROW_H)
                painter.drawText(
                    label_rect,
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    word.text
                )

        painter.restore()

    def _draw_marquee(self, painter: QPainter) -> None:
        painter.save()
        marquee_rect = QRectF(self._marquee_start_pos, self._marquee_current_pos).normalized()
        painter.setPen(QPen(QColor("#3B82F6"), 1.0, Qt.PenStyle.DashLine))
        painter.setBrush(QBrush(QColor(59, 130, 246, 30)))
        painter.drawRect(marquee_rect)
        painter.restore()

    def _draw_playhead(self, painter: QPainter) -> None:
        x = self.time_to_x(self.current_time_ms)
        painter.save()
        head_pen = QPen(QColor("#EF4444"), 1.5)
        painter.setPen(head_pen)
        painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))

        handle_rect = QRectF(x - 4, 0, 8, 12)
        painter.fillRect(handle_rect, QColor("#EF4444"))
        painter.restore()

    def _draw_trim_tooltip(self, painter: QPainter) -> None:
        if not self._trim_tooltip_text:
            return
        painter.save()
        font = QFont("JetBrains Mono", 9, QFont.Weight.Bold)
        font.setStyleHint(QFont.StyleHint.Monospace)
        painter.setFont(font)
        metrics = QFontMetricsF(font)
        tw = metrics.horizontalAdvance(self._trim_tooltip_text) + 12.0
        th = 20.0

        tx = min(max(4.0, self._trim_tooltip_pos.x() + 10.0), max(4.0, self.width() - tw - 4.0))
        ty = max(26.0, self._trim_tooltip_pos.y() - 26.0)
        box_rect = QRectF(tx, ty, tw, th)

        painter.fillRect(box_rect, QColor("#121316"))
        painter.setPen(QPen(QColor("#3B82F6"), 1.0))
        painter.drawRect(box_rect)
        painter.setPen(QColor("#E4E4E7"))
        painter.drawText(box_rect, Qt.AlignmentFlag.AlignCenter, self._trim_tooltip_text)
        painter.restore()

    def _update_hover_cursor(self, pos: QPointF) -> None:
        if pos.y() <= 24:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        for stanza in self.project.stanzas:
            for word in stanza.words:
                rect, wx, wy, ww = self._compute_word_geometry(word)
                expanded_rect = QRectF(wx - 2.0, wy, ww + 4.0, self.ROW_H)
                if expanded_rect.contains(pos):
                    if (
                        abs(pos.x() - wx) <= self.EDGE_HIT_TOLERANCE_PX
                        or abs(pos.x() - (wx + ww)) <= self.EDGE_HIT_TOLERANCE_PX
                    ):
                        self.setCursor(Qt.CursorShape.SizeHorCursor)
                    else:
                        self.setCursor(Qt.CursorShape.SizeAllCursor)
                    return

        self.setCursor(Qt.CursorShape.ArrowCursor)

    def _initiate_word_interaction(
        self,
        word: WordKeyframe,
        wx: float,
        ww: float,
        pos: QPointF,
        modifiers: Qt.KeyboardModifier,
    ) -> None:
        ctrl_held = bool(modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier))
        shift_held = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)

        near_left = abs(pos.x() - wx) <= self.EDGE_HIT_TOLERANCE_PX
        near_right = abs(pos.x() - (wx + ww)) <= self.EDGE_HIT_TOLERANCE_PX

        if ctrl_held:
            if word.id in self.selected_word_ids:
                self.selected_word_ids.remove(word.id)
                if self.active_primary_word_id == word.id:
                    self.active_primary_word_id = (
                        next(iter(self.selected_word_ids)) if self.selected_word_ids else None
                    )
                self.selection_changed.emit(set(self.selected_word_ids), self.active_primary_word_id or "")
                self.update()
                return
            else:
                self.selected_word_ids.add(word.id)
                self.active_primary_word_id = word.id
        elif shift_held:
            self.selected_word_ids.add(word.id)
            self.active_primary_word_id = word.id
        else:
            if word.id not in self.selected_word_ids or near_left or near_right:
                self.selected_word_ids = {word.id}
            self.active_primary_word_id = word.id

        self.selection_changed.emit(set(self.selected_word_ids), self.active_primary_word_id or "")

        self._active_drag_word = word
        self._drag_start_x = pos.x()
        self._drag_orig_bounds.clear()

        if near_left:
            self._resizing_word_left = True
            self._drag_orig_bounds[word.id] = (word.start_ms, word.end_ms)
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif near_right:
            self._resizing_word_right = True
            self._drag_orig_bounds[word.id] = (word.start_ms, word.end_ms)
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self._dragging_words = True
            for s in self.project.stanzas:
                for w in s.words:
                    if w.id in self.selected_word_ids:
                        self._drag_orig_bounds[w.id] = (w.start_ms, w.end_ms)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position()
        click_time = self.x_to_time(pos.x())
        modifiers = event.modifiers()

        # Ruler click scrubs playhead
        if pos.y() <= 24:
            self._dragging_playhead = True
            self.set_time(click_time)
            self.time_scrubbed.emit(click_time)
            return

        hit_words = []
        for stanza in self.project.stanzas:
            for word in stanza.words:
                rect, wx, wy, ww = self._compute_word_geometry(word)
                hit_rect = QRectF(wx - 2.0, wy - 2.0, ww + 4.0, self.ROW_H + 4.0)
                if hit_rect.contains(pos):
                    hit_words.append((stanza, word, rect, wx, ww))

        if len(hit_words) > 1:
            menu = QMenu(self)
            hdr = menu.addAction("SELECT OVERLAPPING WORD:")
            hdr.setEnabled(False)
            menu.addSeparator()

            action_to_word = {}
            for stanza, word, rect, wx, ww in hit_words:
                t_s = word.start_ms / 1000.0
                t_e = word.end_ms / 1000.0
                label = f'"{word.text}"  ({t_s:.2f}s - {t_e:.2f}s | Line {word.line_index})'
                act = menu.addAction(label)
                action_to_word[act] = (word, wx, ww)

            chosen = menu.exec(self.mapToGlobal(pos.toPoint()))
            if chosen and chosen in action_to_word:
                word, wx, ww = action_to_word[chosen]
                self._initiate_word_interaction(word, wx, ww, pos, modifiers)
            return

        elif len(hit_words) == 1:
            _, word, _, wx, ww = hit_words[0]
            self._initiate_word_interaction(word, wx, ww, pos, modifiers)
            return

        # Empty track space: start rubber-band marquee selection
        additive = bool(
            modifiers & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)
        )
        self._is_marquee_selecting = True
        self._marquee_start_pos = pos
        self._marquee_current_pos = pos

        if additive:
            self._marquee_initial_selection = set(self.selected_word_ids)
            self._marquee_initial_primary = self.active_primary_word_id
        else:
            self._marquee_initial_selection = set()
            self._marquee_initial_primary = None
            self.selected_word_ids.clear()
            self.active_primary_word_id = None
            self.set_time(click_time)
            self.time_scrubbed.emit(click_time)
            self.selection_changed.emit(set(), "")

        self.update()

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()

        if self._dragging_playhead:
            new_time = self.x_to_time(pos.x())
            self.set_time(new_time)
            self.time_scrubbed.emit(new_time)
            return

        if self._is_marquee_selecting:
            self._marquee_current_pos = pos
            marquee_rect = QRectF(self._marquee_start_pos, self._marquee_current_pos).normalized()

            intersected_ids: Set[str] = set(self._marquee_initial_selection)
            last_hit_id: Optional[str] = self._marquee_initial_primary

            for stanza in self.project.stanzas:
                for word in stanza.words:
                    rect, _, _, _ = self._compute_word_geometry(word)
                    if marquee_rect.intersects(rect):
                        intersected_ids.add(word.id)
                        last_hit_id = word.id

            if not intersected_ids:
                last_hit_id = None
            elif last_hit_id not in intersected_ids:
                last_hit_id = next(iter(intersected_ids))

            if intersected_ids != self.selected_word_ids or last_hit_id != self.active_primary_word_id:
                self.selected_word_ids = intersected_ids
                self.active_primary_word_id = last_hit_id
                self.selection_changed.emit(set(self.selected_word_ids), self.active_primary_word_id or "")

            self.update()
            return

        if self._active_drag_word is not None:
            delta_px = pos.x() - self._drag_start_x
            raw_delta_ms = int(round((delta_px / self.pixels_per_second) * 1000.0))
            affected_stanzas: List[Stanza] = []
            max_end_ms = self.project.duration_ms

            if self._dragging_words and self._drag_orig_bounds:
                min_orig_start = min(s_ms for s_ms, _ in self._drag_orig_bounds.values())
                clamped_delta_ms = max(-min_orig_start, raw_delta_ms)

                for stanza in self.project.stanzas:
                    stanza_touched = False
                    for w in stanza.words:
                        if w.id in self._drag_orig_bounds:
                            orig_s, orig_e = self._drag_orig_bounds[w.id]
                            dur = orig_e - orig_s
                            w.start_ms = orig_s + clamped_delta_ms
                            w.end_ms = w.start_ms + dur
                            max_end_ms = max(max_end_ms, w.end_ms)
                            stanza_touched = True
                    if stanza_touched:
                        affected_stanzas.append(stanza)

                sign = "+" if clamped_delta_ms >= 0 else ""
                tc = format_ms_timecode(self._active_drag_word.start_ms)
                self._trim_tooltip_text = f"{tc} ({sign}{clamped_delta_ms}ms)"
                self._trim_tooltip_pos = pos

            elif self._resizing_word_left:
                w = self._active_drag_word
                orig_s, orig_e = self._drag_orig_bounds[w.id]
                new_start = max(0, min(orig_e - 50, orig_s + raw_delta_ms))
                applied_delta = new_start - orig_s
                w.start_ms = new_start
                for s in self.project.stanzas:
                    if w in s.words:
                        affected_stanzas.append(s)
                        break

                sign = "+" if applied_delta >= 0 else ""
                tc = format_ms_timecode(w.start_ms)
                self._trim_tooltip_text = f"{tc} ({sign}{applied_delta}ms)"
                self._trim_tooltip_pos = pos

            elif self._resizing_word_right:
                w = self._active_drag_word
                orig_s, orig_e = self._drag_orig_bounds[w.id]
                new_end = max(orig_s + 50, orig_e + raw_delta_ms)
                applied_delta = new_end - orig_e
                w.end_ms = new_end
                max_end_ms = max(max_end_ms, w.end_ms)
                for s in self.project.stanzas:
                    if w in s.words:
                        affected_stanzas.append(s)
                        break

                sign = "+" if applied_delta >= 0 else ""
                tc = format_ms_timecode(w.end_ms)
                self._trim_tooltip_text = f"{tc} ({sign}{applied_delta}ms)"
                self._trim_tooltip_pos = pos

            if max_end_ms > self.project.duration_ms:
                self.project.duration_ms = max_end_ms + 1000
                self.duration_expanded.emit(self.project.duration_ms)
                self.update_scrollbar()

            for s in affected_stanzas:
                s.recompute_bounds()

            self.project_changed.emit()
            self.update()
            return

        # Not dragging: update cursor feedback based on hover zone
        self._update_hover_cursor(pos)

    def mouseReleaseEvent(self, event) -> None:
        if self._active_drag_word is not None and self._drag_orig_bounds:
            changes: List[Tuple[str, int, int, int, int]] = []
            for s in self.project.stanzas:
                for w in s.words:
                    if w.id in self._drag_orig_bounds:
                        orig_s, orig_e = self._drag_orig_bounds[w.id]
                        if w.start_ms != orig_s or w.end_ms != orig_e:
                            changes.append((w.id, orig_s, orig_e, w.start_ms, w.end_ms))
            if changes:
                self.batch_timing_committed.emit(changes)

        self._dragging_playhead = False
        self._dragging_words = False
        self._resizing_word_left = False
        self._resizing_word_right = False
        self._active_drag_word = None
        self._drag_orig_bounds.clear()
        self._trim_tooltip_text = None
        self._is_marquee_selecting = False

        self._update_hover_cursor(event.position())
        self.update()

    def leaveEvent(self, event) -> None:
        if not (self._dragging_words or self._resizing_word_left or self._resizing_word_right):
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.selected_word_ids:
                self.delete_selected_requested.emit()
                event.accept()
                return
        elif event.key() == Qt.Key.Key_A and (
            event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)
        ):
            all_ids = self.project.get_all_word_ids()
            primary = self.active_primary_word_id
            if not primary or primary not in all_ids:
                primary = next(iter(all_ids)) if all_ids else None
            self.set_selection(all_ids, primary)
            self.selection_changed.emit(set(all_ids), primary or "")
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Escape:
            self.set_selection(set(), None)
            self.selection_changed.emit(set(), "")
            event.accept()
            return

        super().keyPressEvent(event)

    def wheelEvent(self, event) -> None:
        modifiers = event.modifiers()
        if modifiers & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.AltModifier):
            delta = event.angleDelta().y()
            self.scroll_offset_x = max(0.0, self.scroll_offset_x - delta)
            self.update()
            self.update_scrollbar()
        else:
            cursor_x = event.position().x()
            cursor_time = self.x_to_time(cursor_x)
            factor = 1.15 if event.angleDelta().y() > 0 else 0.85
            self.pixels_per_second = max(40.0, min(800.0, self.pixels_per_second * factor))
            self.scroll_offset_x = max(0.0, (cursor_time / 1000.0) * self.pixels_per_second - cursor_x)
            self.update()
            self.update_scrollbar()


# ==============================================================================
# 7. PARAMETER INSPECTOR & KINETIC CONTROLS
# ==============================================================================

class WordInspectorWidget(QWidget):
    """
    Inspector sidebar providing deterministic control over per-word and batch
    multi-selected word parameters, stanza animation presets, stroke outlines,
    typography tracking/leading/casing, vertical layout alignment presets,
    and atomic QUndoStack command dispatch.
    """
    word_updated = Signal()
    batch_property_committed = Signal(str, list)
    batch_timing_committed = Signal(list)
    delete_requested = Signal()
    add_word_requested = Signal()
    new_stanza_requested = Signal()
    delete_stanza_requested = Signal()

    def __init__(self, project: LyricProject, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.project = project
        self.selected_word_ids: Set[str] = set()
        self.active_word_id: Optional[str] = None
        self._is_updating_ui = False
        self.setObjectName("dockPanel")
        self._setup_ui()
        self._sync_global_controls()
        self.set_selection(set(), None)

    def set_project(self, project: LyricProject) -> None:
        self.project = project
        self._sync_global_controls()
        self.set_selection(self.selected_word_ids, self.active_word_id)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        lbl_title = QLabel("PARAMETER INSPECTOR")
        lbl_title.setObjectName("panelHeader")
        layout.addWidget(lbl_title)

        self.lbl_selection_telemetry = QLabel("[NO WORD SELECTED]")
        self.lbl_selection_telemetry.setObjectName("telemetryBanner")
        layout.addWidget(self.lbl_selection_telemetry)

        # Global Typography & Shader Controls
        typo_group = QGroupBox("Typography & Shader Engine")
        typo_layout = QVBoxLayout(typo_group)
        typo_layout.setSpacing(4)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Kinetic Preset:"))
        self.combo_preset = QComboBox()
        self.combo_preset.addItem("Stacked Punch", "stacked_punch")
        self.combo_preset.addItem("Box Badge (Inverted)", "box_badge")
        self.combo_preset.addItem("Word Stagger Drift", "word_stagger")
        self.combo_preset.addItem("Hard-Cut Glitch", "hard_cut_glitch")
        self.combo_preset.currentIndexChanged.connect(self._on_preset_changed)
        preset_row.addWidget(self.combo_preset)
        typo_layout.addLayout(preset_row)

        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Global Font:"))
        self.combo_global_font = QComboBox()
        self.combo_global_font.setEditable(True)
        self.combo_global_font.currentTextChanged.connect(self._on_global_font_changed)
        font_row.addWidget(self.combo_global_font)

        self.btn_load_global_font = QPushButton("Load...")
        self.btn_load_global_font.setToolTip("Load custom font file (.ttf, .otf, .woff)")
        self.btn_load_global_font.clicked.connect(self._on_load_global_font_file)
        font_row.addWidget(self.btn_load_global_font)
        typo_layout.addLayout(font_row)

        case_row = QHBoxLayout()
        case_row.addWidget(QLabel("Text Casing:"))
        self.combo_casing = QComboBox()
        self.combo_casing.addItem("ALL CAPS", "ALL_CAPS")
        self.combo_casing.addItem("Title Case", "TITLE_CASE")
        self.combo_casing.addItem("As Typed", "AS_TYPED")
        self.combo_casing.currentIndexChanged.connect(self._on_casing_changed)
        case_row.addWidget(self.combo_casing)
        typo_layout.addLayout(case_row)

        align_row = QHBoxLayout()
        align_row.addWidget(QLabel("Vertical Anchor:"))
        self.combo_valign = QComboBox()
        self.combo_valign.addItem("Top-Third (22%)", 0.22)
        self.combo_valign.addItem("Reels Safe Zone (42%)", 0.42)
        self.combo_valign.addItem("Center (45%)", 0.45)
        self.combo_valign.addItem("Bottom-Third (68%)", 0.68)
        self.combo_valign.currentIndexChanged.connect(self._on_valign_changed)
        align_row.addWidget(self.combo_valign)
        typo_layout.addLayout(align_row)

        ls_row = QHBoxLayout()
        ls_row.addWidget(QLabel("Letter Spacing (%):"))
        self.spin_letter_spacing = QDoubleSpinBox()
        self.spin_letter_spacing.setRange(-10.0, 20.0)
        self.spin_letter_spacing.setSingleStep(0.5)
        self.spin_letter_spacing.valueChanged.connect(self._on_letter_spacing_changed)
        ls_row.addWidget(self.spin_letter_spacing)
        typo_layout.addLayout(ls_row)

        lh_row = QHBoxLayout()
        lh_row.addWidget(QLabel("Line Height (x):"))
        self.spin_line_height = QDoubleSpinBox()
        self.spin_line_height.setRange(0.80, 1.50)
        self.spin_line_height.setSingleStep(0.02)
        self.spin_line_height.valueChanged.connect(self._on_line_height_changed)
        lh_row.addWidget(self.spin_line_height)
        typo_layout.addLayout(lh_row)

        stroke_row = QHBoxLayout()
        stroke_row.addWidget(QLabel("Stroke Width (px):"))
        self.spin_stroke_width = QDoubleSpinBox()
        self.spin_stroke_width.setRange(0.0, 12.0)
        self.spin_stroke_width.setSingleStep(0.5)
        self.spin_stroke_width.valueChanged.connect(self._on_stroke_width_changed)
        stroke_row.addWidget(self.spin_stroke_width)

        self.btn_stroke_color = QPushButton("Stroke #000000")
        self.btn_stroke_color.clicked.connect(self._on_pick_stroke_color)
        stroke_row.addWidget(self.btn_stroke_color)
        typo_layout.addLayout(stroke_row)

        layout.addWidget(typo_group)

        # Selected Word / Batch Controls
        self.word_container = QWidget()
        word_layout = QVBoxLayout(self.word_container)
        word_layout.setContentsMargins(0, 0, 0, 0)
        word_layout.setSpacing(6)

        txt_group = QGroupBox("Active Word Token")
        txt_layout = QVBoxLayout(txt_group)
        txt_layout.setSpacing(4)
        self.edit_text = QLineEdit()
        self.edit_text.setPlaceholderText("WORD")
        self.edit_text.textEdited.connect(self._on_text_edited)
        txt_layout.addWidget(self.edit_text)

        line_row = QHBoxLayout()
        line_row.addWidget(QLabel("Stack Row:"))
        self.combo_line = QComboBox()
        self.combo_line.addItems([
            "Line 0 (Top Punch)",
            "Line 1 (Middle)",
            "Line 2 (Base)",
            "Line 3 (Row 4)",
            "Line 4 (Row 5)",
            "Line 5 (Row 6)",
        ])
        self.combo_line.currentIndexChanged.connect(self._on_line_changed)
        line_row.addWidget(self.combo_line)
        txt_layout.addLayout(line_row)
        word_layout.addWidget(txt_group)

        word_font_group = QGroupBox("Word & Letter Typography")
        wf_layout = QVBoxLayout(word_font_group)
        wf_layout.setSpacing(4)

        w_font_row = QHBoxLayout()
        w_font_row.addWidget(QLabel("Word Font:"))
        self.combo_word_font = QComboBox()
        self.combo_word_font.setEditable(True)
        self.combo_word_font.currentTextChanged.connect(self._on_word_font_changed)
        w_font_row.addWidget(self.combo_word_font)

        self.btn_load_word_font = QPushButton("Load...")
        self.btn_load_word_font.setToolTip("Load custom font file for this word")
        self.btn_load_word_font.clicked.connect(self._on_load_word_font_file)
        w_font_row.addWidget(self.btn_load_word_font)
        wf_layout.addLayout(w_font_row)

        lbl_letter_ovr = QLabel("Letter Font Overrides:")
        lbl_letter_ovr.setObjectName("mutedLabel")
        wf_layout.addWidget(lbl_letter_ovr)

        l_sel_row = QHBoxLayout()
        l_sel_row.addWidget(QLabel("Target Letter:"))
        self.combo_letter_idx = QComboBox()
        self.combo_letter_idx.currentIndexChanged.connect(self._on_letter_idx_changed)
        l_sel_row.addWidget(self.combo_letter_idx)
        wf_layout.addLayout(l_sel_row)

        l_font_row = QHBoxLayout()
        l_font_row.addWidget(QLabel("Letter Font:"))
        self.combo_letter_font = QComboBox()
        self.combo_letter_font.setEditable(True)
        self.combo_letter_font.currentTextChanged.connect(self._on_letter_font_changed)
        l_font_row.addWidget(self.combo_letter_font)

        self.btn_load_letter_font = QPushButton("Load...")
        self.btn_load_letter_font.setToolTip("Load custom font file for selected letter")
        self.btn_load_letter_font.clicked.connect(self._on_load_letter_font_file)
        l_font_row.addWidget(self.btn_load_letter_font)
        wf_layout.addLayout(l_font_row)

        l_act_row = QHBoxLayout()
        self.btn_reset_letter = QPushButton("Reset Letter")
        self.btn_reset_letter.setToolTip("Clear custom font for the selected letter")
        self.btn_reset_letter.clicked.connect(self._on_reset_selected_letter_font)
        l_act_row.addWidget(self.btn_reset_letter)

        self.btn_clear_all_letters = QPushButton("Clear All Letters")
        self.btn_clear_all_letters.setToolTip("Clear all letter font overrides on this word")
        self.btn_clear_all_letters.clicked.connect(self._on_clear_all_letter_fonts)
        l_act_row.addWidget(self.btn_clear_all_letters)
        wf_layout.addLayout(l_act_row)

        word_layout.addWidget(word_font_group)

        scale_group = QGroupBox("Punch Scale & Vector Offsets")
        scale_layout = QVBoxLayout(scale_group)
        scale_layout.setSpacing(4)
        scale_val_box = QHBoxLayout()
        self.lbl_scale = QLabel("1.0x")
        self.lbl_scale.setObjectName("accentValueLabel")
        scale_val_box.addWidget(QLabel("Scale Multiplier:"))
        scale_val_box.addStretch()
        scale_val_box.addWidget(self.lbl_scale)
        scale_layout.addLayout(scale_val_box)

        self.slider_scale = QSlider(Qt.Orientation.Horizontal)
        self.slider_scale.setRange(8, 30)
        self.slider_scale.setValue(10)
        self.slider_scale.valueChanged.connect(self._on_scale_slider)
        scale_layout.addWidget(self.slider_scale)

        xy_box = QHBoxLayout()
        xy_box.addWidget(QLabel("X:"))
        self.spin_x = QDoubleSpinBox()
        self.spin_x.setRange(-400.0, 400.0)
        self.spin_x.setSingleStep(2.0)
        self.spin_x.valueChanged.connect(self._on_offset_x_changed)
        xy_box.addWidget(self.spin_x)

        xy_box.addWidget(QLabel("Y:"))
        self.spin_y = QDoubleSpinBox()
        self.spin_y.setRange(-400.0, 400.0)
        self.spin_y.setSingleStep(2.0)
        self.spin_y.valueChanged.connect(self._on_offset_y_changed)
        xy_box.addWidget(self.spin_y)
        scale_layout.addLayout(xy_box)
        word_layout.addWidget(scale_group)

        self.time_group = QGroupBox("Keyframe Telemetry (ms)")
        time_layout = QVBoxLayout(self.time_group)
        time_layout.setSpacing(4)

        s_box = QHBoxLayout()
        s_box.addWidget(QLabel("Start (ms):"))
        self.spin_start = QSpinBox()
        self.spin_start.setRange(0, 3600000)
        self.spin_start.setSingleStep(25)
        self.spin_start.valueChanged.connect(self._on_time_changed)
        s_box.addWidget(self.spin_start)
        time_layout.addLayout(s_box)

        e_box = QHBoxLayout()
        e_box.addWidget(QLabel("Duration (ms):"))
        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(50, 60000)
        self.spin_duration.setSingleStep(25)
        self.spin_duration.valueChanged.connect(self._on_duration_changed)
        e_box.addWidget(self.spin_duration)
        time_layout.addLayout(e_box)
        word_layout.addWidget(self.time_group)

        trans_group = QGroupBox("Transition & Alpha Curve")
        trans_layout = QVBoxLayout(trans_group)
        trans_layout.setSpacing(4)

        fc_box = QHBoxLayout()
        fc_box.addWidget(QLabel("Fade (ms):"))
        self.spin_fade = QSpinBox()
        self.spin_fade.setRange(10, 1000)
        self.spin_fade.setSingleStep(20)
        self.spin_fade.valueChanged.connect(self._on_fade_changed)
        fc_box.addWidget(self.spin_fade)

        fc_box.addWidget(QLabel("Curve:"))
        self.combo_curve = QComboBox()
        self.combo_curve.addItems(["cubic", "linear"])
        self.combo_curve.currentTextChanged.connect(self._on_curve_changed)
        fc_box.addWidget(self.combo_curve)
        trans_layout.addLayout(fc_box)

        op_lbl_box = QHBoxLayout()
        op_lbl_box.addWidget(QLabel("Inactive Opacity:"))
        self.lbl_opacity = QLabel("0.00")
        self.lbl_opacity.setObjectName("accentValueLabel")
        op_lbl_box.addStretch()
        op_lbl_box.addWidget(self.lbl_opacity)
        trans_layout.addLayout(op_lbl_box)

        preset_box = QHBoxLayout()
        self.btn_preset_invisible = QPushButton("0% (Invisible)")
        self.btn_preset_invisible.clicked.connect(lambda: self._set_opacity_preset(0.0))
        preset_box.addWidget(self.btn_preset_invisible)

        self.btn_preset_dimmed = QPushButton("30% (Dimmed)")
        self.btn_preset_dimmed.clicked.connect(lambda: self._set_opacity_preset(0.30))
        preset_box.addWidget(self.btn_preset_dimmed)
        trans_layout.addLayout(preset_box)

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setValue(0)
        self.slider_opacity.valueChanged.connect(self._on_opacity_slider)
        trans_layout.addWidget(self.slider_opacity)

        self.btn_apply_opacity_all = QPushButton("Apply Inactive Opacity to All Words")
        self.btn_apply_opacity_all.clicked.connect(self._on_apply_opacity_all)
        trans_layout.addWidget(self.btn_apply_opacity_all)
        word_layout.addWidget(trans_group)

        btn_action_box = QHBoxLayout()
        self.btn_add_word = QPushButton("+ Add Word")
        self.btn_add_word.setObjectName("accentActionButton")
        self.btn_add_word.clicked.connect(self.add_word_requested.emit)
        btn_action_box.addWidget(self.btn_add_word)

        self.btn_delete_word = QPushButton("Delete Word")
        self.btn_delete_word.setObjectName("dangerButton")
        self.btn_delete_word.clicked.connect(self.delete_requested.emit)
        btn_action_box.addWidget(self.btn_delete_word)
        word_layout.addLayout(btn_action_box)

        layout.addWidget(self.word_container)

        stanza_group = QGroupBox("Stanza Operations")
        st_layout = QHBoxLayout(stanza_group)
        self.btn_new_stanza = QPushButton("+ Stanza")
        self.btn_new_stanza.clicked.connect(self.new_stanza_requested.emit)
        self.btn_del_stanza = QPushButton("Delete Stanza")
        self.btn_del_stanza.clicked.connect(self.delete_stanza_requested.emit)
        st_layout.addWidget(self.btn_new_stanza)
        st_layout.addWidget(self.btn_del_stanza)
        layout.addWidget(stanza_group)

        layout.addStretch()

    def _sync_global_controls(self) -> None:
        self._is_updating_ui = True
        try:
            self._populate_font_combos()
            idx_p = self.combo_preset.findData(self.project.default_layout_preset)
            if idx_p >= 0:
                self.combo_preset.setCurrentIndex(idx_p)

            cur_fam = self.project.base_font_family
            if cur_fam:
                idx_f = self.combo_global_font.findText(cur_fam)
                if idx_f >= 0:
                    self.combo_global_font.setCurrentIndex(idx_f)
                else:
                    self.combo_global_font.setEditText(cur_fam)

            idx_c = self.combo_casing.findData(self.project.text_casing)
            if idx_c >= 0:
                self.combo_casing.setCurrentIndex(idx_c)

            best_align_idx = 1
            best_diff = 999.0
            for i in range(self.combo_valign.count()):
                val = float(self.combo_valign.itemData(i))
                if abs(val - self.project.align_y) < best_diff:
                    best_diff = abs(val - self.project.align_y)
                    best_align_idx = i
            self.combo_valign.setCurrentIndex(best_align_idx)

            self.spin_letter_spacing.setValue(self.project.letter_spacing)
            self.spin_line_height.setValue(self.project.line_height_factor)
            self.spin_stroke_width.setValue(self.project.stroke_width)
            self.btn_stroke_color.setText(f"Stroke {self.project.stroke_color.upper()}")
        finally:
            self._is_updating_ui = False

    def set_selection(self, word_ids: Set[str], primary_id: Optional[str]) -> None:
        self.selected_word_ids = {
            wid for wid in word_ids if self.project.find_word_by_id(wid) is not None
        }
        if primary_id and primary_id in self.selected_word_ids:
            self.active_word_id = primary_id
        elif self.selected_word_ids:
            self.active_word_id = next(iter(self.selected_word_ids))
        else:
            self.active_word_id = None

        count = len(self.selected_word_ids)
        if count == 0 or not self.active_word_id:
            self.lbl_selection_telemetry.setText("[NO WORD SELECTED]")
            self.word_container.setEnabled(False)
            self.btn_delete_word.setText("Delete Word")
            return

        res = self.project.find_word_by_id(self.active_word_id)
        if not res:
            self.lbl_selection_telemetry.setText("[NO WORD SELECTED]")
            self.word_container.setEnabled(False)
            return

        stanza, word = res
        is_batch = count > 1

        if is_batch:
            self.lbl_selection_telemetry.setText(f"[BATCH EDITING: {count} WORDS SELECTED]")
            self.btn_delete_word.setText(f"Delete Words ({count})")
        else:
            self.lbl_selection_telemetry.setText(f"[ACTIVE WORD: {word.id}]")
            self.btn_delete_word.setText("Delete Word")

        self._is_updating_ui = True
        try:
            self.word_container.setEnabled(True)
            self.edit_text.setEnabled(not is_batch)
            self.time_group.setEnabled(not is_batch)

            idx_p = self.combo_preset.findData(stanza.layout_preset)
            if idx_p >= 0:
                self.combo_preset.setCurrentIndex(idx_p)

            if is_batch:
                self.edit_text.setText(f"[{count} WORDS SELECTED]")
            else:
                self.edit_text.setText(word.text)

            self.combo_line.setCurrentIndex(min(5, max(0, word.line_index)))

            # Sync Word Font
            self.combo_word_font.blockSignals(True)
            if is_batch:
                sel_words = [w for _, w in self._get_selected_words()]
                fams = {w.font_family for w in sel_words}
                if len(fams) == 1:
                    fam_val = next(iter(fams))
                    if fam_val:
                        idx_f = self.combo_word_font.findText(fam_val)
                        if idx_f >= 0:
                            self.combo_word_font.setCurrentIndex(idx_f)
                        else:
                            self.combo_word_font.setEditText(fam_val)
                    else:
                        self.combo_word_font.setCurrentIndex(0)
                else:
                    self.combo_word_font.setEditText("[Multiple Fonts]")
            else:
                if word.font_family:
                    idx_f = self.combo_word_font.findText(word.font_family)
                    if idx_f >= 0:
                        self.combo_word_font.setCurrentIndex(idx_f)
                    else:
                        self.combo_word_font.setEditText(word.font_family)
                else:
                    self.combo_word_font.setCurrentIndex(0)
            self.combo_word_font.blockSignals(False)

            self._sync_letter_combo_for_word(word, is_batch)

            self.slider_scale.setValue(int(round(word.scale_multiplier * 10.0)))
            self.lbl_scale.setText(f"{word.scale_multiplier:.1f}x")
            self.spin_x.setValue(word.offset_x)
            self.spin_y.setValue(word.offset_y)
            self.spin_start.setValue(word.start_ms)
            self.spin_duration.setValue(max(50, word.end_ms - word.start_ms))
            self.spin_fade.setValue(word.fade_in_ms)

            curve_name = str(word.fade_curve)
            if curve_name not in ("cubic", "linear"):
                curve_name = "cubic"
                word.fade_curve = "cubic"
            self.combo_curve.setCurrentText(curve_name)

            self.slider_opacity.setValue(int(round(word.inactive_opacity * 100.0)))
            self.lbl_opacity.setText(f"{word.inactive_opacity:.2f}")
        finally:
            self._is_updating_ui = False

    def _get_selected_words(self) -> List[Tuple[Stanza, WordKeyframe]]:
        results: List[Tuple[Stanza, WordKeyframe]] = []
        for s in self.project.stanzas:
            for w in s.words:
                if w.id in self.selected_word_ids:
                    results.append((s, w))
        return results

    def _commit_property_across_selection(self, prop_name: str, new_val: Any) -> None:
        changes: List[Tuple[str, Any, Any]] = []
        for _, w in self._get_selected_words():
            old_val = getattr(w, prop_name)
            if isinstance(new_val, float):
                if abs(float(old_val) - new_val) > 1e-4:
                    changes.append((w.id, old_val, new_val))
            elif isinstance(new_val, dict) or isinstance(old_val, dict):
                if old_val != new_val:
                    changes.append((w.id, copy.deepcopy(old_val), copy.deepcopy(new_val)))
            else:
                if old_val != new_val:
                    changes.append((w.id, old_val, new_val))
        if changes:
            self.batch_property_committed.emit(prop_name, changes)

    def _on_preset_changed(self, idx: int) -> None:
        if self._is_updating_ui:
            return
        preset = str(self.combo_preset.currentData())
        self.project.default_layout_preset = preset
        selected_pairs = self._get_selected_words()
        if selected_pairs:
            for stanza, _ in selected_pairs:
                stanza.layout_preset = preset
        else:
            for s in self.project.stanzas:
                s.layout_preset = preset
        self.word_updated.emit()

    def _on_casing_changed(self, idx: int) -> None:
        if self._is_updating_ui:
            return
        self.project.text_casing = str(self.combo_casing.currentData())
        self.word_updated.emit()

    def _on_valign_changed(self, idx: int) -> None:
        if self._is_updating_ui:
            return
        self.project.align_y = float(self.combo_valign.currentData())
        self.word_updated.emit()

    def _on_letter_spacing_changed(self, val: float) -> None:
        if self._is_updating_ui:
            return
        self.project.letter_spacing = val
        self.word_updated.emit()

    def _on_line_height_changed(self, val: float) -> None:
        if self._is_updating_ui:
            return
        self.project.line_height_factor = val
        self.word_updated.emit()

    def _on_stroke_width_changed(self, val: float) -> None:
        if self._is_updating_ui:
            return
        self.project.stroke_width = val
        self.word_updated.emit()

    def _on_pick_stroke_color(self) -> None:
        initial = QColor(self.project.stroke_color)
        chosen = QColorDialog.getColor(initial, self, "Select Stroke Color")
        if chosen.isValid():
            self.project.stroke_color = chosen.name()
            self.btn_stroke_color.setText(f"Stroke {self.project.stroke_color.upper()}")
            self.word_updated.emit()

    def _on_text_edited(self, text: str) -> None:
        if self._is_updating_ui or len(self.selected_word_ids) != 1:
            return
        self._commit_property_across_selection("text", text)
        if self.active_word_id:
            res = self.project.find_word_by_id(self.active_word_id)
            if res:
                _, word = res
                self._sync_letter_combo_for_word(word, False)

    def _on_line_changed(self, idx: int) -> None:
        if self._is_updating_ui:
            return
        self._commit_property_across_selection("line_index", idx)

    def _on_scale_slider(self, val: int) -> None:
        if self._is_updating_ui:
            return
        scale = val / 10.0
        self.lbl_scale.setText(f"{scale:.1f}x")
        self._commit_property_across_selection("scale_multiplier", scale)

    def _on_offset_x_changed(self, val: float) -> None:
        if self._is_updating_ui:
            return
        self._commit_property_across_selection("offset_x", val)

    def _on_offset_y_changed(self, val: float) -> None:
        if self._is_updating_ui:
            return
        self._commit_property_across_selection("offset_y", val)

    def _on_time_changed(self, val: int) -> None:
        if self._is_updating_ui or len(self.selected_word_ids) != 1 or not self.active_word_id:
            return
        res = self.project.find_word_by_id(self.active_word_id)
        if res:
            _, w = res
            dur = max(50, w.end_ms - w.start_ms)
            old_s, old_e = w.start_ms, w.end_ms
            new_s, new_e = val, val + dur
            if old_s != new_s or old_e != new_e:
                self.batch_timing_committed.emit([(w.id, old_s, old_e, new_s, new_e)])

    def _on_duration_changed(self, dur: int) -> None:
        if self._is_updating_ui or len(self.selected_word_ids) != 1 or not self.active_word_id:
            return
        res = self.project.find_word_by_id(self.active_word_id)
        if res:
            _, w = res
            old_e = w.end_ms
            new_e = w.start_ms + dur
            if old_e != new_e:
                self._commit_property_across_selection("end_ms", new_e)

    def _on_fade_changed(self, val: int) -> None:
        if self._is_updating_ui:
            return
        self._commit_property_across_selection("fade_in_ms", val)

    def _on_curve_changed(self, text: str) -> None:
        if self._is_updating_ui:
            return
        curve_str = str(text) if str(text) in ("cubic", "linear") else "cubic"
        self._commit_property_across_selection("fade_curve", curve_str)

    def _on_opacity_slider(self, val: int) -> None:
        if self._is_updating_ui:
            return
        ratio = val / 100.0
        self.lbl_opacity.setText(f"{ratio:.2f}")
        self._commit_property_across_selection("inactive_opacity", ratio)

    def _set_opacity_preset(self, val: float) -> None:
        self.slider_opacity.setValue(int(round(val * 100.0)))

    def _on_apply_opacity_all(self) -> None:
        if not self.active_word_id:
            return
        res = self.project.find_word_by_id(self.active_word_id)
        if not res:
            return
        _, w = res
        target_op = w.inactive_opacity
        self.project.global_inactive_opacity = target_op
        changes: List[Tuple[str, Any, Any]] = []
        for s in self.project.stanzas:
            for word in s.words:
                if abs(word.inactive_opacity - target_op) > 1e-4:
                    changes.append((word.id, word.inactive_opacity, target_op))
        if changes:
            self.batch_property_committed.emit("inactive_opacity", changes)

    def _populate_font_combos(self) -> None:
        avail_families = FontManager.get_available_font_families()
        cur_global = self.project.base_font_family or "Inter"

        self.combo_global_font.blockSignals(True)
        cur_g_text = self.combo_global_font.currentText() or cur_global
        self.combo_global_font.clear()
        for f in avail_families:
            self.combo_global_font.addItem(f)
        idx_g = self.combo_global_font.findText(cur_g_text)
        if idx_g >= 0:
            self.combo_global_font.setCurrentIndex(idx_g)
        else:
            self.combo_global_font.setEditText(cur_g_text)
        self.combo_global_font.blockSignals(False)

        self.combo_word_font.blockSignals(True)
        cur_w_text = self.combo_word_font.currentText()
        self.combo_word_font.clear()
        self.combo_word_font.addItem("(Inherit Global Font)", "")
        for f in avail_families:
            self.combo_word_font.addItem(f, f)
        idx_w = self.combo_word_font.findText(cur_w_text)
        if idx_w >= 0:
            self.combo_word_font.setCurrentIndex(idx_w)
        self.combo_word_font.blockSignals(False)

        self.combo_letter_font.blockSignals(True)
        cur_l_text = self.combo_letter_font.currentText()
        self.combo_letter_font.clear()
        self.combo_letter_font.addItem("(Inherit Word Font)", "")
        for f in avail_families:
            self.combo_letter_font.addItem(f, f)
        idx_l = self.combo_letter_font.findText(cur_l_text)
        if idx_l >= 0:
            self.combo_letter_font.setCurrentIndex(idx_l)
        self.combo_letter_font.blockSignals(False)

    def _sync_letter_combo_for_word(self, word: WordKeyframe, is_batch: bool) -> None:
        prev_idx = self.combo_letter_idx.currentIndex()
        if prev_idx < 0:
            prev_idx = 0

        self.combo_letter_idx.blockSignals(True)
        self.combo_letter_idx.clear()

        if is_batch:
            self.combo_letter_idx.addItem("[Disabled in multi-select]", -1)
            self.combo_letter_idx.setEnabled(False)
            self.combo_letter_font.setEnabled(False)
            self.btn_load_letter_font.setEnabled(False)
            self.btn_reset_letter.setEnabled(False)
            self.btn_clear_all_letters.setEnabled(False)
            self.combo_letter_idx.blockSignals(False)
            return

        self.combo_letter_idx.setEnabled(True)
        text_clean = word.text.strip()
        if not text_clean:
            self.combo_letter_idx.addItem("(No letters)", -1)
            self.combo_letter_font.setEnabled(False)
            self.btn_load_letter_font.setEnabled(False)
            self.btn_reset_letter.setEnabled(False)
            self.btn_clear_all_letters.setEnabled(False)
            self.combo_letter_idx.blockSignals(False)
            return

        lf = word.letter_fonts or {}
        for i, ch in enumerate(text_clean):
            ovr = lf.get(str(i))
            label = f"Letter {i + 1}: '{ch}'"
            if ovr:
                label += f"  [{ovr}]"
            self.combo_letter_idx.addItem(label, i)

        target_idx = min(prev_idx, len(text_clean) - 1)
        self.combo_letter_idx.setCurrentIndex(target_idx)
        self.combo_letter_idx.blockSignals(False)
        self._on_letter_idx_changed(target_idx)

    def _on_letter_idx_changed(self, combo_idx: int) -> None:
        if self._is_updating_ui or not self.active_word_id:
            return
        res = self.project.find_word_by_id(self.active_word_id)
        if not res:
            return
        _, word = res

        char_idx = self.combo_letter_idx.currentData()
        if char_idx is None or char_idx < 0:
            self.combo_letter_font.setEnabled(False)
            self.btn_load_letter_font.setEnabled(False)
            self.btn_reset_letter.setEnabled(False)
            self.btn_clear_all_letters.setEnabled(False)
            return

        self.combo_letter_font.setEnabled(True)
        self.btn_load_letter_font.setEnabled(True)
        self.btn_reset_letter.setEnabled(True)
        self.btn_clear_all_letters.setEnabled(bool(word.letter_fonts))

        lf = word.letter_fonts or {}
        ovr_font = lf.get(str(char_idx))

        self.combo_letter_font.blockSignals(True)
        if ovr_font:
            idx = self.combo_letter_font.findText(ovr_font)
            if idx >= 0:
                self.combo_letter_font.setCurrentIndex(idx)
            else:
                self.combo_letter_font.setEditText(ovr_font)
        else:
            self.combo_letter_font.setCurrentIndex(0)  # "(Inherit Word Font)"
        self.combo_letter_font.blockSignals(False)

    def _on_letter_font_changed(self, text: str) -> None:
        if self._is_updating_ui or not self.active_word_id:
            return
        res = self.project.find_word_by_id(self.active_word_id)
        if not res:
            return
        _, word = res

        char_idx = self.combo_letter_idx.currentData()
        if char_idx is None or char_idx < 0:
            return

        font_val = text.strip()
        if font_val in ("(Inherit Word Font)", ""):
            font_val = ""

        new_lf = dict(word.letter_fonts) if word.letter_fonts else {}
        if font_val:
            new_lf[str(char_idx)] = font_val
        else:
            new_lf.pop(str(char_idx), None)

        new_lf_val = new_lf if new_lf else None
        self._commit_property_across_selection("letter_fonts", new_lf_val)
        self._refresh_letter_idx_label(char_idx, font_val)
        self.btn_clear_all_letters.setEnabled(bool(new_lf_val))
        self.word_updated.emit()

    def _refresh_letter_idx_label(self, char_idx: int, font_val: str) -> None:
        if not self.active_word_id:
            return
        res = self.project.find_word_by_id(self.active_word_id)
        if not res:
            return
        _, word = res
        text_clean = word.text.strip()
        if 0 <= char_idx < len(text_clean):
            ch = text_clean[char_idx]
            label = f"Letter {char_idx + 1}: '{ch}'"
            if font_val:
                label += f"  [{font_val}]"
            self.combo_letter_idx.blockSignals(True)
            self.combo_letter_idx.setItemText(char_idx, label)
            self.combo_letter_idx.blockSignals(False)

    def _on_reset_selected_letter_font(self) -> None:
        self.combo_letter_font.setCurrentIndex(0)

    def _on_clear_all_letter_fonts(self) -> None:
        if self._is_updating_ui or not self.active_word_id:
            return
        res = self.project.find_word_by_id(self.active_word_id)
        if not res:
            return
        _, word = res
        if not word.letter_fonts:
            return
        self._commit_property_across_selection("letter_fonts", None)
        self._sync_letter_combo_for_word(word, False)
        self.combo_letter_font.blockSignals(True)
        self.combo_letter_font.setCurrentIndex(0)
        self.combo_letter_font.blockSignals(False)
        self.btn_clear_all_letters.setEnabled(False)
        self.word_updated.emit()

    def _on_global_font_changed(self, text: str) -> None:
        if self._is_updating_ui:
            return
        val = text.strip()
        if val:
            self.project.base_font_family = val
            self.word_updated.emit()

    def _on_word_font_changed(self, text: str) -> None:
        if self._is_updating_ui:
            return
        val = text.strip()
        if val in ("(Inherit Global Font)", "[Multiple Fonts]", ""):
            val = None
        self._commit_property_across_selection("font_family", val)
        self.word_updated.emit()

    def _on_load_global_font_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Global Font File",
            "",
            "Font Files (*.ttf *.otf *.woff *.woff2 *.ttc);;All Files (*.*)",
        )
        if path and os.path.isfile(path):
            family = FontManager.load_font_file(path)
            if family:
                if path not in self.project.custom_font_paths:
                    self.project.custom_font_paths.append(path)
                self.project.base_font_path = path
                self.project.base_font_family = family
                self._populate_font_combos()
                idx = self.combo_global_font.findText(family)
                if idx >= 0:
                    self.combo_global_font.setCurrentIndex(idx)
                else:
                    self.combo_global_font.setEditText(family)
                self.word_updated.emit()
            else:
                QMessageBox.warning(self, "Font Error", f"Could not load font from:\n{path}")

    def _on_load_word_font_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Word Font File",
            "",
            "Font Files (*.ttf *.otf *.woff *.woff2 *.ttc);;All Files (*.*)",
        )
        if path and os.path.isfile(path):
            family = FontManager.load_font_file(path)
            if family:
                if path not in self.project.custom_font_paths:
                    self.project.custom_font_paths.append(path)
                self._populate_font_combos()
                idx = self.combo_word_font.findText(family)
                if idx >= 0:
                    self.combo_word_font.setCurrentIndex(idx)
                else:
                    self.combo_word_font.setEditText(family)
                self._commit_property_across_selection("font_family", family)
                self.word_updated.emit()
            else:
                QMessageBox.warning(self, "Font Error", f"Could not load font from:\n{path}")

    def _on_load_letter_font_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Letter Font File",
            "",
            "Font Files (*.ttf *.otf *.woff *.woff2 *.ttc);;All Files (*.*)",
        )
        if path and os.path.isfile(path):
            family = FontManager.load_font_file(path)
            if family:
                if path not in self.project.custom_font_paths:
                    self.project.custom_font_paths.append(path)
                self._populate_font_combos()
                idx = self.combo_letter_font.findText(family)
                if idx >= 0:
                    self.combo_letter_font.setCurrentIndex(idx)
                else:
                    self.combo_letter_font.setEditText(family)
                self._on_letter_font_changed(family)
            else:
                QMessageBox.warning(self, "Font Error", f"Could not load font from:\n{path}")


# ==============================================================================
# 8. CLOCK-SYNCED AUDIO TRANSPORT
# ==============================================================================

class AudioTransport(QWidget):
    """
    Clock-synchronized transport controller locking playback and timeline scrubbing
    to QtMultimedia and high-resolution performance counter clocks within +/-16ms tolerance.
    """
    time_changed = Signal(int)
    play_state_changed = Signal(bool)
    duration_changed = Signal(int)

    def __init__(self, project: LyricProject, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.project = project
        self.current_time_ms = 0
        self.is_playing = False
        self.loop_enabled = True

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.durationChanged.connect(self._on_player_duration_changed)
        self.player.positionChanged.connect(self._on_player_position_changed)

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._on_tick)

        self._clock_start_time = 0.0
        self._clock_start_ms = 0
        self._last_media_pos = 0.0
        self._last_media_perf = 0.0

        self.setObjectName("dockPanel")
        self._setup_ui()

    def set_project(self, project: LyricProject) -> None:
        self.project = project
        self.set_duration(project.duration_ms)

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        self.btn_play = QPushButton("PLAY")
        self.btn_play.setObjectName("primaryButton")
        self.btn_play.setFixedWidth(72)
        self.btn_play.clicked.connect(self.toggle_play)
        layout.addWidget(self.btn_play)

        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setFixedWidth(64)
        self.btn_stop.clicked.connect(self.stop)
        layout.addWidget(self.btn_stop)

        self.chk_loop = QCheckBox("Loop")
        self.chk_loop.setChecked(True)
        self.chk_loop.stateChanged.connect(lambda s: setattr(self, "loop_enabled", bool(s)))
        layout.addWidget(self.chk_loop)

        layout.addSpacing(8)

        self.lbl_timecode = QLabel("00:00.000 / 00:10.000")
        self.lbl_timecode.setObjectName("timecodeLabel")
        layout.addWidget(self.lbl_timecode)

        layout.addSpacing(8)

        layout.addWidget(QLabel("Duration:"))
        self.spin_duration = QDoubleSpinBox()
        self.spin_duration.setRange(1.0, 3600.0)
        self.spin_duration.setSingleStep(1.0)
        self.spin_duration.setSuffix(" s")
        self.spin_duration.setValue(self.project.duration_ms / 1000.0)
        self.spin_duration.valueChanged.connect(self._on_duration_spin_changed)
        layout.addWidget(self.spin_duration)

        layout.addStretch()

    def set_duration(self, duration_ms: int) -> None:
        self.project.duration_ms = max(1000, duration_ms)
        self.spin_duration.blockSignals(True)
        self.spin_duration.setValue(self.project.duration_ms / 1000.0)
        self.spin_duration.blockSignals(False)
        self._update_timecode_display()
        self.duration_changed.emit(self.project.duration_ms)

    def _on_duration_spin_changed(self, val: float) -> None:
        self.set_duration(int(round(val * 1000.0)))

    def _on_player_duration_changed(self, duration_ms: int) -> None:
        if duration_ms > 0:
            self.set_duration(duration_ms)

    def _on_player_position_changed(self, pos_ms: int) -> None:
        self._last_media_pos = float(pos_ms)
        self._last_media_perf = time.perf_counter()

    def load_audio(self, filepath: str) -> None:
        if os.path.exists(filepath):
            self.project.audio_file = filepath
            self.player.setSource(QUrl.fromLocalFile(filepath))

    def toggle_play(self) -> None:
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def play(self) -> None:
        if self.is_playing:
            return

        if self.current_time_ms >= self.project.duration_ms:
            self.seek(0)

        self.is_playing = True
        self.btn_play.setText("PAUSE")
        self.btn_play.setObjectName("playButtonActive")
        self.btn_play.setStyle(self.btn_play.style())

        now = time.perf_counter()
        self._clock_start_time = now
        self._clock_start_ms = self.current_time_ms
        self._last_media_pos = float(self.current_time_ms)
        self._last_media_perf = now

        if self.project.audio_file and os.path.exists(self.project.audio_file):
            self.player.setPosition(self.current_time_ms)
            self.player.play()

        self.timer.start()
        self.play_state_changed.emit(True)

    def pause(self) -> None:
        if not self.is_playing:
            return

        self.is_playing = False
        self.btn_play.setText("PLAY")
        self.btn_play.setObjectName("primaryButton")
        self.btn_play.setStyle(self.btn_play.style())

        if self.project.audio_file and os.path.exists(self.project.audio_file):
            self.player.pause()

        self.timer.stop()
        self.play_state_changed.emit(False)

    def stop(self) -> None:
        self.pause()
        self.seek(0)

    def seek(self, time_ms: int) -> None:
        self.current_time_ms = max(0, min(self.project.duration_ms, time_ms))
        now = time.perf_counter()
        self._clock_start_time = now
        self._clock_start_ms = self.current_time_ms
        self._last_media_pos = float(self.current_time_ms)
        self._last_media_perf = now

        if self.project.audio_file and os.path.exists(self.project.audio_file):
            self.player.setPosition(self.current_time_ms)

        self._update_timecode_display()
        self.time_changed.emit(self.current_time_ms)

    def _on_tick(self) -> None:
        if not self.is_playing:
            return

        now = time.perf_counter()
        has_audio = (
            self.project.audio_file
            and os.path.exists(self.project.audio_file)
            and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        )

        if has_audio:
            elapsed = (now - self._last_media_perf) * 1000.0
            calc_ms = int(round(self._last_media_pos + elapsed))

            pos_actual = self.player.position()
            drift = abs(calc_ms - pos_actual)
            if drift > 16:
                self._last_media_pos = float(pos_actual)
                self._last_media_perf = now
                calc_ms = pos_actual

            self.current_time_ms = calc_ms
        else:
            elapsed = (now - self._clock_start_time) * 1000.0
            self.current_time_ms = int(round(self._clock_start_ms + elapsed))

        if self.current_time_ms >= self.project.duration_ms:
            if self.loop_enabled:
                self.seek(0)
                if has_audio:
                    self.player.play()
            else:
                self.pause()
                self.seek(self.project.duration_ms)
                return

        self._update_timecode_display()
        self.time_changed.emit(self.current_time_ms)

    def _update_timecode_display(self) -> None:
        c_sec = self.current_time_ms / 1000.0
        d_sec = self.project.duration_ms / 1000.0
        c_m, c_s = divmod(c_sec, 60.0)
        d_m, d_s = divmod(d_sec, 60.0)
        txt = f"{int(c_m):02d}:{c_s:06.3f} / {int(d_m):02d}:{d_s:06.3f}"
        self.lbl_timecode.setText(txt)


# ==============================================================================
# 9. HEADLESS SUBPROCESS FFMPEG RGBA STREAM EXPORTER
# ==============================================================================

class FFmpegExportWorker(QThread):
    """
    Asynchronous rendering worker streaming raw RGBA byte frames directly into
    an FFmpeg subprocess standard input pipe.
    Features persistent byte buffer references, per-frame proc.poll() checks,
    and exception-hardened pipe I/O.
    """
    progress = Signal(int, int, float)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        project: LyricProject,
        output_path: str,
        profile: str = "prores",
        fps: int = 60,
        include_audio: bool = True,
        include_background: bool = True,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.project = project
        self.output_path = output_path
        self.profile = profile
        self.fps = fps
        self.include_audio = include_audio
        self.include_background = include_background
        self._is_cancelled = False
        self.proc: Optional[subprocess.Popen] = None

    def cancel(self) -> None:
        self._is_cancelled = True
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass

    def run(self) -> None:
        if not shutil.which("ffmpeg"):
            self.failed.emit("FFmpeg executable not found in system PATH.\nPlease install FFmpeg to export video.")
            return

        width = self.project.resolution_width
        height = self.project.resolution_height
        duration_sec = self.project.duration_ms / 1000.0
        total_frames = max(1, int(round(duration_sec * self.fps)))

        has_bg = (
            self.include_background
            and bool(self.project.bg_media_path)
            and os.path.exists(self.project.bg_media_path)
        )
        bg_is_image = False
        if has_bg:
            ext = os.path.splitext(self.project.bg_media_path)[1].lower()
            bg_is_image = ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp")

        has_project_audio = (
            self.include_audio
            and bool(self.project.audio_file)
            and os.path.exists(self.project.audio_file)
        )

        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-pix_fmt", "rgba",
            "-s", f"{width}x{height}",
            "-r", str(self.fps),
            "-i", "-",
        ]

        if has_bg:
            if bg_is_image:
                ffmpeg_cmd.extend(["-loop", "1", "-i", self.project.bg_media_path])
            else:
                ffmpeg_cmd.extend(["-stream_loop", "-1", "-i", self.project.bg_media_path])

        if has_project_audio:
            ffmpeg_cmd.extend(["-i", self.project.audio_file])

        if has_bg:
            dim_val = max(0.0, min(1.0, float(self.project.bg_dim_opacity)))
            dim_filter = f",drawbox=t=fill:color=black@{dim_val:.2f}" if dim_val > 0.001 else ""
            filter_graph = (
                f"[1:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},setsar=1,fps={self.fps}{dim_filter}[bg];"
                f"[bg][0:v]overlay=0:0:shortest=1[outv]"
            )
            ffmpeg_cmd.extend(["-filter_complex", filter_graph, "-map", "[outv]"])
        else:
            ffmpeg_cmd.extend(["-map", "0:v"])

        if self.profile == "prores":
            ffmpeg_cmd.extend([
                "-c:v", "prores_ks",
                "-profile:v", "4",
                "-pix_fmt", "yuva444p10le",
                "-vendor", "apl0",
            ])
        elif self.profile == "webm":
            ffmpeg_cmd.extend([
                "-c:v", "libvpx-vp9",
                "-pix_fmt", "yuva420p",
                "-b:v", "0",
                "-crf", "18",
            ])
        else:
            ffmpeg_cmd.extend([
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "16",
                "-preset", "slow",
            ])

        ffmpeg_cmd.extend(["-r", str(self.fps)])

        audio_codec = "libopus" if self.profile == "webm" else "aac"
        audio_bitrate = "192k" if self.profile == "webm" else "320k"

        if has_project_audio:
            audio_idx = 2 if has_bg else 1
            ffmpeg_cmd.extend([
                "-map", f"{audio_idx}:a:0",
                "-c:a", audio_codec,
                "-b:a", audio_bitrate,
                "-shortest",
            ])
        elif has_bg and self.include_audio:
            ffmpeg_cmd.extend([
                "-map", "1:a?",
                "-c:a", audio_codec,
                "-b:a", audio_bitrate,
                "-shortest",
            ])

        ffmpeg_cmd.append(self.output_path)

        img_buffer = QImage(width, height, QImage.Format.Format_RGBA8888)
        layout_engine = KineticLayoutEngine(self.project)

        stderr_file = tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8", errors="replace", delete=False)
        stderr_path = stderr_file.name

        flags = get_subprocess_creation_flags()

        try:
            self.proc = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=stderr_file,
                **flags
            )
        except Exception as e:
            stderr_file.close()
            try:
                os.remove(stderr_path)
            except OSError:
                pass
            self.failed.emit(f"Failed to spawn FFmpeg: {str(e)}")
            return

        expected_line_bytes = width * 4
        persistent_frame_ref: Optional[bytes] = None

        try:
            for frame_idx in range(total_frames):
                if self._is_cancelled:
                    if self.proc.poll() is None:
                        self.proc.terminate()
                    self.failed.emit("Export cancelled by user.")
                    return

                if self.proc.poll() is not None:
                    break

                time_ms = (frame_idx / float(self.fps)) * 1000.0

                if has_bg or self.profile in ("prores", "webm"):
                    img_buffer.fill(QColor(0, 0, 0, 0))
                else:
                    img_buffer.fill(QColor(0, 0, 0, 255))

                painter = QPainter(img_buffer)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
                layout_engine.render_frame(painter, time_ms)
                painter.end()

                ptr = img_buffer.constBits()
                mv = memoryview(ptr)
                bytes_per_line = img_buffer.bytesPerLine()

                if bytes_per_line == expected_line_bytes:
                    persistent_frame_ref = bytes(mv[: height * expected_line_bytes])
                else:
                    persistent_frame_ref = b"".join(
                        bytes(mv[y * bytes_per_line : y * bytes_per_line + expected_line_bytes])
                        for y in range(height)
                    )

                try:
                    if self.proc.stdin is not None:
                        self.proc.stdin.write(persistent_frame_ref)
                except (BrokenPipeError, OSError) as pipe_err:
                    stderr_file.flush()
                    with open(stderr_path, "r", encoding="utf-8", errors="replace") as ef:
                        err_log = ef.read()
                    self.failed.emit(f"FFmpeg stream interrupted ({pipe_err}):\n{err_log[-1200:]}")
                    return

                pct = (frame_idx + 1) / float(total_frames) * 100.0
                self.progress.emit(frame_idx + 1, total_frames, pct)

            if self.proc.stdin is not None:
                try:
                    self.proc.stdin.flush()
                    self.proc.stdin.close()
                except (BrokenPipeError, OSError):
                    pass

            self.proc.wait(timeout=30)
            stderr_file.close()

            if self.proc.returncode != 0:
                with open(stderr_path, "r", encoding="utf-8", errors="replace") as ef:
                    err_msg = ef.read()
                self.failed.emit(f"FFmpeg error (code {self.proc.returncode}):\n{err_msg[-1200:]}")
            else:
                self.completed.emit(self.output_path)

        except Exception as ex:
            if self.proc and self.proc.poll() is None:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.failed.emit(f"Export execution failure: {str(ex)}")
        finally:
            persistent_frame_ref = None
            try:
                stderr_file.close()
            except Exception:
                pass
            if os.path.exists(stderr_path):
                try:
                    os.remove(stderr_path)
                except OSError:
                    pass


class ExportDialog(QDialog):
    """Configuration dialog for executing headless FFmpeg exports."""

    def __init__(self, project: LyricProject, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Export Kinetic Lyrics Video")
        self.setMinimumSize(480, 320)
        self._worker: Optional[FFmpegExportWorker] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        form_group = QGroupBox("Video Encoding Profile")
        form_layout = QVBoxLayout(form_group)
        form_layout.setSpacing(6)

        self.combo_profile = QComboBox()
        self.combo_profile.addItem("Apple ProRes 4444 (.mov) - Transparent Alpha", "prores")
        self.combo_profile.addItem("WebM VP9 (.webm) - Transparent Alpha", "webm")
        self.combo_profile.addItem("H.264 MP4 (.mp4) - Solid Black Background", "mp4")
        self.combo_profile.currentIndexChanged.connect(self._update_default_extension)
        form_layout.addWidget(self.combo_profile)

        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("Framerate:"))
        self.combo_fps = QComboBox()
        self.combo_fps.setEditable(True)
        self.combo_fps.addItems([
            "24 FPS", "25 FPS", "30 FPS", "48 FPS", "50 FPS",
            "60 FPS", "90 FPS", "120 FPS", "144 FPS", "240 FPS"
        ])
        self.combo_fps.setCurrentText(f"{self.project.fps} FPS" if f"{self.project.fps} FPS" in [
            "24 FPS", "25 FPS", "30 FPS", "48 FPS", "50 FPS", "60 FPS", "90 FPS", "120 FPS", "144 FPS", "240 FPS"
        ] else f"{max(1, min(240, self.project.fps))} FPS")
        fps_layout.addWidget(self.combo_fps)
        form_layout.addLayout(fps_layout)

        self.chk_bg = QCheckBox("Include Background Media (if loaded)")
        has_bg_file = bool(self.project.bg_media_path and os.path.exists(self.project.bg_media_path))
        self.chk_bg.setChecked(has_bg_file)
        self.chk_bg.setEnabled(has_bg_file)
        form_layout.addWidget(self.chk_bg)

        self.chk_audio = QCheckBox("Mux Audio Track (if loaded)")
        self.chk_audio.setChecked(True)
        form_layout.addWidget(self.chk_audio)

        layout.addWidget(form_group)

        path_box = QHBoxLayout()
        self.edit_path = QLineEdit()
        self.edit_path.setText(os.path.abspath("instagram_lyrics_prores.mov"))
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self._on_browse)
        path_box.addWidget(self.edit_path)
        path_box.addWidget(self.btn_browse)
        layout.addLayout(path_box)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Ready to export.")
        self.lbl_status.setObjectName("mutedLabel")
        layout.addWidget(self.lbl_status)

        btn_box = QHBoxLayout()
        self.btn_start = QPushButton("Start Render")
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.clicked.connect(self._on_start_export)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self._on_cancel)
        btn_box.addStretch()
        btn_box.addWidget(self.btn_start)
        btn_box.addWidget(self.btn_cancel)
        layout.addLayout(btn_box)

    def _update_default_extension(self) -> None:
        profile = self.combo_profile.currentData()
        current = self.edit_path.text()
        base, _ = os.path.splitext(current)
        if profile == "prores":
            self.edit_path.setText(f"{base}.mov")
        elif profile == "webm":
            self.edit_path.setText(f"{base}.webm")
        elif profile == "mp4":
            self.edit_path.setText(f"{base}.mp4")

    def _on_browse(self) -> None:
        profile = self.combo_profile.currentData()
        ext_map = {"prores": "QuickTime (*.mov)", "webm": "WebM Video (*.webm)", "mp4": "MP4 Video (*.mp4)"}
        path, _ = QFileDialog.getSaveFileName(self, "Save Video", self.edit_path.text(), ext_map.get(profile, "All Files (*)"))
        if path:
            self.edit_path.setText(path)

    def _on_start_export(self) -> None:
        target_path = self.edit_path.text().strip()
        if not target_path:
            QMessageBox.warning(self, "Error", "Please specify an output file path.")
            return

        profile = self.combo_profile.currentData()
        fps_text = self.combo_fps.currentText().strip()
        fps_match = re.search(r"\d+", fps_text)
        if fps_match:
            fps = max(1, min(240, int(fps_match.group(0))))
        else:
            fps = 60
        include_audio = self.chk_audio.isChecked()
        include_bg = self.chk_bg.isChecked()

        self.btn_start.setEnabled(False)
        self.combo_profile.setEnabled(False)
        self.combo_fps.setEnabled(False)
        self.chk_bg.setEnabled(False)
        self.chk_audio.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Streaming RGBA frames to FFmpeg...")

        self._worker = FFmpegExportWorker(
            project=self.project,
            output_path=target_path,
            profile=profile,
            fps=fps,
            include_audio=include_audio,
            include_background=include_bg,
            parent=self,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.completed.connect(self._on_completed)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, frame: int, total: int, pct: float) -> None:
        self.progress_bar.setValue(int(round(pct)))
        self.lbl_status.setText(f"Encoding frame {frame}/{total} ({pct:.1f}%)...")

    def _on_completed(self, path: str) -> None:
        self.progress_bar.setValue(100)
        self.lbl_status.setText("Export completed.")
        QMessageBox.information(self, "Success", f"Video exported to:\n{path}")
        self.accept()

    def _on_failed(self, err: str) -> None:
        self.btn_start.setEnabled(True)
        self.combo_profile.setEnabled(True)
        self.combo_fps.setEnabled(True)
        self.chk_bg.setEnabled(bool(self.project.bg_media_path and os.path.exists(self.project.bg_media_path)))
        self.chk_audio.setEnabled(True)
        self.lbl_status.setText("Export failed.")
        QMessageBox.critical(self, "Export Error", err)

    def _on_cancel(self) -> None:
        self._cleanup_worker()
        self.reject()

    def closeEvent(self, event) -> None:
        self._cleanup_worker()
        event.accept()

    def _cleanup_worker(self) -> None:
        if self._worker and self._worker.isRunning():
            try:
                self._worker.progress.disconnect()
                self._worker.completed.disconnect()
                self._worker.failed.disconnect()
            except Exception:
                pass
            self._worker.cancel()
            self._worker.wait(500)


# ==============================================================================
# 10. WHISPER ASR & KINETIC CLUSTERING ENGINE
# ==============================================================================

def clean_word_token(raw: str) -> str:
    """
    Strips leading/trailing noise while preserving Unicode Cyrillic casing,
    inner hyphens/apostrophes, and Bulgarian song punctuation (commas).
    """
    stripped = raw.strip()
    cleaned = re.sub(r"^[^\w\'-]+|[^\w\',-]+$", "", stripped, flags=re.UNICODE)
    if not cleaned:
        cleaned = stripped
    return cleaned


def compress_hallucinated_tokens(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filters out repetitive loop hallucinations caused by instrumental music passages.
    Collapses consecutive identical single-word or 2-word phrase loops exceeding 3 repetitions.
    """
    if not tokens:
        return []

    filtered: List[Dict[str, Any]] = []
    repeat_count = 0
    last_norm = ""

    for tok in tokens:
        norm = re.sub(r"[^\w]", "", tok["text"], flags=re.UNICODE).lower()
        if norm and norm == last_norm:
            repeat_count += 1
            if repeat_count >= 3:
                continue
        else:
            repeat_count = 0
            last_norm = norm
        filtered.append(tok)

    result: List[Dict[str, Any]] = []
    i = 0
    n = len(filtered)
    while i < n:
        if i + 5 < n:
            w0 = filtered[i]["text"].lower()
            w1 = filtered[i + 1]["text"].lower()
            if (
                w0 == filtered[i + 2]["text"].lower() == filtered[i + 4]["text"].lower()
                and w1 == filtered[i + 3]["text"].lower() == filtered[i + 5]["text"].lower()
            ):
                result.append(filtered[i])
                result.append(filtered[i + 1])
                i += 6
                while i + 1 < n and filtered[i]["text"].lower() == w0 and filtered[i + 1]["text"].lower() == w1:
                    i += 2
                continue
        result.append(filtered[i])
        i += 1

    return result


def assign_lines_to_stanza_words(words: List[WordKeyframe]) -> None:
    """
    Deterministic line row allocator partitioning stanza words across
    Line 0 (Punch Header), Line 1 (Supporting), and Line 2 (Base)
    for both English and Bulgarian / Cyrillic lyrics.
    """
    n = len(words)
    if n <= 1:
        for w in words:
            w.line_index = 0
        return

    weak_particles = {
        "A", "AN", "THE", "AND", "OR", "BUT", "IF", "SO", "I", "TO", "OF", "IN", "ON", "AT", "BY", "FOR", "WITH",
        "И", "В", "ВЪВ", "С", "СЪС", "НА", "ЗА", "ОТ", "ДО", "ПО", "ДА", "НЕ", "ЧЕ", "КАК", "СЕ", "СИ", "ТЕ",
        "ТО", "ТЯ", "ТОЙ", "НИЕ", "ВИЕ", "АЗ", "Е", "СА", "БЕ", "БЯХ", "ЩЕ", "БИ", "ПРИ", "БЕЗ", "ПРЕЗ", "СЛЕД",
        "МЕ", "ГО", "Я", "НИ", "ВИ", "ГИ", "МИ", "ТИ", "МУ", "Й", "НО", "А", "ЛИ"
    }

    w0_text = re.sub(r"[^\w]", "", words[0].text.strip(), flags=re.UNICODE).upper()
    w0_is_weak = (w0_text in weak_particles) and n >= 3

    if n == 2:
        words[0].line_index = 0
        words[1].line_index = 1
    elif n == 3:
        if w0_is_weak:
            words[0].line_index = 0
            words[1].line_index = 0
            words[2].line_index = 1
        else:
            words[0].line_index = 0
            words[1].line_index = 1
            words[2].line_index = 1
    elif n == 4:
        if w0_is_weak:
            words[0].line_index = 0
            words[1].line_index = 0
            words[2].line_index = 1
            words[3].line_index = 1
        else:
            words[0].line_index = 0
            words[1].line_index = 1
            words[2].line_index = 1
            words[3].line_index = 2
    elif n == 5:
        if w0_is_weak:
            words[0].line_index = 0
            words[1].line_index = 0
            words[2].line_index = 1
            words[3].line_index = 2
            words[4].line_index = 2
        else:
            words[0].line_index = 0
            words[1].line_index = 1
            words[2].line_index = 1
            words[3].line_index = 2
            words[4].line_index = 2
    else:
        words[0].line_index = 0
        if w0_is_weak:
            words[1].line_index = 0
            words[2].line_index = 1
            words[3].line_index = 1
            for k in range(4, n):
                words[k].line_index = min(5, 2 + (k - 4) // 2)
        else:
            words[1].line_index = 1
            words[2].line_index = 1
            for k in range(3, n):
                words[k].line_index = min(5, 2 + (k - 3) // 2)


def cluster_and_style_words(
    raw_words: List[Any],
    pause_threshold_ms: int = 350,
    punch_intensity: float = 2.0,
    max_words_per_stanza: int = 6,
    default_preset: str = "stacked_punch",
) -> List[Stanza]:
    """
    Transforms raw timestamped speech tokens into styled kinetic stanzas with
    hallucination loop compression and Bulgarian Cyrillic punctuation awareness.
    """
    if not raw_words:
        return []

    extracted_tokens = []
    for rw in raw_words:
        word_text = getattr(rw, "word", str(rw))
        prob = getattr(rw, "probability", 1.0)
        if prob < 0.12:
            continue
        cleaned = clean_word_token(word_text)
        if cleaned:
            start_sec = getattr(rw, "start", 0.0)
            end_sec = getattr(rw, "end", start_sec + 0.3)
            s_ms = int(round(start_sec * 1000.0))
            e_ms = int(round(end_sec * 1000.0))
            if e_ms <= s_ms:
                e_ms = s_ms + 250
            has_term_punct = bool(re.search(r"[.?!;]$", word_text.strip()))
            has_comma_punct = bool(re.search(r"[,]$", cleaned))
            extracted_tokens.append({
                "text": cleaned,
                "start_ms": s_ms,
                "end_ms": e_ms,
                "term_punct": has_term_punct,
                "comma_punct": has_comma_punct,
            })

    valid_tokens = compress_hallucinated_tokens(extracted_tokens)
    if not valid_tokens:
        return []

    clusters: List[List[dict]] = []
    current_cluster: List[dict] = []

    for token in valid_tokens:
        if not current_cluster:
            current_cluster.append(token)
            continue

        prev_token = current_cluster[-1]
        pause_ms = token["start_ms"] - prev_token["end_ms"]
        current_span_ms = token["end_ms"] - current_cluster[0]["start_ms"]

        is_pause_split = pause_ms >= pause_threshold_ms
        is_count_split = len(current_cluster) >= max_words_per_stanza
        is_punct_split = prev_token["term_punct"] or (prev_token["comma_punct"] and len(current_cluster) >= 3)
        is_time_split = current_span_ms >= 4000
        is_overlap_split = token["start_ms"] < prev_token["start_ms"]

        if is_pause_split or is_count_split or is_punct_split or is_time_split or is_overlap_split:
            clusters.append(current_cluster)
            current_cluster = [token]
        else:
            current_cluster.append(token)

    if current_cluster:
        clusters.append(current_cluster)

    stanzas: List[Stanza] = []
    for c_idx, cluster in enumerate(clusters):
        stanza_words: List[WordKeyframe] = []
        for w_idx, tok in enumerate(cluster):
            duration_ms = max(50, tok["end_ms"] - tok["start_ms"])
            fade_in = min(120, max(40, int(math.floor(duration_ms * 0.35))))

            wk = WordKeyframe(
                id=f"ai_{c_idx}_{w_idx}_{uuid.uuid4().hex[:4]}",
                text=tok["text"],
                start_ms=tok["start_ms"],
                end_ms=tok["end_ms"],
                scale_multiplier=1.0,
                offset_x=0.0,
                offset_y=0.0,
                fade_in_ms=fade_in,
                fade_curve="cubic",
                inactive_opacity=0.0,
                line_index=0,
            )
            stanza_words.append(wk)

        assign_lines_to_stanza_words(stanza_words)
        l0_count = sum(1 for w in stanza_words if w.line_index == 0)

        for w in stanza_words:
            if w.line_index == 0:
                if l0_count == 1:
                    w.scale_multiplier = round(punch_intensity, 2)
                else:
                    w.scale_multiplier = round(max(1.35, punch_intensity * 0.75), 2)
            elif w.line_index == 1:
                w.scale_multiplier = 1.00
            elif w.line_index == 2:
                w.scale_multiplier = 1.15
            else:
                w.scale_multiplier = 1.00

        s_start = stanza_words[0].start_ms
        last_word_end = stanza_words[-1].end_ms

        next_s_start = None
        if c_idx + 1 < len(clusters):
            next_s_start = clusters[c_idx + 1][0]["start_ms"]

        if next_s_start is not None:
            delta_pause = max(0, next_s_start - last_word_end)
            hold_buffer = min(250, max(80, delta_pause))
            s_end = min(next_s_start, last_word_end + hold_buffer)
        else:
            s_end = last_word_end + 1000

        for w in stanza_words:
            w.end_ms = max(w.end_ms, s_end)

        stanza = Stanza(
            id=f"stanza_ai_{c_idx}_{uuid.uuid4().hex[:4]}",
            start_ms=s_start,
            end_ms=s_end,
            words=stanza_words,
            layout_preset=default_preset,
        )
        stanza.recompute_bounds()
        stanzas.append(stanza)

    return stanzas


class WhisperTranscriptionWorker(QThread):
    """
    Asynchronous background worker loading faster-whisper, executing speech-to-text
    with no_speech_prob filtering, hallucination compression, and Bulgarian Cyrillic rules.
    """
    progress = Signal(str, int)
    language_detected = Signal(str, float)
    finished_stanzas = Signal(list, str, float, int)
    error_occurred = Signal(str)

    def __init__(
        self,
        audio_path: str,
        model_name: str = "large-v3-turbo",
        device_choice: str = "auto",
        language_override: Optional[str] = None,
        punch_intensity: float = 2.0,
        pause_threshold_ms: int = 350,
        use_vad: bool = True,
        default_preset: str = "stacked_punch",
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.audio_path = audio_path
        self.model_name = model_name
        self.device_choice = device_choice
        self.language_override = language_override
        self.punch_intensity = punch_intensity
        self.pause_threshold_ms = pause_threshold_ms
        self.use_vad = use_vad
        self.default_preset = default_preset
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        try:
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                self.error_occurred.emit(
                    "The 'faster-whisper' package is not installed.\n\n"
                    "Please install it in your environment using:\n"
                    "pip install faster-whisper"
                )
                return

            cuda_available = False
            try:
                import ctranslate2
                cuda_available = ctranslate2.get_cuda_device_count() > 0
            except Exception:
                cuda_available = False

            device = self.device_choice
            if device == "auto":
                if cuda_available:
                    device = "cuda"
                    compute_type = "float16"
                else:
                    device = "cpu"
                    compute_type = "int8"
            elif device == "cuda":
                compute_type = "float16"
            else:
                compute_type = "int8"

            self.progress.emit(f"Loading Whisper '{self.model_name}' on {device.upper()}...", 5)

            try:
                model = WhisperModel(self.model_name, device=device, compute_type=compute_type)
            except Exception as e:
                if device == "cuda":
                    self.progress.emit(f"CUDA initialization failed ({e}). Falling back to CPU int8...", 8)
                    device = "cpu"
                    compute_type = "int8"
                    model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
                else:
                    raise e

            if self._is_cancelled:
                return

            self.progress.emit("Transcribing audio & filtering instrumental passages...", 15)

            lang_param = None
            if self.language_override and self.language_override != "auto":
                lang_param = self.language_override

            initial_prompt = None
            if lang_param == "bg":
                initial_prompt = (
                    "Текст на българска песен с ясна дикция, правилен правопис на кирилица, "
                    "запетаи пред съюзите че, но, а, които, и главни букви."
                )
            elif lang_param == "en":
                initial_prompt = "Song lyrics with clear vocal articulation, commas, and punctuation."

            vad_kwargs: Dict[str, Any] = {}
            if self.use_vad:
                vad_kwargs = {
                    "vad_filter": True,
                    "vad_parameters": dict(
                        min_silence_duration_ms=350,
                        speech_pad_ms=400,
                        threshold=0.30,
                    ),
                }
            else:
                vad_kwargs = {"vad_filter": False}

            segments_gen, info = model.transcribe(
                self.audio_path,
                word_timestamps=True,
                language=lang_param,
                initial_prompt=initial_prompt,
                condition_on_previous_text=False,
                compression_ratio_threshold=2.2,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.60,
                beam_size=5,
                best_of=5,
                temperature=[0.0, 0.2, 0.4],
                **vad_kwargs,
            )

            self.language_detected.emit(info.language, info.language_probability)

            raw_words = []
            total_duration_sec = max(0.5, info.duration) if info.duration else 1.0
            last_seg_text = ""
            repeat_seg_count = 0

            for segment in segments_gen:
                if self._is_cancelled:
                    return

                no_speech_prob = getattr(segment, "no_speech_prob", 0.0)
                if no_speech_prob > 0.72:
                    continue

                seg_norm = segment.text.strip().lower()
                if seg_norm and seg_norm == last_seg_text:
                    repeat_seg_count += 1
                    if repeat_seg_count >= 2:
                        continue
                else:
                    repeat_seg_count = 0
                    last_seg_text = seg_norm

                if segment.words:
                    for w in segment.words:
                        raw_words.append(w)

                pct = min(92, 15 + int(round((segment.end / total_duration_sec) * 75.0)))
                self.progress.emit(f"Transcribing: {segment.end:.1f}s / {total_duration_sec:.1f}s", pct)

            if self._is_cancelled:
                return

            self.progress.emit("Compressing hallucinations & clustering kinetic stanzas...", 95)

            stanzas = cluster_and_style_words(
                raw_words,
                pause_threshold_ms=self.pause_threshold_ms,
                punch_intensity=self.punch_intensity,
                default_preset=self.default_preset,
            )

            self.progress.emit("Complete!", 100)
            total_ms = int(round(total_duration_sec * 1000.0))
            self.finished_stanzas.emit(stanzas, info.language, info.language_probability, total_ms)

        except Exception as ex:
            self.error_occurred.emit(f"AI Auto-Transcription error:\n{str(ex)}")


class AIAutoGenerateDialog(QDialog):
    """
    Modal control suite for Whisper ASR model configuration, device selection,
    Bulgarian language optimization, punch intensity calibration, and live transcription progress.
    """

    def __init__(self, project: LyricProject, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("AI Auto-Transcription & Kinetic Lyrics")
        self.setMinimumSize(520, 520)

        self._worker: Optional[WhisperTranscriptionWorker] = None
        self._generated_stanzas: List[Stanza] = []
        self._detected_language: str = ""
        self._language_probability: float = 0.0
        self._audio_duration_ms: int = 0
        self._chosen_audio_path: str = project.audio_file or ""

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        hdr_box = QHBoxLayout()
        lbl_title = QLabel("AI AUTO-TRANSCRIPTION & KINETIC STYLING")
        lbl_title.setObjectName("panelHeader")
        hdr_box.addWidget(lbl_title)
        hdr_box.addStretch()
        layout.addLayout(hdr_box)

        audio_group = QGroupBox("Audio Source")
        audio_layout = QHBoxLayout(audio_group)

        self.edit_audio = QLineEdit()
        self.edit_audio.setPlaceholderText("Select an audio track (.wav, .mp3, .m4a, .flac)...")
        if self._chosen_audio_path:
            self.edit_audio.setText(self._chosen_audio_path)
        audio_layout.addWidget(self.edit_audio)

        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self._on_browse_audio)
        audio_layout.addWidget(self.btn_browse)
        layout.addWidget(audio_group)

        asr_group = QGroupBox("Whisper ASR Parameters")
        asr_layout = QVBoxLayout(asr_group)
        asr_layout.setSpacing(6)

        m_box = QHBoxLayout()
        m_box.addWidget(QLabel("Whisper Model:"))
        self.combo_model = QComboBox()
        self.combo_model.addItem("large-v3-turbo (~809M - Best for Bulgarian & Singing, Fast)", "large-v3-turbo")
        self.combo_model.addItem("medium (~769M - High Accuracy Multilingual)", "medium")
        self.combo_model.addItem("small (~244M - Balanced)", "small")
        self.combo_model.addItem("base (~74M - Fast Draft)", "base")
        self.combo_model.addItem("tiny (~39M - Ultra-Fast Draft)", "tiny")
        self.combo_model.setCurrentIndex(0)
        m_box.addWidget(self.combo_model)
        asr_layout.addLayout(m_box)

        d_box = QHBoxLayout()
        d_box.addWidget(QLabel("Compute Device:"))
        self.combo_device = QComboBox()
        self.combo_device.addItem("Auto (CUDA if available, else CPU)", "auto")
        self.combo_device.addItem("CUDA (NVIDIA GPU - Float16)", "cuda")
        self.combo_device.addItem("CPU (Standard - Int8)", "cpu")
        d_box.addWidget(self.combo_device)
        asr_layout.addLayout(d_box)

        l_box = QHBoxLayout()
        l_box.addWidget(QLabel("Spoken Language:"))
        self.combo_lang = QComboBox()
        self.combo_lang.addItem("Auto-Detect Language", "auto")
        languages = [
            ("Bulgarian (Български)", "bg"),
            ("English", "en"),
            ("Spanish", "es"),
            ("French", "fr"),
            ("German", "de"),
            ("Italian", "it"),
            ("Portuguese", "pt"),
            ("Russian", "ru"),
            ("Ukrainian", "uk"),
            ("Turkish", "tr"),
            ("Greek", "el"),
            ("Romanian", "ro"),
            ("Serbian", "sr"),
            ("Macedonian", "mk"),
            ("Japanese", "ja"),
            ("Korean", "ko"),
            ("Chinese", "zh"),
            ("Arabic", "ar"),
        ]
        for name, code in languages:
            self.combo_lang.addItem(name, code)
        self.combo_lang.currentIndexChanged.connect(self._on_lang_changed)
        l_box.addWidget(self.combo_lang)
        asr_layout.addLayout(l_box)

        self.chk_vad = QCheckBox("Voice Activity Filter (VAD) tuned for sustained singing")
        self.chk_vad.setChecked(True)
        asr_layout.addWidget(self.chk_vad)

        self.lbl_lang_hint = QLabel("Note: Hallucination compression and Bulgarian Cyrillic rules active.")
        self.lbl_lang_hint.setObjectName("mutedLabel")
        asr_layout.addWidget(self.lbl_lang_hint)

        layout.addWidget(asr_group)

        style_group = QGroupBox("Kinetic Clustering Parameters")
        style_layout = QVBoxLayout(style_group)
        style_layout.setSpacing(6)

        p_hdr = QHBoxLayout()
        p_hdr.addWidget(QLabel("Punch Intensity:"))
        self.lbl_punch_val = QLabel("2.0x")
        self.lbl_punch_val.setObjectName("accentValueLabel")
        p_hdr.addStretch()
        p_hdr.addWidget(self.lbl_punch_val)
        style_layout.addLayout(p_hdr)

        self.slider_punch = QSlider(Qt.Orientation.Horizontal)
        self.slider_punch.setRange(14, 25)
        self.slider_punch.setValue(20)
        self.slider_punch.valueChanged.connect(self._on_punch_slider_changed)
        style_layout.addWidget(self.slider_punch)

        s_hdr = QHBoxLayout()
        s_hdr.addWidget(QLabel("Silence Split Threshold:"))
        self.lbl_silence_val = QLabel("350 ms")
        self.lbl_silence_val.setObjectName("accentValueLabel")
        s_hdr.addStretch()
        s_hdr.addWidget(self.lbl_silence_val)
        style_layout.addLayout(s_hdr)

        self.slider_silence = QSlider(Qt.Orientation.Horizontal)
        self.slider_silence.setRange(250, 750)
        self.slider_silence.setValue(350)
        self.slider_silence.setSingleStep(25)
        self.slider_silence.valueChanged.connect(lambda v: self.lbl_silence_val.setText(f"{v} ms"))
        style_layout.addWidget(self.slider_silence)

        layout.addWidget(style_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Select an audio track and click 'Start Auto-Generation'.")
        self.lbl_status.setObjectName("mutedLabel")
        layout.addWidget(self.lbl_status)

        btn_box = QHBoxLayout()
        self.btn_start = QPushButton("Start Auto-Generation")
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.clicked.connect(self._on_start_transcription)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self._on_cancel)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_start)
        btn_box.addWidget(self.btn_cancel)
        layout.addLayout(btn_box)

    def _on_lang_changed(self, idx: int) -> None:
        code = self.combo_lang.currentData()
        if code == "bg":
            self.lbl_lang_hint.setText("Bulgarian Selected: Preserving Cyrillic casing, commas, and lyrical syntax.")
            if self.combo_model.currentIndex() > 1:
                self.combo_model.setCurrentIndex(0)
        else:
            self.lbl_lang_hint.setText("Note: Hallucination compression and vocal VAD tuning active.")

    def _on_punch_slider_changed(self, val: int) -> None:
        p = val / 10.0
        self.lbl_punch_val.setText(f"{p:.1f}x")

    def _on_browse_audio(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "", "Audio Files (*.wav *.mp3 *.m4a *.flac *.ogg)"
        )
        if path:
            self.edit_audio.setText(path)
            self._chosen_audio_path = path

    def _on_start_transcription(self) -> None:
        audio_path = self.edit_audio.text().strip()
        if not audio_path or not os.path.exists(audio_path):
            QMessageBox.warning(self, "Invalid Audio", "Please select a valid existing audio file.")
            return

        self._chosen_audio_path = audio_path
        model_name = self.combo_model.currentData()
        device_choice = self.combo_device.currentData()
        lang_choice = self.combo_lang.currentData()
        punch_intensity = self.slider_punch.value() / 10.0
        pause_threshold_ms = self.slider_silence.value()
        use_vad = self.chk_vad.isChecked()

        self.btn_start.setEnabled(False)
        self.combo_model.setEnabled(False)
        self.combo_device.setEnabled(False)
        self.combo_lang.setEnabled(False)
        self.chk_vad.setEnabled(False)
        self.slider_punch.setEnabled(False)
        self.slider_silence.setEnabled(False)
        self.btn_browse.setEnabled(False)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Initializing transcription engine...")

        self._worker = WhisperTranscriptionWorker(
            audio_path=audio_path,
            model_name=model_name,
            device_choice=device_choice,
            language_override=lang_choice,
            punch_intensity=punch_intensity,
            pause_threshold_ms=pause_threshold_ms,
            use_vad=use_vad,
            default_preset=self.project.default_layout_preset,
            parent=self,
        )
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.language_detected.connect(self._on_worker_language)
        self._worker.finished_stanzas.connect(self._on_worker_finished)
        self._worker.error_occurred.connect(self._on_worker_error)
        self._worker.start()

    def _on_worker_progress(self, msg: str, pct: int) -> None:
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(msg)

    def _on_worker_language(self, lang_code: str, prob: float) -> None:
        self._detected_language = lang_code
        self._language_probability = prob
        self.lbl_status.setText(f"Detected language: {lang_code.upper()} ({prob * 100.0:.1f}% confidence)")

    def _on_worker_finished(
        self, stanzas: List[Stanza], lang: str, prob: float, total_ms: int
    ) -> None:
        self._generated_stanzas = stanzas
        self._detected_language = lang
        self._language_probability = prob
        self._audio_duration_ms = total_ms

        self.progress_bar.setValue(100)
        self.lbl_status.setText("Transcription & clustering complete!")
        self.accept()

    def _on_worker_error(self, err_msg: str) -> None:
        self.btn_start.setEnabled(True)
        self.combo_model.setEnabled(True)
        self.combo_device.setEnabled(True)
        self.combo_lang.setEnabled(True)
        self.chk_vad.setEnabled(True)
        self.slider_punch.setEnabled(True)
        self.slider_silence.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.lbl_status.setText("Transcription failed.")
        QMessageBox.critical(self, "Transcription Error", err_msg)

    def _on_cancel(self) -> None:
        self._cleanup_worker()
        self.reject()

    def closeEvent(self, event) -> None:
        self._cleanup_worker()
        event.accept()

    def _cleanup_worker(self) -> None:
        if self._worker and self._worker.isRunning():
            try:
                self._worker.progress.disconnect()
                self._worker.language_detected.disconnect()
                self._worker.finished_stanzas.disconnect()
                self._worker.error_occurred.disconnect()
            except Exception:
                pass
            self._worker.cancel()
            self._worker.wait(500)

    def get_results(self) -> Optional[Tuple[List[Stanza], str, float, int, str]]:
        if self._generated_stanzas:
            return (
                self._generated_stanzas,
                self._detected_language,
                self._language_probability,
                self._audio_duration_ms,
                self._chosen_audio_path,
            )
        return None


# ==============================================================================
# 11. MAIN APPLICATION STUDIO WINDOW & ENTRY POINT
# ==============================================================================

class InstagramKineticStudio(QMainWindow):
    """
    Main desktop studio application coordinating the kinetic layout engine,
    preview canvas, NLE multi-selection timeline sequencer, parameter inspector,
    atomic QUndoStack history, AI auto-transcription engine, and FFmpeg export.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instagram Kinetic Typography Studio")
        self.resize(1380, 920)

        self.project = LyricProject.create_default_punch_sample()
        self.undo_stack = QUndoStack(self)
        self.selected_word_ids: Set[str] = set()
        self.active_primary_word_id: Optional[str] = None

        self._setup_style()
        self._setup_ui()
        self._setup_menus()
        self._bind_signals()

        if self.project.stanzas and self.project.stanzas[0].words:
            first_w = self.project.stanzas[0].words[0]
            self._on_selection_changed({first_w.id}, first_w.id)

    def _setup_style(self) -> None:
        self.setStyleSheet(STYLE_SHEET)

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 2, 4, 2)
        top_bar.setSpacing(6)

        lbl_proj = QLabel("KINETIC STUDIO")
        lbl_proj.setObjectName("panelHeader")
        top_bar.addWidget(lbl_proj)

        top_bar.addSpacing(8)

        self.btn_undo = QPushButton("UNDO")
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self.undo_stack.undo)
        top_bar.addWidget(self.btn_undo)

        self.btn_redo = QPushButton("REDO")
        self.btn_redo.setEnabled(False)
        self.btn_redo.clicked.connect(self.undo_stack.redo)
        top_bar.addWidget(self.btn_redo)

        self.undo_stack.canUndoChanged.connect(self.btn_undo.setEnabled)
        self.undo_stack.canRedoChanged.connect(self.btn_redo.setEnabled)

        top_bar.addSpacing(8)

        top_bar.addWidget(QLabel("Aspect:"))
        self.combo_aspect = QComboBox()
        self.combo_aspect.addItem("9:16 (1080x1920)", (1080, 1920))
        self.combo_aspect.addItem("1:1 (1080x1080)", (1080, 1080))
        top_bar.addWidget(self.combo_aspect)

        top_bar.addWidget(QLabel("Inactive:"))
        self.combo_inactive_global = QComboBox()
        self.combo_inactive_global.addItem("0% Invisible", 0.0)
        self.combo_inactive_global.addItem("30% Dimmed", 0.30)
        top_bar.addWidget(self.combo_inactive_global)

        fade_box = QHBoxLayout()
        fade_box.setSpacing(4)
        fade_box.addWidget(QLabel("Fade:"))
        self.slider_global_fade = QSlider(Qt.Orientation.Horizontal)
        self.slider_global_fade.setRange(10, 1000)
        self.slider_global_fade.setSingleStep(20)
        self.slider_global_fade.setValue(self.project.global_fade_in_ms)
        self.slider_global_fade.setFixedWidth(80)
        fade_box.addWidget(self.slider_global_fade)

        self.lbl_global_fade = QLabel(f"{self.project.global_fade_in_ms} ms")
        self.lbl_global_fade.setFixedWidth(48)
        self.lbl_global_fade.setObjectName("accentValueLabel")
        fade_box.addWidget(self.lbl_global_fade)
        top_bar.addLayout(fade_box)

        top_bar.addWidget(QLabel("BG:"))
        self.combo_bg = QComboBox()
        self.combo_bg.addItems(["Solid Black (#000000)", "Checkerboard Alpha", "Custom Media Overlay"])
        top_bar.addWidget(self.combo_bg)

        self.btn_load_bg = QPushButton("BG File...")
        self.btn_load_bg.clicked.connect(self._on_load_bg_media)
        top_bar.addWidget(self.btn_load_bg)

        top_bar.addWidget(QLabel("Dim:"))
        self.slider_bg_dim = QSlider(Qt.Orientation.Horizontal)
        self.slider_bg_dim.setRange(0, 100)
        self.slider_bg_dim.setValue(int(round(self.project.bg_dim_opacity * 100)))
        self.slider_bg_dim.setFixedWidth(65)
        top_bar.addWidget(self.slider_bg_dim)

        self.chk_guides = QCheckBox("Guides")
        self.chk_guides.setChecked(True)
        top_bar.addWidget(self.chk_guides)

        top_bar.addStretch()

        self.btn_load_audio = QPushButton("Load Audio...")
        self.btn_load_audio.clicked.connect(self._on_load_audio)
        top_bar.addWidget(self.btn_load_audio)

        self.btn_ai_generate = QPushButton("AI AUTO-GENERATE")
        self.btn_ai_generate.setObjectName("accentActionButton")
        self.btn_ai_generate.clicked.connect(self._on_open_ai_dialog)
        top_bar.addWidget(self.btn_ai_generate)

        self.btn_export = QPushButton("EXPORT VIDEO")
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.clicked.connect(self._on_open_export_dialog)
        top_bar.addWidget(self.btn_export)

        main_layout.addLayout(top_bar)

        center_splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self.canvas = PreviewCanvasWidget(self.project)
        left_layout.addWidget(self.canvas, stretch=1)

        self.transport = AudioTransport(self.project)
        left_layout.addWidget(self.transport)

        center_splitter.addWidget(left_widget)

        inspector_scroll = QScrollArea()
        inspector_scroll.setWidgetResizable(True)
        inspector_scroll.setFixedWidth(350)
        inspector_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.inspector = WordInspectorWidget(self.project)
        inspector_scroll.setWidget(self.inspector)
        center_splitter.addWidget(inspector_scroll)

        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.addWidget(center_splitter)

        timeline_box = QWidget()
        timeline_box.setObjectName("dockPanel")
        t_layout = QVBoxLayout(timeline_box)
        t_layout.setContentsMargins(4, 4, 4, 4)
        t_layout.setSpacing(4)

        t_header = QHBoxLayout()
        t_lbl = QLabel("TIMELINE & KEYFRAMES  [DRAG MARQUEE: MULTI-SELECT | SHIFT/CTRL+CLICK: ADD/TOGGLE | DEL: REMOVE]")
        t_lbl.setObjectName("mutedLabel")
        t_header.addWidget(t_lbl)
        t_header.addStretch()

        t_header.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(50, 600)
        self.zoom_slider.setValue(180)
        self.zoom_slider.setFixedWidth(120)
        self.zoom_slider.valueChanged.connect(lambda v: self.timeline.set_zoom(float(v)))
        t_header.addWidget(self.zoom_slider)

        t_layout.addLayout(t_header)

        self.timeline = TimelineWidget(self.project)
        t_layout.addWidget(self.timeline)

        self.timeline_scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        self.timeline_scrollbar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        t_layout.addWidget(self.timeline_scrollbar)
        self.timeline.set_scrollbar(self.timeline_scrollbar)

        v_splitter.addWidget(timeline_box)
        v_splitter.setStretchFactor(0, 7)
        v_splitter.setStretchFactor(1, 3)

        main_layout.addWidget(v_splitter, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("READY | ENGINE: DETERMINISTIC 60FPS | NLE MULTI-SELECT & UNDO STACK: ACTIVE")

    def _setup_menus(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu("&File")

        act_new = QAction("&New Project", self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._on_new_project)
        file_menu.addAction(act_new)

        act_open = QAction("&Open Project JSON...", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._on_open_project)
        file_menu.addAction(act_open)

        act_save = QAction("&Save Project JSON", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self._on_save_project)
        file_menu.addAction(act_save)

        file_menu.addSeparator()

        act_export = QAction("&Export Video...", self)
        act_export.setShortcut(QKeySequence("Ctrl+E"))
        act_export.triggered.connect(self._on_open_export_dialog)
        file_menu.addAction(act_export)

        edit_menu = bar.addMenu("&Edit")

        act_undo = self.undo_stack.createUndoAction(self, "&Undo")
        act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(act_undo)

        act_redo = self.undo_stack.createRedoAction(self, "&Redo")
        act_redo.setShortcuts([QKeySequence.StandardKey.Redo, QKeySequence("Ctrl+Y")])
        edit_menu.addAction(act_redo)

        edit_menu.addSeparator()

        act_select_all = QAction("Select &All Words", self)
        act_select_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        act_select_all.triggered.connect(self._on_select_all_words)
        edit_menu.addAction(act_select_all)

        act_delete_sel = QAction("&Delete Selected Words", self)
        act_delete_sel.setShortcuts([QKeySequence.StandardKey.Delete, QKeySequence(Qt.Key.Key_Backspace)])
        act_delete_sel.triggered.connect(self._on_delete_selected_words)
        edit_menu.addAction(act_delete_sel)

        edit_menu.addSeparator()

        act_space = QAction("Play / Pause", self)
        act_space.setShortcut(QKeySequence(Qt.Key.Key_Space))
        act_space.triggered.connect(self.transport.toggle_play)
        edit_menu.addAction(act_space)

        tools_menu = bar.addMenu("&Tools")
        act_ai = QAction("&AI Auto-Generate Lyrics...", self)
        act_ai.setShortcut(QKeySequence("Ctrl+Shift+A"))
        act_ai.triggered.connect(self._on_open_ai_dialog)
        tools_menu.addAction(act_ai)

    def _bind_signals(self) -> None:
        self.combo_aspect.currentIndexChanged.connect(self._on_aspect_ratio_changed)
        self.combo_inactive_global.currentIndexChanged.connect(self._on_global_inactive_style_changed)
        self.slider_global_fade.valueChanged.connect(self._on_global_fade_changed)
        self.combo_bg.currentIndexChanged.connect(self._on_bg_mode_changed)
        self.slider_bg_dim.valueChanged.connect(self._on_bg_dim_changed)
        self.chk_guides.toggled.connect(self.canvas.toggle_guides)

        self.transport.time_changed.connect(self._on_time_sync)
        self.transport.play_state_changed.connect(self.canvas.on_play_state_changed)
        self.transport.duration_changed.connect(self._on_duration_changed)

        self.timeline.time_scrubbed.connect(self._on_timeline_scrub)
        self.timeline.selection_changed.connect(self._on_selection_changed)
        self.timeline.duration_expanded.connect(self.transport.set_duration)
        self.timeline.batch_timing_committed.connect(self._on_batch_timing_committed)
        self.timeline.delete_selected_requested.connect(self._on_delete_selected_words)
        self.canvas.selection_changed.connect(self._on_selection_changed)

        self.inspector.word_updated.connect(self._on_project_modified)
        self.inspector.batch_property_committed.connect(self._on_batch_property_committed)
        self.inspector.batch_timing_committed.connect(self._on_batch_timing_committed)
        self.inspector.delete_requested.connect(self._on_delete_selected_words)
        self.inspector.add_word_requested.connect(self._on_add_word)
        self.inspector.new_stanza_requested.connect(self._on_new_stanza)
        self.inspector.delete_stanza_requested.connect(self._on_delete_stanza)
        self.timeline.project_changed.connect(self._on_project_modified)

    def _on_undo_callback(self, selected_ids: Set[str], primary_id: Optional[str]) -> None:
        self._on_selection_changed(selected_ids, primary_id or "")
        self._on_project_modified()

    def _on_batch_timing_committed(self, changes: List[Tuple[str, int, int, int, int]]) -> None:
        if not changes:
            return
        cmd = BatchWordTimingUndoCommand(
            self.project,
            changes,
            self.selected_word_ids,
            self.active_primary_word_id,
            self._on_undo_callback,
        )
        self.undo_stack.push(cmd)

    def _on_batch_property_committed(self, prop_name: str, changes: List[Tuple[str, Any, Any]]) -> None:
        if not changes:
            return
        cmd = BatchWordPropertyUndoCommand(
            self.project,
            prop_name,
            changes,
            self.selected_word_ids,
            self.active_primary_word_id,
            self._on_undo_callback,
        )
        self.undo_stack.push(cmd)

    def _on_select_all_words(self) -> None:
        fw = QApplication.focusWidget()
        if isinstance(fw, QLineEdit):
            fw.selectAll()
            return
        all_ids = self.project.get_all_word_ids()
        primary = self.active_primary_word_id
        if not primary or primary not in all_ids:
            primary = next(iter(all_ids)) if all_ids else ""
        self._on_selection_changed(all_ids, primary or "")

    def _on_selection_changed(self, word_ids: Set[str], primary_id: str) -> None:
        valid_ids = {wid for wid in word_ids if self.project.find_word_by_id(wid) is not None}
        primary: Optional[str] = primary_id if (primary_id and primary_id in valid_ids) else (
            next(iter(valid_ids)) if valid_ids else None
        )
        self.selected_word_ids = valid_ids
        self.active_primary_word_id = primary

        self.canvas.set_selection(valid_ids, primary)
        self.timeline.set_selection(valid_ids, primary)
        self.inspector.set_selection(valid_ids, primary)

    def _on_bg_mode_changed(self, idx: int) -> None:
        modes = ["black", "checkerboard", "custom"]
        mode = modes[idx] if 0 <= idx < len(modes) else "black"
        if mode == "custom" and not self.project.bg_media_path:
            self._on_load_bg_media()
        self.canvas.set_background_mode(mode)

    def _on_load_bg_media(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Background Image or Video",
            "",
            "Media Files (*.png *.jpg *.jpeg *.webp *.bmp *.mp4 *.mov *.webm *.mkv)",
        )
        if path:
            if self.canvas.load_background_media(path):
                self.combo_bg.blockSignals(True)
                self.combo_bg.setCurrentIndex(2)
                self.combo_bg.blockSignals(False)
                self.canvas.set_background_mode("custom")
                self.status_bar.showMessage(f"Loaded background media: {os.path.basename(path)}")

    def _on_bg_dim_changed(self, val: int) -> None:
        self.project.bg_dim_opacity = val / 100.0
        self.canvas.update()

    def _on_time_sync(self, time_ms: int) -> None:
        self.canvas.set_time(time_ms)
        self.timeline.set_time(time_ms)

    def _on_timeline_scrub(self, time_ms: int) -> None:
        self.transport.seek(time_ms)

    def _on_project_modified(self) -> None:
        self.canvas.update()
        self.timeline.update()

    def _on_aspect_ratio_changed(self) -> None:
        dims = self.combo_aspect.currentData()
        self.project.resolution_width = dims[0]
        self.project.resolution_height = dims[1]
        self.canvas.update()

    def _on_global_inactive_style_changed(self) -> None:
        val = self.combo_inactive_global.currentData()
        self.project.global_inactive_opacity = val
        for s in self.project.stanzas:
            for w in s.words:
                w.inactive_opacity = val
        self.inspector.set_selection(self.selected_word_ids, self.active_primary_word_id)
        self._on_project_modified()

    def _on_global_fade_changed(self, val: int) -> None:
        self.lbl_global_fade.setText(f"{val} ms")
        self.project.global_fade_in_ms = val
        for s in self.project.stanzas:
            for w in s.words:
                w.fade_in_ms = val
        self.inspector.set_selection(self.selected_word_ids, self.active_primary_word_id)
        self._on_project_modified()

    def _on_duration_changed(self, duration_ms: int) -> None:
        self.project.duration_ms = duration_ms
        self.timeline.update()
        self.timeline.update_scrollbar()

    def _on_load_audio(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Audio Track", "", "Audio Files (*.wav *.mp3 *.m4a *.flac *.ogg)"
        )
        if path:
            self.transport.load_audio(path)
            self.timeline.load_audio_waveform(path)
            self.status_bar.showMessage(f"Loaded audio track: {os.path.basename(path)}")

    def _on_open_ai_dialog(self) -> None:
        try:
            import faster_whisper
        except ImportError:
            QMessageBox.warning(
                self,
                "faster-whisper Required",
                "The 'faster-whisper' package is required for AI auto-transcription.\n\n"
                "Please install it in your terminal via:\n"
                "pip install faster-whisper",
            )
            return

        dlg = AIAutoGenerateDialog(self.project, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            res = dlg.get_results()
            if res:
                stanzas, lang, confidence, total_ms, audio_path = res
                if audio_path and (not self.project.audio_file or self.project.audio_file != audio_path):
                    self.transport.load_audio(audio_path)
                    self.timeline.load_audio_waveform(audio_path)

                old_data = [s.to_dict() for s in self.project.stanzas]
                new_data = [s.to_dict() for s in stanzas]
                first_id = stanzas[0].words[0].id if (stanzas and stanzas[0].words) else None

                cmd = StanzaListUndoCommand(
                    self.project,
                    old_data,
                    new_data,
                    first_id,
                    "AI Auto-Generate Lyrics",
                    self._on_undo_callback,
                )
                self.undo_stack.push(cmd)

                if total_ms > 0:
                    self.transport.set_duration(total_ms)
                    self.project.duration_ms = total_ms

                self._refresh_project_views()

                total_words = sum(len(s.words) for s in stanzas)
                lang_display = lang.upper() if lang else "UNKNOWN"
                conf_pct = confidence * 100.0 if confidence else 0.0
                msg = f"Generated {len(stanzas)} stanzas ({total_words} words) | Lang: {lang_display} ({conf_pct:.1f}%)"
                self.status_bar.showMessage(msg)

    def _on_add_word(self) -> None:
        active_stanza = self.project.get_active_stanza(self.transport.current_time_ms)
        created_new = False
        if not active_stanza and self.project.stanzas:
            active_stanza = self.project.stanzas[0]

        if not active_stanza:
            active_stanza = Stanza(
                start_ms=0,
                end_ms=2500,
                layout_preset=self.project.default_layout_preset,
            )
            self.project.stanzas.append(active_stanza)
            created_new = True

        t_curr = self.transport.current_time_ms
        new_w = WordKeyframe(
            text="NEW",
            start_ms=t_curr,
            end_ms=t_curr + 600,
            scale_multiplier=1.0,
            fade_in_ms=self.project.global_fade_in_ms,
            inactive_opacity=self.project.global_inactive_opacity,
            line_index=0,
        )
        cmd = AddWordUndoCommand(
            self.project,
            active_stanza.id,
            new_w.to_dict(),
            created_new,
            self._on_undo_callback,
        )
        self.undo_stack.push(cmd)
        if active_stanza.end_ms > self.project.duration_ms:
            self.transport.set_duration(active_stanza.end_ms + 1000)

    def _on_delete_selected_words(self) -> None:
        fw = QApplication.focusWidget()
        if isinstance(fw, QLineEdit):
            return
        if not self.selected_word_ids:
            return
        cmd = BatchDeleteWordsUndoCommand(
            self.project,
            self.selected_word_ids,
            self.active_primary_word_id,
            self._on_undo_callback,
        )
        self.undo_stack.push(cmd)

    def _on_new_stanza(self) -> None:
        old_data = [s.to_dict() for s in self.project.stanzas]
        last_end = max((s.end_ms for s in self.project.stanzas), default=0)
        new_s = Stanza(
            start_ms=last_end + 100,
            end_ms=last_end + 1800,
            layout_preset=self.project.default_layout_preset,
        )
        w1 = WordKeyframe(
            text="PUNCH",
            start_ms=last_end + 100,
            end_ms=last_end + 1800,
            scale_multiplier=2.0,
            fade_in_ms=self.project.global_fade_in_ms,
            inactive_opacity=self.project.global_inactive_opacity,
        )
        new_s.words.append(w1)
        new_s.recompute_bounds()
        new_data = old_data + [new_s.to_dict()]

        cmd = StanzaListUndoCommand(
            self.project, old_data, new_data, w1.id, "Add Stanza", self._on_undo_callback
        )
        self.undo_stack.push(cmd)

        if new_s.end_ms > self.project.duration_ms:
            self.transport.set_duration(new_s.end_ms + 1000)

    def _on_delete_stanza(self) -> None:
        if not self.project.stanzas:
            return
        active_stanza = self.project.get_active_stanza(self.transport.current_time_ms)
        if active_stanza:
            old_data = [s.to_dict() for s in self.project.stanzas]
            new_data = [s.to_dict() for s in self.project.stanzas if s.id != active_stanza.id]
            cmd = StanzaListUndoCommand(
                self.project, old_data, new_data, None, "Delete Stanza", self._on_undo_callback
            )
            self.undo_stack.push(cmd)

    def _on_new_project(self) -> None:
        self.undo_stack.clear()
        self.project = LyricProject.create_default_punch_sample()
        self._refresh_project_views()

    def _on_open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Project JSON", "", "JSON Files (*.json)")
        if path:
            try:
                self.undo_stack.clear()
                self.project = LyricProject.load(path)
                self._refresh_project_views()
                self.status_bar.showMessage(f"Project loaded: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error Loading Project", str(e))

    def _on_save_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Project JSON", "lyrics_project.json", "JSON Files (*.json)")
        if path:
            try:
                self.project.save(path)
                self.status_bar.showMessage(f"Project saved: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error Saving Project", str(e))

    def _refresh_project_views(self) -> None:
        self.canvas.set_project(self.project)
        self.timeline.set_project(self.project)
        self.inspector.set_project(self.project)
        self.transport.set_project(self.project)
        self.transport.set_duration(self.project.duration_ms)
        self.slider_global_fade.blockSignals(True)
        self.slider_global_fade.setValue(self.project.global_fade_in_ms)
        self.lbl_global_fade.setText(f"{self.project.global_fade_in_ms} ms")
        self.slider_global_fade.blockSignals(False)
        if self.project.stanzas and self.project.stanzas[0].words:
            w0 = self.project.stanzas[0].words[0]
            self._on_selection_changed({w0.id}, w0.id)
        else:
            self._on_selection_changed(set(), "")
        self._on_project_modified()

    def _on_open_export_dialog(self) -> None:
        dlg = ExportDialog(self.project, self)
        dlg.exec()


def main():
    if hasattr(Qt.HighDpiScaleFactorRoundingPolicy, "PassThrough"):
        try:
            QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("InstagramKineticStudio")
    window = InstagramKineticStudio()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
