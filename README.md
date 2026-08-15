# dice-cam

Read a **D20 roll from a webcam** and report the result — on-screen and optionally to Discord.

Point a webcam at a dice tray, roll, and dice-cam detects when the die settles, crops tightly to it, and reads the top face with a vision LLM (Google Gemini). The design goal, stated from day one:

> "Anyone could use it with any reasonable camera setup and a die."

No fixed rig, no controlled lighting, no special die. One-time in-app setup (click the tray outline, run calibration) is all that's expected.

## How it works

1. **Settle detection** (`settle_detector.py`) — frame-to-frame difference over the tray region. The motion threshold is derived from measured camera noise at calibration, not hardcoded, so it adapts to any webcam. When motion stops after having occurred, a roll has settled.
2. **Locate and crop** (`frame_initialization.py`, `MAIN.py`) — a background model of the empty tray is captured at calibration; occupancy is measured by background subtraction inside a user-clicked polygon mask. The die is found by contour, sanity-checked (`validCapture`), and cropped tightly.
3. **Capture quality** (`capture_generator.py`) — best-of-N frame selection by Laplacian sharpness, plus a focus sweep at startup, so the saved PNG is sharp enough to read.
4. **Classify** (`llm_gemini.py`) — the crop is sent to the Gemini API with a structured-output Pydantic schema (`ai_variables.py`) that forces the model to commit to geometry before naming a numeral. Returns a real `int` value, or `null` when unsure — abstaining beats guessing.
5. **Report** (`interface.py`, `discord_webhook.py`) — tkinter window showing the roll, with optional Discord webhook post.

Accuracy on real captures runs at **~94%**, weighted to how often each face actually comes up: 96% on ordinary faces, lower on 6 and 9, where the two numerals differ only by rotation and the dot printed beside them is the only thing telling them apart.

## Requirements

- Windows (camera backend is pinned to DirectShow)
- Python 3.13, webcam, a dice tray with decent die/tray color contrast
- A Google Cloud project with Vertex AI enabled (calls go through Vertex, authenticated with your gcloud credentials)
- The [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) — it is not a pip package, so install it separately

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

That installs the vision client (`google-genai`) along with OpenCV, pydantic and the rest.

Authenticate with Google Cloud and point the app at your project:

```powershell
gcloud auth application-default login
```

The Vertex project name and location are set in `general_variables.py` (`ai_project_name`, `ai_location`) — change `ai_project_name` to your own project ID.

## Run

```powershell
python MAIN.py
```

First run walks you through setup, in this order:

1. **Outline the tray.** Click the corners of your tray in the camera window to define the region of interest — at least 3 points. `ENTER` to confirm, `z` to undo the last point, `ESC` to start the outline over.
2. **Focus sweep — die in the tray.** You'll be prompted to *place a die in the tray*, then press `ENTER`. A coarse sweep followed by a fine sweep picks the sharpest focus value and locks autofocus off.
3. **Calibration — tray empty.** You'll be prompted to *remove everything from the tray*, then press `ENTER`. Keep the tray empty and still while it measures the camera noise floor and captures the background reference.

Both prompts are on the terminal, not the camera window. Then roll the die.

The tray outline and focus value persist in `config.json` (gitignored), so later runs skip steps 1 and 2. Step 3 runs on every launch — the background reference has to be re-measured against current lighting.

## Discord

Optional — the result of each roll can be posted to a Discord channel.

Paste a channel webhook URL into the field in the app window and press **Save** (it persists to `config.json`), then press the **Off** button to flip it to **On**. Rolls are posted from that point on; a 20 and a 1 get their own emoji treatment. Leave the toggle Off and nothing is sent.

The **Reset** button clears the tray outline and focus value and exits, so the next launch walks through setup again.

## Project layout

| File | Role |
|---|---|
| `MAIN.py` | Entry point — config → geometry → calibration → detection loop |
| `camera.py` | Shared `VideoCapture`; resolution, autofocus, backend pinning |
| `settle_detector.py` | Motion-based roll/settle detection with adaptive threshold |
| `frame_initialization.py` | Polygon ROI picker, tray geometry, occupancy counting |
| `capture_generator.py` | Sharpest-frame selection, focus sweep, capture saving |
| `llm_gemini.py` | Gemini API adapter — reads the die value |
| `ai_variables.py` | Model tunables + the `DieReading` response schema |
| `general_variables.py` | Tunable constants |
| `config.py` / `config.json` | Runtime settings persistence |
| `interface.py` | tkinter UI, plus the detection worker thread that feeds it |
| `ui_vars.py` | UI grid positions |
| `discord_webhook.py` | Discord webhook posting |

## Status

Educational project (Boot.dev), in active development.

End to end and working: `python MAIN.py` runs setup, detects a settled roll, classifies it, and shows the value in the UI with optional Discord posting. Detection runs on a worker thread and hands results to the tkinter window through a queue, so the UI stays responsive between rolls.

Next up is the 6-vs-9 specialist — a second, narrower LLM pass that resolves the orientation ambiguity using the dot printed beside the numeral. It exists as `sixNineSubagent` in `llm_gemini.py` but is not yet called from the live loop. Phase 1 (d6 pip counting) worked and may return as a separate mode; the long-term plan includes multiple LLM providers and an offline k-NN classifier trained on your own rig.
