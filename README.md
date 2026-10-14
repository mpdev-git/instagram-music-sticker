# ⚡ Kinetic Studio

> **Fast, frame-accurate kinetic typography and punch lyrics for Reels, Shorts, and TikTok.**  
> Built with Python, PySide6, and headless FFmpeg streaming. No subscription, no watermarks, completely offline.

---
![instagram_lyrics_prores - Trim](https://github.com/user-attachments/assets/a46252ce-41e0-4ecd-885a-dac8acf014f7)

### Why I built this

If you've ever tried making those hard-hitting, word-by-word rap or hip-hop lyric videos in Premiere Pro or After Effects, you know the drill:
- Chopping up 100 text layers by hand.
- Nudging keyframes back and forth trying to match fast flows.
- Generic auto-caption apps (CapCut, Submix) that look templated and give you zero control over layout stacking or negative leading.

I wanted something dedicated: an actual desktop tool where I could drop in a beat, click AI auto-transcribe (or tap keys to sync), pick heavy fonts, customize individual letters, slap on background video, and export crisp 60/120/240 fps videos with zero hassle.

---

## ✨ Features

- **4 Kinetic Animation Presets**
  - **Stacked Punch:** Aggressive multi-line row stacking with punch scale emphasis on primary rhymes.
  - **Box Badge:** Clean inverted black-on-white badge highlighting active words.
  - **Word Stagger Drift:** Smooth alternating directional drift on word hit.
  - **Hard-Cut Glitch:** Sharp vector micro-displacement on impact.
- **Deep Font & Typography Control**
  - **Global Project Font:** Pick any installed system font or load your own `.ttf` / `.otf` / `.woff` file.
  - **Word Font Override:** Give specific punch words their own font.
  - **Letter Font Override:** Customize individual letters within a word (e.g. make the first letter an old English serif and the rest heavy grotesque).
  - Fine-grained control over letter spacing, line height (negative leading), and stroke outline width & color.
- **Non-Linear Multi-Track Timeline**
  - Interactive audio waveform view with zoom and horizontal scroll.
  - Draggable keyframe blocks with left/right trim handles.
  - Multi-select with drag-marquee, `Shift+Click` and `Ctrl+Click`.
  - Full Undo / Redo (`Ctrl+Z` / `Ctrl+Y`) stack for every single parameter.
- **AI Auto-Transcription (Whisper)**
  - Integrated with `faster-whisper` (runs locally on CUDA GPU or CPU).
  - VAD (Voice Activity Detection) filtering tuned for singing and instrumental pauses.
  - Built-in Cyrillic / Bulgarian and English linguistic rules to avoid hallucinations.
- **High-FPS Video Export (FFmpeg Pipe)**
  - Direct headless memory streaming: pushes raw RGBA byte frames straight into FFmpeg's `stdin`.
  - Supports **1 FPS to 240 FPS** custom framerates.
  - Aspect ratio presets: **9:16 vertical** (1080x1920 Reels/TikTok) and **1:1 square** (1080x1080 Feed).
  - Background video and images scale and loop automatically with adjustable dimmer overlays.
  - Codecs: H.264 (MP4), ProRes 4444 (with alpha channel), VP9 (WebM with alpha).

---

## 🚀 Quick Start

### 1. Requirements

- **Python 3.10+**
- **FFmpeg** installed and added to your system `PATH` ([Download FFmpeg](https://ffmpeg.org/download.html)).  
  *(Verify in terminal: `ffmpeg -version`)*

### 2. Install Dependencies

Clone this repo (or download `app.py`):

```bash
git clone https://github.com/your-username/kinetic-studio.git
cd kinetic-studio
```

Install the required packages:

```bash
pip install PySide6 numpy
```

*(Optional) If you want the offline AI Auto-Transcription feature:*
```bash
pip install faster-whisper
```
> **Note for NVIDIA GPU users:** If you have an NVIDIA card and want faster-whisper to run on CUDA, make sure you have the CUDA toolkit or run with CPU mode (int8).

### 3. Launch

```bash
python app.py
```

---

## ⌨️ Keyboard & Mouse Shortcuts

| Action | Shortcut / Gesture |
| :--- | :--- |
| **Play / Pause** | `Spacebar` |
| **Scrub Timeline** | Click or drag on the ruler / waveform |
| **Zoom Timeline** | `Mouse Wheel` (vertical) or Zoom Slider |
| **Scroll Timeline** | `Shift + Mouse Wheel` or Timeline Scrollbar |
| **Multi-Select Words** | Click & drag marquee over word blocks |
| **Add to Selection** | `Shift + Click` or `Ctrl + Click` |
| **Trim Word Timing** | Drag left or right edge handles of any word block |
| **Move Word Timing** | Click and drag the center of a word block |
| **Delete Selected Word(s)** | `Delete` or `Backspace` |
| **Select All Words** | `Ctrl + A` |
| **Undo / Redo** | `Ctrl + Z` / `Ctrl + Y` |
| **Export Video Dialog** | `Ctrl + E` |

---

## 🛠️ How It Works Under The Hood

```
[ Audio / Lyrics ] ──> [ KineticLayoutEngine ] ──> [ QPainterPath Vector Glyphs ]
                               │                                  │
                               ▼                                  ▼
                     [ Real-Time Viewport ]           [ Headless FFmpeg Subprocess ]
                   (Aspect Framing & Guides)              (Pipes raw RGBA frames)
                                                                  │
                                                                  ▼
                                                      [ Final Rendered MP4 / MOV ]
```

1. **Deterministic Timing:** Every frame timestamp is calculated mathematically (`(frame_index / fps) * 1000.0`), guaranteeing zero drift between audio and video across any framerate.
2. **True Vector Glyphs:** Words and individual letters are measured with sub-pixel precision (`QFontMetricsF`) and converted directly into vector outline paths (`QPainterPath`). This allows unified strokes, fills, and kinetic presets without raster blur or jagged edges.
3. **Zero Temp Files on Export:** Rather than saving thousands of PNG files to disk, frames are written directly to FFmpeg's standard input pipe as continuous RGBA byte arrays.

---

## 📁 Project Format

Saving your work creates a clean, lightweight `.json` file holding your timestamps, fonts, colors, and layout presets. It looks something like this:

```json
{
  "title": "Punch Lyrics Project",
  "base_font_family": "Inter",
  "fps": 60,
  "align_y": 0.42,
  "stroke_width": 3.0,
  "stroke_color": "#000000",
  "stanzas": [
    {
      "start_ms": 100,
      "end_ms": 1550,
      "layout_preset": "stacked_punch",
      "words": [
        {
          "text": "REP",
          "start_ms": 100,
          "end_ms": 1550,
          "scale_multiplier": 2.3,
          "line_index": 0,
          "letter_fonts": { "0": "Impact" }
        }
      ]
    }
  ]
}
```

---

## 🤝 Contributing

Found a bug or have an idea for another kinetic preset (like bounce or 3D rotation)?  
Feel free to open an issue or submit a pull request!

## 📄 License

MIT License. Do whatever you want with it — commercial reels, music videos, or your own tools.

## Disclaimer - I built this with AI, not hiding it. I have to disclaim it.
