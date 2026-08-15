# dice-cam — Handoff Summary

Status as of 2026-08-14. The 2026-08-07 summary immediately below is kept for
history; read "Status update — 2026-08-14" first, as it supersedes several of
the numbers and decisions in it.

**Where the project stands:** build-order stages 1–4 are built and working. The
program detects a settled die, confirms the tray is occupied, crops tightly to the
die, saves a sharp PNG, and — as of 2026-08-07 — **reads the number correctly**.
Gemini returned 7/7 on the clean capture set with a single call per image and
structured output. What remains is wiring the classifier into the live loop and
rebuilding the UI (stage 6).

**Two things changed materially since the last handoff, and a fresh agent should
read both before doing anything else:**

1. **The image-quality blocker is CLOSED.** Captures went from 35–363 Laplacian
   variance (unreadable mush at the low end) to 953–2119 across three fixes. See
   "Image quality — RESOLVED" below. Do not re-open this.
2. **The classifier decision changed.** Local Ollama is abandoned and deleted;
   the project is now on the **Gemini API** with a bring-your-own-key model.
   Plan A (k-NN on embeddings) is explicitly deferred, not rejected — see
   "Classifier decision — settled for now".

There is also now a `tests/` directory. It is the one place an agent may write
code (see "How to work with Tyler on this").

Sections describing design decisions still hold unless marked otherwise. Anything
marked **DONE**, **CLOSED**, or **Parked** reflects work already completed or
deliberately deferred — do not re-litigate those.

## Status update — 2026-08-14

The week's work was almost entirely on **classifier accuracy**, and it is now
measured rather than estimated. The "7/7 on the clean capture set" figure above
is obsolete — it was 7 images, hand-picked, and did not survive contact with a
real set.

### The measurement harness — BUILT, and it is the important artifact

`test_set.py` plus `test_images/` and `test_results/`. This is the thing that
makes every further decision cheap, and it should be maintained.

- `test_images/` holds **55 captures, 53 labeled**, as matched `roll_*.png` +
  `roll_*.json` sidecar pairs. The sidecar carries `bbox`, `occupancy`,
  `sharpness`, `die`, and the hand-entered `value`.
- **Labels come from the physical die at roll time, never from reading the
  image back.** This is not fussiness: two images were mislabeled by reading
  them off-screen (a 7 read as 15, a 9 read as 19) and a test set that
  certifies a wrong answer optimises everything downstream toward it.
- Two captures are deliberate negatives, labeled `"reject_reason":
  "motion_blur"` with a null value. They test the capture gate, not the model.
- `loadTestSet` → `runTestSet` → `scoreResults` / `scoreSplit` →
  `saveTestResults`. Results files carry a `summary` block first, then
  `results`; older result files are bare arrays, so loaders need
  `data["results"] if isinstance(data, dict) else data`.
- **The set is ~47% sixes and nines on purpose.** A real d20 rolls 6 or 9 on
  10% of rolls. Always score the two populations separately (`scoreSplit`) and
  weight to 90/10 before quoting a real-world number. A single blended figure
  is misleading in both directions.

### Locked-in configuration — do not drift these without a run

```
model               gemini-3.5-flash        (Vertex, location "global")
thinking_budget     2096
max_output_tokens   8196
crop                pad_ratio 0.5, centred on bbox, upscaled
specialist          OFF
temperature         0.0
```

Measured on the 53-image labeled set with this config:

```
overall (skewed set)   45/53   84.9%
non-6/9                27/28   96.4%
6/9 subset             18/25   72.0%
weighted to real rolls          ~94%
```

For contrast, the same images on whole-tray captures scored **48%**. The single
largest gain in the project was cropping.

### Why cropping mattered — the geometry failure

The dominant error mode was never OCR. Measured on whole-tray images, **73% of
wrong answers had the true value present in `other_face_numerals`** — the model
read the right numeral and assigned it to the wrong triangle. Cropping collapsed
that to near zero, because "which triangle is the top face" becomes "the one in
the middle of the picture" once the die fills the frame.

`other_face_numerals` exists to make that measurable. Keep it.

### The 6/9 wall — genuinely stuck at ~72%

Six of seven remaining 6/9 errors are **a 6 read as a 9**: a 6 that landed
rotated 180° looks exactly like a 9, and the model reads the raw glyph without
applying the dot correction. All at `high` confidence.

Things tried, all measured, none of which moved it:

- three rewrites of the dot instruction in the main prompt
- thinking budget 0, 2096, and higher
- `gemini-2.5-pro` vs `gemini-3.5-flash`
- a dedicated 6/9 sub-agent (see below)

**Do not spend more prompt iterations here.** The dot is 2–3 pixels at the
current ~95px die size. This is an optics problem — camera distance, sensor
resolution, and lighting — not a wording problem.

### The 6/9 specialist sub-agent — TRIED AND REJECTED

A second call fired when the first pass returned 6 or 9, given the first pass's
`top_face_position` and asked only to resolve orientation from the dot.
`SixNineReading` and `sixNineSubagent` remain in the code, off by default.

Across every version its flips ran **8 fixed / 7 broke** — a coin flip. The
first version was actively harmful (−4 rows).

Root cause, and it generalises: the design asked the model to "read the glyph
exactly as displayed, without rotating" and then swap if the dot was above.
**Vision models normalise orientation automatically** — step one already
contains the correction, so the swap applies it twice and inverts correct
answers. Any future design that depends on the model reporting raw,
un-normalised pixel appearance will fail the same way.

If revisited, make it a **verifier, not an overrider**: two independent reads,
`null` on disagreement. That converts coin-flips into re-rolls rather than
inversions. Adopt only if `fixed / (fixed + broke)` is clearly above 0.5 across
two or more runs.

### Prompt structure findings worth preserving

- **Pydantic field order is generation order.** The schema forces the model to
  commit to geometry before it can name a numeral —
  `die_location`, `top_face_position`, `visible_faces`, `other_face_numerals`,
  `top_face`, `value`, `confidence`. Putting `visible_faces` before
  `top_face_position` measurably reintroduces the face-selection error. Do not
  reorder these casually.
- **Prompt and input framing must match.** The instruction is written for tight
  crops. Feeding it a whole-tray image is the 48% configuration.
- The prompt is deliberately **colour-agnostic** — tray felt changed from red to
  blue mid-project and die colours vary. Never reintroduce colour as a cue.
- Naming a fallback value invites it. An early prompt produced 10 phantom `1`s;
  suppressing `1` moved the default to `17`. Fallbacks migrate — the fix is
  making `null` the sanctioned escape, not banning specific digits.

### Confidence is still not usable as a gate

Across every configuration, wrong answers come back `high` as often as correct
ones. `gemini-2.5-pro` briefly showed calibrated confidence (8 `high`, zero
wrong) but lost on accuracy and threw API nulls. **Do not gate on `confidence`
without re-measuring it first.**

