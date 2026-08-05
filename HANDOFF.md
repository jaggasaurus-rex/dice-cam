# dice-cam — Handoff Summary

Status as of 2026-08-04.

**Where the project stands:** build-order stages 1–3 are built and working. The
program detects a settled die, confirms the tray is occupied, crops tightly to the
die, and saves a PNG. What it cannot yet do is read the number. Stage 4 (the VLM
path) is in progress and currently blocked on image quality — see "Physical
constraints discovered" below, which is the most important new section for a fresh
agent to read.

Sections describing design decisions still hold unless marked otherwise. Anything
marked **DONE**, **CLOSED**, or **Parked** reflects work already completed or
deliberately deferred — do not re-litigate those.

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

Two carve-outs, both documentation rather than code: `HANDOFF.md` and
`toolguide.md` are yours to maintain when asked.

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

Example:

```
Function:
ttk.Label(master, text=None, textvariable=None, font=None, relief=None)
    master: the parent container — only required positional arg
    text: the string shown on the label
        text="Score": a fixed literal string
        default None: blank unless an image is set
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
| `capture_generator.py` | `saveSingleFrame`, `grabProcessedFrame`, capture directory | current |
| `ollama_func.py` | VLM call (`qwen2.5vl:7b`) — being tested, not yet wired into `MAIN.py` | in progress |
| `interface.py` | tkinter UI — **broken by design**, still built on the deleted `pipCount` and value-change detection. Rewritten wholesale at build-order step 6 | stale |
| `discord_webhook.py` | Webhook POST (renamed from `discord.py`) | untouched |
| `ui_vars.py` | Grid coordinate constants | untouched |
| `quick_functions.py` | A `toggle` helper — unused | untouched |
| `toolguide.md` | 63-entry reference of every function used, in the `Function:` format below | maintained |
| `archive/live_frame.py` | Retired Phase-1 detection code — salvage reference only | archived |
| `archive/test.py` | Scratch holding pen; **untracked** (holds the live webhook URL) | archived |
| `config.json` | Per-user runtime state — gitignored, generated | generated |
| `captures/` | Saved die crops — gitignored | generated |

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

### Unresolved architectural fork — decide before building stage 5 (k-NN)

These two routes are incompatible and a new agent should not silently assume
either:

- **Per-digit:** segment individual digits, classify each as 0–9, recombine.
  Only 10 classes, but inherits the touching-digit and ordering problems above.
- **Whole-face:** classify the entire top-face crop as one of 20 classes. This
  is what the k-NN plan below assumes. Sidesteps segmentation entirely, but
  needs coverage of all 20 faces during calibration.

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

**Autofocus must stay ON.** Locking focus was tried and failed badly. Setting
`CAP_PROP_AUTOFOCUS` to 0 does not freeze the lens where it sits — control passes
to `CAP_PROP_FOCUS`, and this webcam returns `0.0` from `capture.get` for that
property, so the "captured" value racked the lens to minimum. Measured with
Laplacian variance: **418 and 237 with autofocus on, 15.7 and 20.4 locked** — the
locked images were unreadable mush. If focus locking is revisited, guard with
`if focus_value > 0:` and verify with the sharpness metric.

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
- **C — VLM** (the existing `ollama_func.py`). Its genuine strength is
  generality: any die, any font, zero setup. Weakness is per-call reliability
  and latency. Mitigate by **voting over 3–5 frames** captured just after
  settle at slightly different crops, requiring agreement.

**Chosen plan: A as the primary path, C as the zero-setup fallback.**

- Launch → user drags ROI → choose "Quick start (VLM)" or "Calibrate (5 min)"
- Quick start works immediately; slower and less reliable
- Calibration uses the **VLM to pre-label** captured crops, so the user only
  corrects mistakes instead of typing 60 numbers
- After calibration, runtime switches to k-NN: fast and accurate

Rejected outright: **OCR** (Tesseract/EasyOCR). Numerals land at arbitrary
rotation and it hallucinates on 6/9/8.

#### VLM path — results so far (stage 4, in progress)

`ollama_func.py` now takes a **numpy array**, upscales it, encodes to JPEG, and
calls `ollama.generate`. The prompt was fixed to reply `UNKNOWN` on failure rather
than the old "reply 20", which had made failures indistinguishable from real
answers and therefore uncountable. Output is coerced with `int()` inside a
`try/except ValueError`, and an unparseable reply becomes an abstain.

**Accuracy so far is poor**, but no clean measurement exists yet. The tests run to
date were contaminated:

- The first batch was ~70×70 px per die — numerals ~13 px, unreadable by a human
  reviewer too.
- A later batch of eight included three fragment captures from the translucent die,
  i.e. three unanswerable inputs counted as failures.
- Some reads came from *side* faces, which is partly resolution and partly that a
  model looking at a flat image has no notion of "the top". Prompt wording like
  "the face directly facing the camera, in the centre of the image" is actionable
  where "the very top" is not.

**The measurement still owed:** run the VLM against ~10 sharp, whole-die captures
of the opaque die and record **correct / wrong / UNKNOWN separately**. Count 6-vs-9
confusions separately again, since the handoff already treats those as unsolvable
in general and they should not count against the model the way a 14-read-as-4 does.

Only after that number exists is it worth deciding whether to build the 3–5 frame
voting layer, or to treat C as a weak fallback and move effort to A.

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
- ~~`ollama_func.py` prompt~~ **DONE** — now replies `UNKNOWN` on failure.

**Keep as-is:**
- `MAIN.py`, `ui_vars.py`, the tkinter layout in `interface.py`
- `fireMessage` structure — but note `pip_count` arrives as a **string** from the
  VLM path, so the `== 20` / `== 1` comparisons in `discord.py` currently never
  match. Coerce to `int` at the classifier boundary.

**Promoted, not sidelined:** `ollama_func.py` serves double duty as the
zero-setup path *and* the calibration auto-labeler.

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
4. VLM voting path — **IN PROGRESS.** Single-call path works; see "VLM path —
   results so far" above. Blocked on getting a clean accuracy baseline before
   building the voting layer.
5. Embedding + k-NN classifier and the calibration wizard UI
6. Rewire `interface.py` to consume settle events, and move `webhook_url` into
   `config.json`

Each stage is independently testable, which the original pipeline was not.

## Known bugs and unbuilt guards — current

None of these block progress; all were identified and left. Ranked:

1. **Occupancy bands are stale.** `occupancy_threshold=500`, `partial_occupancy_min=200`,
   `outlier_occupancy=10000` were tuned before the resolution change and before the
   camera moved. Pixel counts roughly quadrupled, so fragments now pass as valid
   rolls. Re-derive from printed values before trusting any capture set. This is
   the third re-tune — see the "Parked: occupancy thresholds" section.
2. **Aspect-ratio and contour-count sanity checks unbuilt.** Would catch the
   fragments, die-plus-shadow, and two-dice cases as honest abstains.
3. **`capture.release()` is never called.** `MAIN.py` has no `try/finally`, so the
   camera stays held after an exception or Ctrl+C, and the next run may fail to
   open it.
4. **`cv2.imwrite` return value unchecked** in `capture_generator.py`. It returns
   `False` rather than raising, so a bad path loses captures silently.
5. **Timestamp collision.** `time.strftime('%Y%m%d_%H%M%S')` has one-second
   resolution; two captures in the same second overwrite silently. Matters during
   a 40–60 roll calibration collection.
6. **Dead code:** `displayWindow` in `settle_detector.py`; `result = 0.0` in
   `dieRollDetection`, overwritten before it is read.

## Open threads

- ~~`__pycache__/` tracked in git, `.gitignore` typo~~ **CLOSED** — typo fixed,
  nothing matching `__pycache__`/`config.json`/`test.py` appears in
  `git ls-files`, and `git check-ignore -v` confirms all three rules fire.
- ~~Camera position~~ **CLOSED** — overhead; see build order step 0.
- **Per-digit vs. whole-face classification — fork still not decided.** Note it
  does not block stage 4: a VLM reads whatever crop it is given. It must be decided
  before stage 5. The physical constraints above argue for whole-face — at 30px,
  segmenting individual digits is far less viable than matching the face as a
  single pattern.
- Whether d6 pip mode is kept alongside d20 — assumed yes, not confirmed. The pip
  code now lives only in `archive/test.py`, which is untracked; if that mode is
  wanted, the `SimpleBlobDetector` block needs rescuing before the file is deleted.
- **A clean VLM accuracy baseline** on sharp whole-die captures — the immediate
  next measurement, described under "VLM path — results so far".
- Tyler was offered, and has not yet taken up, a detailed sketch of either the
  calibration flow's state machine or the settle detector's adaptive threshold
  logic.
- **Calibration is accumulating jobs.** It currently measures the noise floor and
  captures the background. Proposed additions, all wanting the die present in the
  tray: derive the occupancy bands, lock focus by sharpness sweep, check die/tray
  colour contrast, and ask the 6-vs-9 underline question. Worth designing as one
  coherent flow rather than bolting each on separately.