`opposite_face_valid` (a face cannot be visible while its opposite, summing to
21, is on top) is the better signal: it caught the single worst error in an
early run with no false positives, though on a larger sample it runs ~70%
precision. Use it as a retry trigger, not a hard reject.

### Capture findings from the labeled set

- **The full-ROI sharpness metric is dead.** Motion-blurred rejects scored
  124–125 while good captures with the camera light off scored 62–74. An empty
  tray scored 132. A global `sharpness_floor` cannot work; score the **die bbox
  region** instead.
- **A moved tray produces a false "die".** One capture was an empty tray whose
  background reference no longer matched after the tray was bumped: occupancy
  5849, bbox `[38, 0, 197, 306]` — a tall strip on the frame edge. This is the
  same signature as the earlier 8:1 red strips, which were therefore
  background mismatch, not motion smear. Premature capture is a *separate*,
  also-real failure.
- **`validCapture` was added** — aspect ratio 0.7–1.4, occupancy 2000–8000,
  bbox not touching the frame border. It rejects both known bad-capture classes.
  `occupancy_threshold` was raised from 500 to 2000; good rolls cluster at
  3500–7300.
- A dark die in a cast shadow still under-detects (one bbox came back 52×61
  against a ~95px median). `deriveCrop` should take a `min_side` and crop
  square from the bbox centre so a partial detection still contains the die.

### Immediate next steps

1. **Production still sends the wrong image.** `mainALT2` saves the full masked
   tray; the prompt expects a crop. Wire `deriveCrop` into the live loop before
   uncommenting `readDie`, or the live path runs at 48%, not 94%.
2. Regional sharpness scoring, then gate on it in `mainALT2` (`score` is
   computed at MAIN.py:88 and discarded).
3. Self-healing background refresh on confirmed-empty settles.
4. Optics: the tray spans ~854px of a 1920px sensor. A larger die is the only
   remaining lever on 6/9 and on glare.

### Known-hard images (regression canaries)

- `roll_20260811_215752` (truth 7) — glare-blown top face, legible `15` on an
  edge face. Every model in every run answers 15. Correct answer is `null`.
- `roll_20260811_213827` (truth 14) — partial detection, 52×61 bbox.
- `roll_20260811_220200` (truth 6) / `roll_20260811_220154` (truth 9) — the
  dot cases that historically consumed the most thinking and truncated first.

## Security status — RESOLVED (verified at commit `6872ef3`)

A live Discord webhook URL had been committed to the repo. This is now handled;
recorded here so it is not re-raised as an open item.

- **Webhook rotated.** ID changed `1529286260877692978` → `1531381177993269501`
  — a genuine rotation, not a re-paste. The old URL remains in commits
  `70b6230` / `fc47143` / `53e4966`, but the endpoint is dead, so that history
  is inert. **No history rewrite is needed. Do not propose one.**
- **New URL never committed.** Verified with `git log -S` across all refs — it
  exists only in the untracked working-tree `test.py`.
- **`test.py` untracked.** `git rm --cached` was applied; it no longer appears
  in `git ls-files`.

### Hygiene item — CLOSED 2026-07-30

`__pycache__/` tracking and the `.gitignore` typo (`__pychache__/`) are both
fixed. `git check-ignore -v` confirms the rules for `test.py`, `__pycache__/`, and
`config.json` all fire, and nothing matching them appears in `git ls-files`.

Note `HANDOFF.md` is listed in `.gitignore` but is **already tracked**, so the
entry has no effect. Harmless and arguably desirable for a design doc — recorded
so it is not mistaken for a broken ignore rule.

### Forward-looking: consolidate secrets into the config file

The live webhook is currently plaintext in an untracked file, which is one
accidental `git add -f` from re-leaking. `config.json` now exists and is
gitignored, with a `webhook_url` key already present in `DEFAULTS` (currently
`None`). **Move the URL there** when `interface.py` is rewired — one gitignored
file holding all runtime settings, rather than a separate mechanism.

## How to work with Tyler on this

**This is an educational project. Do not write or edit any of the project's code —
ever, including when asked to "just fix it".** Tyler writes every line by hand;
editing for him removes the entire point. Provide guidance, design sketches,
review, diagnosis, and quick checks. Report findings with file and line number and
describe the fix in enough detail that typing it is trivial.

Three carve-outs. Two are documentation rather than code: `HANDOFF.md` and
`toolguide.md` are yours to maintain when asked. The third is **`tests/`** —
Tyler granted permission to write unit tests there on 2026-08-05, and that
permission is scoped to that directory only. Everything outside `tests/` remains
hands-off.

**Running things and measuring is encouraged.** Diagnosing by running the code,
probing the camera, calling the API, and measuring real numbers has repeatedly
been more useful than reading the source — every fix in "Image quality —
RESOLVED" came from a measurement, not an inspection. The venv interpreter is
`.venv/Scripts/python.exe`; `pytest` is installed.

Six project-scoped skills in `.claude/skills/` encode the recurring patterns from
past sessions, each with the read-only constraint built in. They should trigger on
their own; if one seems relevant and has not fired, invoke it explicitly.

| Skill | Fires on |
|---|---|
| `opencv-silent-failure-audit` | cv2 code review, "works but the output is wrong", blank images, ignored camera properties |
| `derive-threshold-from-data` | "what should I set this to", detector over/under-firing, a constant that broke after a change |
| `constant-vs-config-triage` | adding a tunable, "where should this live", "had to re-tune again" |
| `cv-pipeline-visual-debug` | wrong crop/mask/detection with no error |
| `python-api-explainer` | "explain X", "how do I use Y", or before recommending an unfamiliar function |
| `module-hygiene-check` | after splitting files, ImportError, "running the old version" |

**Re-read files from disk before reviewing them**, including files already read
earlier in the session. This has bitten before: a confident report of duplicate
functions was based on a stale copy, and Tyler had already migrated them.

Provide guidance, design sketches, review, and quick checks — do not implement
features directly.

**Response style:** concise, direct, bullet points over paragraphs, no
sycophancy. He pushed back on vagueness in a previous session and explicitly
asked for concrete code examples per step — honor that while still not
assembling the application for him.

**Working cadence:** one stage at a time, running and verifying each before
moving on. He will say "next stage" when ready. Do not run ahead.

**Syntax/guide explanations — follow this format strictly:**

- Under a `Function:` label, show the **full signature with every argument and
  its default** — not a minimal example. He wants the whole menu of options so
  he can choose.
- Then break down every token: library/module, method, each argument.
- Options and variations go in **real indented sub-bullets** (4-space indent).
  Do not use `---` as a fake-indent prefix.
- **Always close with a generic runnable usage example.** Not optional, and not
  skipped for functions that look self-evident — Tyler is a visual learner and
  has said seeing the call in use is what makes the signature click. Use
  placeholder names rather than his variables, include the imports, and show the
  **return value being used**, since that is usually the confusing part. Roughly
  3–8 lines; two examples when a flag changes the whole usage pattern.

Example:

```
Function:
ttk.Label(master, text=None, textvariable=None, font=None, relief=None)
    master: the parent container — only required positional arg
    text: the string shown on the label
        text="Score": a fixed literal string
        default None: blank unless an image is set
```

```python
import tkinter as tk
from tkinter import ttk

root = tk.Tk()
score = tk.StringVar(value="0")
label = ttk.Label(root, textvariable=score, font=("Arial", 48))
label.pack()
score.set("17")        # the label updates itself — no reconfigure needed
```

## Goal

An app that reads a **D20** roll from a webcam and reports the result
(optionally posting to Discord). Design constraint, stated explicitly:

> "Anyone could use it with any reasonable camera setup and a die."

This rules out solutions that depend on a fixed physical rig, controlled
lighting, or a specific die. One-time *in-app* setup (drag an ROI, run a
calibration wizard) is acceptable and encouraged; physical precision is not.

**Project phases:**

- **Phase 1 (working):** pip-based d6 reading. This is functional and produced
  correct counts — see "Phase 1 works" below. It is not dead code.
- **Phase 2 (current):** numeral-based dice, specifically d20.
- **Long term:** varied dice colors, types, and symbol sets.

Output channels: tkinter desktop GUI + Discord webhook post.

## Environment

- Windows, PowerShell, VS Code
- Python invoked as `python3` / `py`; `python -m pip` idiom
- Virtualenv at `.venv`, activated via `.\.venv\Scripts\Activate.ps1`
- Required `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` for activation
- Packages: `opencv-python`, `requests`, `ollama`, plus stdlib `tkinter`

## Current codebase

| File | Role | State |
|---|---|---|
| `MAIN.py` | Entry point — config → geometry → calibration → detection loop | current |
| `camera.py` | The single shared `VideoCapture`, plus resolution/focus settings | current |
| `config.py` | `CONFIG_PATH`, `DEFAULTS`, `loadConfig` / `saveConfig` / `writeEntryToConfig` | current |
| `general_variables.py` | Tunable constants (see the "hardcoded constants" note) | current |
| `frame_initialization.py` | Polygon picker (`multiPoint`, `onMouse`), `firstRunROIConfig`, `buildTrayGeometry`, `occupancyCount` | current |
| `settle_detector.py` | `frameConversion`, `frameDiff`, `cropToRoi`, `frameNoise`, `cameraCalibration`, `dieRollDetection` | current |
| `capture_generator.py` | `saveSingleFrame`, `generateAndSaveFrame`, `sharpness`, `sharpestFrame`, capture directory | current |
| `llm_gemini.py` | Gemini API adapter — reads dice correctly; needs a real `readDie(image_bytes)` signature and 429 handling | working |
| `ai_variables.py` | Model call tunables + the `DieReading` Pydantic schema | current |
| `internal_variables.py` | Holds `gemini_api_key`. **Gitignored and untracked** — verified | current, temporary |
| `tests/` | pytest suite — `conftest.py` plus 4 test modules. Agent-writable. | current |
| `interface.py` | tkinter UI — **broken by design**, still built on the deleted `pipCount` and value-change detection. Rewritten wholesale at build-order step 6 | stale |
| `discord_webhook.py` | Webhook POST (renamed from `discord.py`) | untouched |
| `ui_vars.py` | Grid coordinate constants | untouched |
| `quick_functions.py` | A `toggle` helper — unused | untouched |
| `toolguide.md` | Function reference in the `Function:` format below; now includes a Gemini API section | maintained |
| `archive/live_frame.py` | Retired Phase-1 detection code — salvage reference only | archived |
| `archive/test.py` | Scratch holding pen; **untracked** (holds the live webhook URL) | archived |
| `config.json` | Per-user runtime state — gitignored, generated | generated |
| `captures/` | Saved die crops — gitignored | generated |

`ollama_func.py` has been **deleted**. The local-VLM path is abandoned; see
"Classifier decision" below. Its `ollama.generate` entry survives in
`toolguide.md`, marked RETIRED, only for the prompt-design lessons.

**Do not import from `archive/`.** Both files run code at module scope and will
open cameras or blocking windows on import.

`live_frame.py` was retired as planned — its `findTop`, `newRollDetector`, and
whole-frame Otsu `cropFrame` are all superseded. Treat it as a salvage reference,
never a base to edit.

## Phase 1 works: d6 pip counting is functional

Important framing correction. The pip machinery is a dead end **for the D20**,
but it is a working, verified d6 feature. Do not delete it reflexively — the
likely outcome is keeping d6 as a separate mode alongside the new d20 path.
Confirm with Tyler before removing any of it.

The working pipeline: `VideoCapture(0)` → `COLOR_BGR2GRAY` → `GaussianBlur
((5,5), 0)` → `adaptiveThreshold(blockSize=41, C=8, ADAPTIVE_THRESH_GAUSSIAN_C,
THRESH_BINARY_INV)` → `SimpleBlobDetector` (minCircularity 0.8, area filtered) →
count = `len(keypoints)`.

## Key finding: the original approach was wrong for a D20

The code was built around **pip counting** (`SimpleBlobDetector`, circularity
filters, blob-count-as-value). That is D6 machinery. A D20 has printed
**numerals** on 20 triangular faces — there is nothing to count. No amount of
tuning saves that path.

Three additional structural problems identified:

1. `cropFrame` uses `max(contours, key=cv2.contourArea)` after an Otsu threshold
   on the whole frame — returns the largest bright region in the scene, which is
   the table or a highlight as often as the die. No verification it found a die.
2. Roll detection (`newRollDetector`, and `refresh` in `interface.py`) infers a
   new roll from the *value changing*. A 14 followed by another 14 is invisible,
   and any single-frame misread fires a false roll. Detection must come from
   **motion**, not value.
3. ~~`discord.py` shadows the `discord` PyPI package.~~ **RESOLVED** in commit
   `53e4966` — renamed to `discord_webhook.py` and the import in `interface.py`
   updated. Recorded because the hazard was not hypothetical: the project had
   already lost time to a local `ollama.py` shadowing the `ollama` package
   (`module has no attribute 'chat'`). Watch for the pattern recurring with new
   module names.

## Prior art: what has already been tried and rejected

**Moondream via Ollama — tried and abandoned.** Results reading d20 digits were
inconsistent and unreliable. This is *why* the code now sits on `qwen2.5vl:7b`.
Do not propose "try a small local VLM" as a fresh idea. The parked upgrade path
was a larger model (`llama3.2-vision`, ~8GB VRAM), never tested.

Debugging notes salvaged from that attempt, still useful:

- `.webp` images are not decoded — convert to `.png`/`.jpg` first
- Paths with spaces must be quoted
- `ollama.chat()` returns a response object; text is at
  `response["message"]["content"]`

## Salvage from the old pipeline: digit-handling insights

Genuinely useful work from the previous staged design, worth preserving whatever
classifier route is chosen:

- **Left-to-right ordering.** `cv2.boundingRect` per blob, then
  `sort(key=lambda b: b[0])`, so "17" does not read as "71".
- **Pad before resize.** `cv2.copyMakeBorder` to square each digit *before*
  resizing, so a narrow "1" is not stretched into distortion.
- **Uniform recognizer input.** `cv2.resize(..., (28,28),
  interpolation=cv2.INTER_AREA)` — MNIST-style sizing.
- **Known risk, unverified:** touching digits. If "1" and "7" touch,
  `findContours` returns a single blob and the split fails.

### Architectural fork — RESOLVED 2026-08-06: whole-face

Only relevant if plan A is revived; it does not affect the LLM path.

- **Per-digit:** segment individual digits, classify each as 0–9, recombine.
  Only 10 classes, but inherits the touching-digit and ordering problems above.
  **Not chosen** — at ~30 px numeral height, segmenting strokes a few pixels
  wide is far less viable than matching the face as one pattern.
- **Whole-face (CHOSEN):** classify the entire top-face crop as one of 20
  classes. Sidesteps segmentation entirely. The cost is needing coverage of all
  20 faces during calibration — a data-collection cost, not an accuracy risk.

## Agreed architecture

Three stages. Stages 1 and 2 generalize across cameras for free; stage 3 is
where the real difficulty lives.

### 1. Settle detection (camera-agnostic) — BUILT

Per-frame mean absolute difference against the previous frame, over the ROI,
normalized by frame size. When it stays under threshold for ~0.5s *after having
been above it*, the die has stopped and a new roll occurred. Emit a settle
event. The threshold should be **derived from observed noise** during the first
second of capture, not hardcoded — that is what makes it work on any webcam.

This replaces `newRollDetector` entirely and fixes both the repeated-value and
false-positive problems.

**Built and working** (`settle_detector.py`). Noise floor is `mean + 4*stdev`
over ~30 idle samples, times `error_margin` from `general_variables.py`. First
30 frames are discarded for auto-exposure settling, and exact-`0.0` diffs are
skipped as duplicate frames (the loop polls faster than the camera refreshes;
left unfiltered they pad the quiet counter and fire settles mid-bounce).

**Parked robustness upgrade — swap the mean metric for a changed-pixel count.**
`cv2.mean` averages change across the whole ROI, so a small die at distance gets
buried by the unchanged pixels around it. This showed up in testing: a hand
triggered reliably, a die did not. Tightening the ROI and lowering
`error_margin` resolved it for the current setup, but the dilution is inherent
to the metric and will resurface at longer camera distances or with smaller
dice. The more robust measure counts *how many* pixels changed rather than *how
much on average*:

```python
diff = cv2.absdiff(active, prev)
_, mask = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
changed = cv2.countNonZero(mask)
```

Localized motion survives this; averaging destroys it. It is also less sensitive
to a uniform lighting shift, which moves the mean but trips few pixels past the
per-pixel cutoff. Drop-in replacement for the body of `frameDiff` — the floor,
`error_margin`, and state machine all work unchanged, but `error_margin` needs
re-tuning because the units change from brightness-delta to pixel count.

### Parked: occupancy thresholds are hardcoded constants

The occupancy bands live in `general_variables.py` as fixed integers
(`partial_occupancy_min`, `occupancy_threshold`, `outlier_occupancy`, plus
`error_margin`, `roll_dwell`, `crop_pad`). They were picked by reading printed
values off Tyler's own rig, so they encode his camera distance, die size, and
tray. They will not transfer to another user's setup.

Two ways out, not mutually exclusive:

- **Derive them at calibration.** The settle threshold already self-tunes from
  observed noise; occupancy should do the same. Ask the user to place the die in
  the tray during calibration, measure its pixel coverage once, and set
  `occupancy_threshold` to roughly half that, `partial_occupancy_min` to a
  small fraction, and `outlier_occupancy` to ~3x. This adapts to camera
  distance and die size for free, matching how the motion threshold works.
- **Make them user-configurable.** Move them out of `general_variables.py` into
  `config.json` and expose them in a settings menu, so the numbers survive
  between sessions and can be corrected by hand when auto-derivation is off.

The right answer is probably both: auto-derive at calibration, write the result
to `config.json`, and let the settings menu override it. Note that
`general_variables.py` is the correct home for genuine constants — values Tyler
chooses and commits — whereas anything measured from a user's rig belongs in
`config.json`. These three currently sit on the wrong side of that line.

Deferred deliberately; the hardcoded values are fine for single-rig development.

### 2. Locate and crop the die — BUILT

- **One-time polygon selection**, not a rectangle drag. Most dice trays are
  hexagonal; a bounding rectangle includes the corner wedges and their tray-wall
  reflections and shadow in every measurement. `multiPoint` collects clicked
  points via `cv2.setMouseCallback`, with `z` to undo and ESC to cancel.
- **Background model of the empty tray** captured during calibration — it is the
  last frame `frameNoise` processes, already cropped/gray/blurred so it matches
  everything compared against it. Occupancy is then `absdiff` against it,
  thresholded, intersected with the polygon mask, and counted.
- **Tight crop**: `findContours` on the occupancy mask → largest by area →
  `boundingRect` → padded and clamped. Note the clamps need `max(0, ...)` for
  lower bounds and `min(shape[N], ...)` for upper; using `max` for both was a real
  bug here and produces a crop that always runs to the image edge.
- **Sanity checks are still NOT implemented.** Aspect ratio (reject `w/h` outside
  ~0.6–1.6) and contour count would catch die-plus-shadow, two dice, and the
  fragment captures described below. This is the highest-value unbuilt item in
  this stage.

### Physical constraints discovered — read before proposing image fixes

These are properties of the setup, not bugs, and they bound what any classifier
can do. Several rounds were spent rediscovering them.

**Resolution is maxed; distance is fixed.** `camera.py` requests 1920×1080 and the
readback confirms it. The camera must sit far enough back for a standard six-sided
dice tray to fit in frame, and moving closer is **not an option** — that distance
is the design target, not a temporary state. The result: a die crop is roughly
**130×130 px**, and the top-face numeral about **30 px tall**.

This matters strategically. A VLM has to *read* the numeral, which needs enough
pixels to resolve strokes. k-NN on embeddings does not read anything — it matches
whole-face appearance against examples labelled on the user's own rig, and a 30px
numeral is a perfectly distinctive pattern even when it is not legible as text. The
distance constraint therefore **strengthens the already-chosen plan A** rather than
blocking it.

**Upscaling does not add information.** `cv2.resize(..., fx=4, INTER_CUBIC)` before
the VLM call can help, because vision models tile images into patches and a small
image gets coarsely sampled. But it invents nothing. Judge sharpness on the
natively-saved PNG, never the upscaled copy.

**Autofocus must stay ON — and you must verify it took.** Locking focus was tried
and failed badly. Setting `CAP_PROP_AUTOFOCUS` to 0 does not freeze the lens where
it sits — control passes to `CAP_PROP_FOCUS`, and this webcam returns `0.0` from
`capture.get` for that property, so the "captured" value racked the lens to
minimum. Measured with Laplacian variance: **418 and 237 with autofocus on, 15.7
and 20.4 locked** — the locked images were unreadable mush.

Separately and more insidiously: for a long time the `set(CAP_PROP_AUTOFOCUS, 1)`
request was **silently ignored**. See "Image quality — RESOLVED" below. `camera.py`
now pins `CAP_DSHOW` and asserts the readback. Do not revert it to `CAP_ANY`.

A better version exists if it becomes necessary: sweep `CAP_PROP_FOCUS` across its
range, measure `cv2.Laplacian(gray, cv2.CV_64F).var()` at each step, and keep the
highest. That focuses on *die height specifically*, which autofocus cannot know to
do. Note the empty-tray calibration has nothing at die height to focus on, so this
would need the die present.

**Contrast between die and tray is a hard requirement.** A translucent die closely
matching the tray colour produced fragmentary masks — captures of 33×42 and 39×40
px, i.e. pieces of a die, saved as valid rolls. Background subtraction can only
find what differs from the reference; this is a limitation of the approach, not a
tuning problem. A "your die is too close in colour to your tray" check during
calibration would be the honest way to surface it.

### 3. Classify the numeral — the real decision

No approach is simultaneously zero-setup, general across dice, and highly
reliable. Options considered:

- **A — Few-shot calibration (RECOMMENDED).** Wizard asks the user to roll
  40–60 times. Settle detection auto-captures crops; user confirms values.
  Embed each crop with a **frozen pretrained backbone** (MobileNetV3 or
  torchvision ResNet18, ImageNet weights) and store the vectors. Runtime
  classification is **k-nearest-neighbor in embedding space** — no training
  loop, no GPU, no hyperparameters, milliseconds per call. Effectively
  rig-trained on the user's own rig.
- **B — Generic YOLO detector** trained on diverse public dice datasets
  (Roboflow has D20 sets). True zero setup, but weeks of data work and lower
  accuracy on unseen die/lighting combinations. Not chosen.
- **C — VLM.** Its genuine strength is generality: any die, any font, zero
  setup. Weakness is per-call reliability and latency. Mitigate by **voting over
  3–5 frames** captured just after settle at slightly different crops, requiring
  agreement.

**Original plan was A primary, C fallback. As of 2026-08-07 that is inverted:
C is the path being built, using a cloud model rather than a local one, and A is
deferred.** See "Classifier decision — settled for now" below for the reasoning
and the conditions under which A comes back. The rest of this section records the
design that A would use if revived — keep it.

- Launch → user drags ROI → choose "Quick start (LLM)" or "Calibrate (5 min)"
- Quick start works immediately; slower and less reliable
- Calibration uses the **LLM to pre-label** captured crops, so the user only
  corrects mistakes instead of typing 60 numbers
- After calibration, runtime switches to k-NN: fast, accurate, and offline

Rejected outright: **OCR** (Tesseract/EasyOCR). Numerals land at arbitrary
rotation and it hallucinates on 6/9/8.

## Image quality — RESOLVED 2026-08-06

Captures were blurry and inconsistent. Three separate defects, all now fixed.
Measured Laplacian variance on die crops across the three runs:

| Run | Sharpness range |
|---|---|
| Original (MSMF, single grab) | 35 – 363 — worst were unreadable |
| After backend fix | 424 – 1081 |
| After backend + best-of-N | **953 – 2119** |

**1. `CAP_ANY` resolved to MSMF, which silently dropped the autofocus request.**
`set(CAP_PROP_AUTOFOCUS, 1)` returned `True` and the readback stayed `0.0`. Same
silent-failure family as every other `cv2.set`. Measured side by side:

```
MSMF   set(AUTOFOCUS,1) -> True   get -> 0.0    set(FOURCC,MJPG) -> False
DSHOW  set(AUTOFOCUS,1) -> True   get -> 1.0    set(FOURCC,MJPG) -> True
```

`camera.py` now pins `cv2.CAP_DSHOW` and prints a warning if the readback
disagrees. **Never trust a `cv2.set` return value — assert on the readback.**

**2. A single frame was grabbed with no sharpness check.** Frame-to-frame
sharpness on a static scene varies only 1.30× (min 1355, max 1765, σ 88), but
saved captures varied 10× — so the blur was *focus drift between rolls*, not
per-frame jitter. `sharpestFrame` in `capture_generator.py` now reads 8 frames
and keeps the highest `cv2.Laplacian(gray, cv2.CV_64F).var()`, gated by
`sharpness_floor` in `general_variables.py` (currently 40).

No `sleep` is involved and none is needed: `capture.read()` blocks until the
camera delivers, so 8 back-to-back reads self-pace to ~0.36 s at 22 fps.

Sharpness is measured on the **ROI crop**, not the die crop — deliberately.
Laplacian variance measures *edge density*, not focus, so it is only a valid
focus proxy when image content is held constant. The fixed ROI holds it constant;
variable-size die crops do not. Demonstrated: a 71×86 fragment scored 1039 while
a correctly framed but soft whole-die crop scored 424.

**3. `time.strftime` collided.** One-second resolution meant rapid saves
overwrote silently. Five `saveSingleFrame` calls in a loop produced **one** file.
Now `datetime.now().strftime('%Y%m%d_%H%M%S_%f')`, and `cv2.imwrite`'s return
value is checked and raises `IOError`.

### Classifier decision — settled for now (2026-08-07)

**Ollama is abandoned.** Accuracy on d20 numerals was poor at every local model
tried; `ollama_func.py` is deleted. Do not propose a local VLM again.

**The project is on the Gemini API**, chosen over Anthropic and OpenAI for one
reason: it is the only one of the three with a **free tier that needs no credit
card and includes image input**.

**Plan A (few-shot calibration + k-NN on frozen-backbone embeddings) is deferred,
not rejected.** Tyler's stated reasoning: this is a class project, and A is "too
much fiddling and effort to be worth doing at this moment." He intends to revisit
it if development continues past submission. Do not quietly re-litigate this — but
the argument that will matter later is recorded under "Distribution" below.

Roboflow (pretrained d20 models, or pretrained data) was considered and dropped
before any code was written.

### Distribution model — bring-your-own-key

Decided while weighing whether others could use this.

- **A shipped API key is not an option.** Anything the app can read at runtime, a
  user can extract — source, config, env var, or "encrypted" (the decryption key
  ships too). It would also mean Tyler pays for every user's rolls, uncapped.
  The only alternative is hosting a backend, which is wildly disproportionate here.
- **The user pastes their own key** into a settings field. Currently the key lives
  in `internal_variables.py` (gitignored, untracked — verified with
  `git check-ignore` and `git ls-files`). That is fine for development but is a
  *source file holding a secret*, the same shape as the old `test.py` hazard.
  **It must move to `config.json` alongside `webhook_url`** when the settings
  menu is built.
- **Multiple providers** are planned via one adapter per provider
  (`llm_gemini.py`, `llm_anthropic.py`, `llm_openai.py`), each exposing an
  identical `readDie(image_array) -> DieReading`, with a dispatcher selecting on
  `cfg["llm_provider"]`. Duplicate only the adapter, never the pipeline — `MAIN.py`
  must never learn which provider is active. Only the Gemini adapter is being
  built now.
- **The long-term argument for plan A is distribution, not accuracy.** k-NN is the
  only option that is free, offline, account-free, and unlimited. A cloud-only app
  is one provider pricing change away from being unusable. That is the case to
  make if Tyler revisits this.

### Gemini specifics that cost time — read before writing API code

Full signatures are in `toolguide.md` → "Gemini API (google-genai)". The
non-obvious parts:

- **Package is `google-genai`**, imported `from google import genai`. The older
  `google-generativeai` is deprecated with a different client shape.
- **`genai.Client` is keyword-only.** `genai.Client(key)` raises
  `TypeError: Client.__init__() takes 1 positional argument but 2 were given`,
  which reads like an arity bug. `self` is positional argument 1. Must be
  `genai.Client(api_key=...)`.
- **Model IDs expire.** `gemini-2.5-flash` and `gemini-2.5-flash-lite` both went
  404 "no longer available to new users" — and both still appear in
  `models.list()`. **`models.list()` is not an availability check**; calling the
  model is. Verified working 2026-08-07: `gemini-3.6-flash`,
  `gemini-3.1-flash-lite`, `gemini-3-flash-preview`, `gemini-flash-latest`.
  `gemini-3.5-flash` returned 503 (transient overload, not a block).
- **Distinguish 404 from 503** — permanently unavailable vs. busy right now.
- **The model ID should live in `general_variables.py` or `config.json`**, not
  inline in `llm_gemini.py`, so the next expiry is a one-line change.
- **`max_output_tokens` must be generous — 2048, not 256 — because thinking
  tokens are billed against it.** This cost a debugging session on 2026-08-07 and
  presents as an image problem, which it is not. `gemini-flash-latest` resolves to
  `gemini-3.6-flash`, a **thinking model**. At `max_output_tokens=256` the
  observed run spent 243 tokens on internal reasoning, emitted 9 tokens of
  preamble, and was truncated before producing any JSON: `finish_reason`
  `MAX_TOKENS`, `response.parsed` `None`, `response.text` the fragment
  `'Here is the JSON requested:\n```'`. `thoughts_token_count` was **243 then 446
  on two runs of the same image** — it is variable and cannot be budgeted tightly.
  Note `thinking_config=types.ThinkingConfig(thinking_budget=0)` is the usual way
  to disable this and **gemini-3.6-flash rejects it with 400 INVALID_ARGUMENT** —
  headroom is the only lever.
- **When `response.parsed` is `None`, read `finish_reason` before anything else.**
  `parsed is None` alone does not distinguish truncation from a safety block from
  a schema mismatch. `response.candidates[0].finish_reason` and
  `response.usage_metadata.thoughts_token_count` separate them in two lines. A
  bare `except` around `response.parsed.value` hides all of this.
- **Free tier is 20 requests per DAY, per model** — not the ~10/minute previously
  recorded here. Verified from a live 429 on 2026-08-07: `quotaId`
  `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `quotaValue` 20. The RPM
  ceiling exists but the daily cap is hit first. Token usage is never the binding
  constraint; a die crop bills ~1110 input tokens against a 1M/minute ceiling.
- **Quota is scoped per model**, per the 429's `quotaDimensions`. A different
  model ID draws from a separate 20/day bucket, which is the escape hatch when
  one is exhausted. `gemini-flash-latest` is an alias sharing `gemini-3.6-flash`'s
  bucket — pin an explicit ID to control which bucket is drawn from. Do not mix
  results from two models in one accuracy table.
- **Distinguish per-minute from per-day 429s.** Both are HTTP 429. A
  `...PerMinute...` quota is transient and sleep-and-retry is correct; a
  `...PerDay...` quota is exhausted until midnight Pacific and retrying only
  spins. Branch on the `quotaId` substring — `break` the batch on PerDay,
  `continue` on PerMinute. Ignore the `retryDelay: 2s` field on a per-day
  violation; it is generic and misleading.
- **Tyler is on paid credits as of 2026-08-07**, so the free-tier caps above no
  longer bind day-to-day development. They are recorded because the
  bring-your-own-key distribution model means *users* will be on the free tier —
  20 rolls/day is roughly one short D&D combat. This is a real limit on the
  product, not just on development, and it strengthens the long-term argument for
  plan A recorded under "Distribution".

**Verified end to end 2026-08-07:** a real 114×109 capture, PNG bytes →
`types.Part.from_bytes` → `gemini-3.6-flash` returned a numeric answer. The
plumbing works.

### The accuracy baseline — DONE 2026-08-07: 7/7

**Result: 7 correct, 0 wrong, 0 abstain, on `gemini-3.6-flash`, single call per
image, no voting.** This measurement had been owed since the Ollama era; every
previous attempt was contaminated (early batches ~70×70 px with ~13 px numerals,
unreadable by a human reviewer too; a later batch of eight included three
fragment captures, i.e. unanswerable inputs scored as failures). These inputs
were clean and the result is trustworthy for what it covers.

**Ground truth for `captures/`, verified by Tyler 2026-08-07.** This had never
been recorded anywhere. In `sorted(glob.glob("captures/*.png"))` order:

| File | Value |
|---|---|
| `roll_20260806_173557_717511.png` | 8 |
| `roll_20260806_173601_588791.png` | 20 |
| `roll_20260806_173616_373642.png` | 13 |
| `roll_20260806_173620_181063.png` | 19 |
| `roll_20260806_173626_966083.png` | 4 |
| `roll_20260806_173630_406358.png` | 16 |
| `roll_20260806_173633_863178.png` | 20 |

**Two limits on what this proves — do not overstate it:**

- **n=7, one die, one lighting setup, one camera position.** It justifies
  proceeding on the LLM path; it does not establish a general accuracy rate.
- **6-vs-9 is UNTESTED, not solved.** No face in the sample is a bare 6 or 9
  (the values are 8, 20, 13, 19, 4, 16, 20). The ambiguity described under "Two
  constraints to design in from the start" remains entirely open, and the
  underline calibration question is still needed.

**Consequence: voting is not being built.** The handoff's standing instruction
was to measure single-call accuracy before spending request budget on 3–5 frame
voting. Measured — there is no headroom to buy. 5× the requests for 0%
improvement. Revisit only if accuracy degrades on a larger or more varied set.

Prompt-design lessons that carry over from the Ollama attempt: never give the
model a valid-looking default for failure ("if unsure, reply 20") — it makes
failures uncountable. And a model looking at a flat image has no notion of "the
top" of a die; "the face directly facing the camera, in the centre of the image"
is actionable where "the very top" is not.

Use **structured output** rather than string parsing — `response_mime_type` set
to `"application/json"` plus a Pydantic `response_schema`, read back from
`response.parsed`. Besides making abstain explicit, it returns a real `int`,
which closes the `discord_webhook.py` bug where `== 20` and `== 1` never match
against a string.

## GUI decisions already made (tkinter)

- **No always-on camera feed.** Displaying live video was debug-only and was
  deliberately removed, which drops the Pillow / BGR→RGB→PIL→Tk conversion chain
  from the runtime UI. The normal app window shows **results only**.
- **Exception — calibration.** Tyler is open to showing the camera feed *inside
  the calibration flow* if it is needed there (ROI drag, framing check, capture
  preview). It must not persist as an active window outside calibration. This
  likely means Pillow returns as a calibration-only dependency; scope it to that
  path.
- **Layout goal:** large roll number centered, quit button bottom-right.
- **Webhook URL should be read at send time** (`url_var.get()`) rather than
  cached in a module-level global, to avoid staleness after the user edits it.
- **Persisting the URL between sessions** (config file) is a known later step —
  fold it in with the ROI/calibration config file described above.
- Tkinter owns the loop: `root.after(ms, func)` with the function rescheduling
  itself. No `while True`. Do not `return` values from an `.after` callback —
  nothing catches them; write to a `StringVar` or `label.config(...)` instead.

## Two constraints to design in from the start

**Abstain over guess.** Return "unclear — reroll?" when k-NN distance is high or
frame votes disagree. 95% correct with an honest 5% "not sure" is far more
trustworthy than 97% correct with 3% confidently wrong.

**The 6 vs 9 problem.** Under free rotation they are identical. Some dice
underline one, some don't — this cannot be solved generally. Make it an explicit
calibration question ("Does your die underline the 6 and 9?"). If not, accept
ambiguity on those faces and abstain. Surface it honestly in the UI rather than
silently coin-flipping.

## Scrap / rework list

Note: `live_frame.py` is being **archived wholesale** (see above), so the
per-function notes below are about what to salvage versus abandon, not edits to
make in place.

**Abandon (do not carry into the new module):**
- `findTop` (`live_frame.py:39-62`) — counts blobs; also blocks in `imgDisplay`
  and returns nothing
- `newRollDetector` (`live_frame.py:94-104`) — value-change detection
- `demo()` in `test.py` — superseded by `interface.py`

**Do NOT delete without asking:**
- `pipCount` and the `SimpleBlobDetector` block in `test.py`. Wrong for a D20,
  but this is the working Phase 1 d6 feature. Likely becomes a separate d6 mode.
- `quick_functions.py` — `toggle` rebinds a local, return value unused;
  `interface.py` has its own inline version

**Note on `test.py` — now at `archive/test.py`, still slated for deletion.**
Tyler's stated intent: it is a holding pen for code and text he may want to reuse
elsewhere, and **the entire file will be deleted** once he is satisfied the new
detection work stands on its own. Accordingly:

- It **will not run** — it references `cv2`, `math`, `feed`, and `ollamaCall`
  without importing any of them. This is expected. Do not report it as a bug and
  do not "fix" it unprompted.
- Do not propose integrating, refactoring, or preserving it.
- Do not re-track it in git. It is untracked deliberately (it holds the live
  webhook URL).
- Treat it as read-only salvage material until Tyler nukes it.

**Rework:**
- ~~`cropFrame`~~ **DONE** — replaced by polygon ROI + background model + contour
  crop. Sanity checks still outstanding (see known bugs).
- `refresh` (`interface.py:54-72`) — drive off settle events, not value changes.
  Still outstanding; this is build-order step 6.
- ~~`ollama_func.py` prompt~~ **OBSOLETE** — file deleted; the local-VLM path is
  abandoned. The prompt-design lessons are preserved under "The measurement
  still owed" and in `toolguide.md`.

**Keep as-is:**
- `MAIN.py`, `ui_vars.py`, the tkinter layout in `interface.py`
- `fireMessage` structure — but note `pip_count` arrived as a **string** from the
  old VLM path, so the `== 20` / `== 1` comparisons in `discord_webhook.py` never
  match. Using a Pydantic `response_schema` on the Gemini call fixes this at the
  source by returning a real `int`; otherwise coerce at the classifier boundary.

**Replaced:** `ollama_func.py`'s double duty — zero-setup path *and* calibration
auto-labeler — now belongs to `llm_gemini.py`.

## Suggested build order

0. ~~**Blocker:** confirm camera position.~~ **ANSWERED 2026-07-30:** Tyler will
   set up **overhead**. Angled support is deferred to a settings-menu choice, so
   build only the overhead path and branch on `cfg["camera_mount"]` later —
   the system should not have to handle both simultaneously.
1. ~~Settle detector with adaptive threshold, in a new module~~ **DONE** —
   `settle_detector.py`
2. ~~ROI selection + config persistence~~ **DONE**, and upgraded past a
   rectangle. `cv2.selectROI` was replaced with a click-to-place **polygon**
   picker (`multiPoint` in `frame_initialization.py`, built on
   `cv2.setMouseCallback`) because most dice trays are hexagonal — a bounding
   rectangle includes the corner wedges, contributing tray-wall reflections and
   shadow to every measurement. Points are stored as `roi_points` in a
   gitignored `config.json` via `config.py` (`loadConfig` / `saveConfig` /
   `writeEntryToConfig`); `loadConfig` merges the file over `DEFAULTS.copy()`
   so configs written before a new key was added self-heal instead of
   `KeyError`-ing. The old `roi` key was dropped — `buildTrayGeometry` derives
   the bounding rect from the points with `cv2.boundingRect`, so there is one
   source of truth and the two cannot drift. It also builds a `poly_mask` via
   `cv2.fillPoly` (points shifted by the bbox origin into crop-local space),
   threaded through `frameDiff` as `cv2.mean`'s mask and intersected into the
   occupancy mask with `cv2.bitwise_and`.
3. ~~Capture script (settle → crop → save), doubling as the calibration data
   collector~~ **DONE** — `capture_generator.py`. `MAIN.py` consumes settle events
   from the `dieRollDetection` generator, measures occupancy, branches on the
   three bands, tightens the crop via contours, and saves a PNG to `captures/`.
   Note `dieRollDetection` **yields**; it originally used `return "SETTLE"`, and
   because a `for` loop over a returned string iterates its six characters, one
   roll produced six events. That symptom looked exactly like detector instability
   and cost real time — worth remembering if repeated events reappear.
4. Cloud LLM path — **WORKING.** Provider switched from Ollama to Gemini.
   Structured output is in (`DieReading` Pydantic schema in `ai_variables.py`,
   `response_mime_type="application/json"`), and the accuracy baseline is done:
   **7/7 on the clean captures.** Voting is deliberately not built — see "The
   accuracy baseline". What remains in this stage: settle on a final model ID in
   `general_variables.py`, add 429/`finish_reason` handling, and give `readDie`
   its real signature (`image_bytes` rather than a hardcoded path) so
   `llm_anthropic.py` / `llm_openai.py` can match it later.
5. ~~Embedding + k-NN classifier and the calibration wizard UI~~ **DEFERRED** —
   post-submission, if development continues. See "Classifier decision".
6. Rewire `interface.py` to consume settle events; move `webhook_url` **and the
   API key** into `config.json` and expose both in a settings menu.

Each stage is independently testable, which the original pipeline was not.

## Known bugs and unbuilt guards — current

None of these block progress. Ranked:

1. **Occupancy bands are stale — now the top defect.** `occupancy_threshold=500`,
   `partial_occupancy_min=200`, `outlier_occupancy=10000` predate the resolution
   change and the camera move. This is the third re-tune — see the "Parked:
   occupancy thresholds" section. Two distinct failure modes are getting through:
   - **Fragments.** Partial-die crops (71×86, 105×75) saved as valid rolls.
   - **Tray-moved captures.** If the tray shifts, the background model is stale
     and the tray rim against the table reads as a huge changed region. Three of
     ten captures in one run were pictures of the tray edge with **no die in them
     at all** — 3–8× the area of a die crop, ~2× the brightness, and a *low*
     Laplacian score because a plain edge has little detail. `outlier_occupancy`
     was supposed to catch exactly this and did not.
2. **Aspect-ratio and contour-count sanity checks unbuilt.** Note carefully: an
   aspect gate **would not** have caught the tray-rim captures — they land at
   0.62–0.67, inside the proposed 0.6–1.6 band. **Size is the discriminator**
   there (11k–19k px bounding-box area for a real die vs 44k–93k), not shape.
   Aspect still helps for fragments.
3. **Dead code:** `displayWindow` in `settle_detector.py`; `result = 0.0` in
   `dieRollDetection`, overwritten before it is read. `import glob` in
   `llm_gemini.py`. `generateAndSaveFrame` in `capture_generator.py` is unused
   and duplicates `saveSingleFrame`'s naming logic — fix both or delete it.
4. **`requirements.txt` is out of sync.** `google-genai` (installed, 2.17.0) is
   missing, and `ollama==0.6.2` is still listed despite the local-VLM path being
   abandoned. A fresh clone cannot run the classifier.
5. **`llm_gemini.py` runs its test call at module scope.** Importing the module
   fires an API call. **This is deliberate scaffolding, not a bug** — Tyler is
   using the file as a fast manual test harness and has asked that it not be
   flagged. It genuinely does need an `if __name__ == "__main__":` guard before
   `llm_router.py` or the tests import it; raise it *then*, at integration time,
   and not before.

**Closed since the last handoff:** `capture.release()` (now in a `try/finally` in
`MAIN.py`); unchecked `cv2.imwrite` (raises `IOError`); timestamp collision
(microsecond filenames).

## Tests

`tests/` — run with `.venv/Scripts/python.exe -m pytest tests -q`.

| File | Covers |
|---|---|
| `conftest.py` | Stubs the `camera` module in `sys.modules` so importing project code does not seize the webcam. Every other test file depends on this. |
| `test_camera_backend.py` | Hardware tests — resolution/autofocus/buffersize readbacks, the MSMF-drops-autofocus regression guard, per-frame sharpness stability, best-of-N benefit. Skips automatically with no webcam. |
| `test_capture_quality.py` | Audits `captures/*.png` for the unbuilt sanity gates (min side, aspect, sharpness floor, cross-set spread), plus save-path tests that monkeypatch the capture directory. |
| `test_geometry.py` | ROI bbox, hexagon-not-rectangle masking, mask↔crop coordinate alignment, `MAIN.py`'s crop clamps. |
| `test_settle_metric.py` | Quantifies the parked `cv2.mean` dilution — a die jumping 40 px scores *lower* than a 10-grey-level ambient shift that moved nothing. |

Two things a fresh agent should know:

- **`open_like_camera_py()` in `test_camera_backend.py` duplicates `camera.py`'s
  construction and must be kept in sync.** It already went stale once.
- **Failing tests are currently expected.** The capture-quality tests fail on the
  fragment and tray-rim captures by design — they encode the gates that are not
  built yet. Do not "fix" them by loosening thresholds.
- Thresholds in `test_capture_quality.py` (`SHARPNESS_FLOOR`, `MIN_SIDE`) are
  rig-specific and derived from small samples. The hardcoded ROI hexagon in
  `test_geometry.py` will go stale if the tray is re-picked.

## Open threads

- ~~`__pycache__/` tracked in git, `.gitignore` typo~~ **CLOSED** — typo fixed,
  nothing matching `__pycache__`/`config.json`/`test.py` appears in
  `git ls-files`, and `git check-ignore -v` confirms all three rules fire.
- ~~Camera position~~ **CLOSED** — overhead; see build order step 0.
- ~~Per-digit vs. whole-face classification~~ **RESOLVED: whole-face.** At 30 px,
  segmenting individual digits is far less viable than matching the face as one
  pattern, and it sidesteps the touching-digit risk. Only matters if plan A is
  revived; it does not affect the LLM path, which reads whatever crop it is given.
- **Rotation is the unrecorded landmine in plan A.** ImageNet-style embeddings are
  not rotation-invariant, and a D20 face lands at arbitrary rotation. Measured on
  real captures with a normalized-pixel proxy: the *same* face rotated 90° sat at
  distance 87.5 while a *different* face sat at 83.5 — nearest-neighbour picks the
  wrong one. The fix is cheap and must be designed in from the start: augment each
  labelled crop through ~12 rotations at calibration, so one roll becomes twelve
  reference vectors. Two consequences — 60 random rolls will not evenly cover 20
  faces, so the wizard must *track coverage* rather than count to 60; and rotation
  augmentation makes 6-vs-9 strictly worse (rotating a "6" 180° manufactures a "9"
  labelled "6"), which promotes the underline question from nicety to load-bearing.
- Whether d6 pip mode is kept alongside d20 — assumed yes, not confirmed. The pip
  code now lives only in `archive/test.py`, which is untracked; if that mode is
  wanted, the `SimpleBlobDetector` block needs rescuing before the file is deleted.
- ~~A clean accuracy baseline~~ **CLOSED 2026-08-07 — 7/7.** See "The accuracy
  baseline".
- ~~Ground truth for `captures/`~~ **CLOSED** — recorded in the table under "The
  accuracy baseline". It lives in this file rather than beside the captures; move
  it to `captures/ground_truth.md` if the set grows.
- **A larger and more varied accuracy set.** The 7/7 is one die, one lighting
  setup, one camera position, and contains no bare 6 or 9. The useful next
  measurement is a set that deliberately includes 6, 9, and a second die colour.
- Tyler was offered, and has not yet taken up, a detailed sketch of either the
  calibration flow's state machine or the settle detector's adaptive threshold
  logic.
- **Calibration is accumulating jobs.** It currently measures the noise floor and
  captures the background. Proposed additions, all wanting the die present in the
  tray: derive the occupancy bands, lock focus by sharpness sweep, check die/tray
  colour contrast, and ask the 6-vs-9 underline question. Worth designing as one
  coherent flow rather than bolting each on separately.
