# dice-cam — Handoff Summary

Status as of 2026-07-27. No code has been changed yet. Everything below is a
design decision reached in discussion; the implementation is still to be written.

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

### Remaining hygiene item (not a security issue)

`__pycache__/` is still tracked — all seven `.pyc` files appear in
`git ls-files`, including stale `discord.cpython-313.pyc` and
`frame_processing.cpython-313.pyc` from modules that no longer exist. Two
stacked causes:

1. **Typo in `.gitignore:2`** — reads `__pychache__/` (the `a` and `c` are
   transposed). `git check-ignore` confirms nothing is being ignored.
2. Already-tracked files are unaffected by `.gitignore` regardless, so it also
   needs `git rm -r --cached __pycache__`.

No secrets involved — just repo noise.

### Forward-looking: consolidate secrets into the config file

The live webhook is currently plaintext in an untracked file, which is one
accidental `git add -f` from re-leaking. The design already calls for a config
file to persist ROI and calibration data — **put the webhook URL there too**.
One gitignored `config.json` holding all runtime settings, rather than a
separate mechanism. Fold this into the config-persistence step.

## How to work with Tyler on this

Tyler writes the code by hand. Provide guidance, design sketches, review, and
quick checks — do not implement features directly unless explicitly asked.

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

| File | Role |
|---|---|
| `MAIN.py` | Entry point, calls `userWindow()` |
| `interface.py` | tkinter UI, polling loop, Discord toggle |
| `live_frame.py` | OpenCV capture, crop, threshold, roll detection |
| `ollama_func.py` | VLM call (`qwen2.5vl:7b` via ollama) |
| `discord_webhook.py` | Webhook POST (renamed from `discord.py`) |
| `ui_vars.py` | Grid coordinate constants |
| `quick_functions.py` | A `toggle` helper |
| `test.py` | Scratch — old tkinter demo + dead pip-counting code |

### `live_frame.py` is being retired

Tyler's decision: `live_frame.py` outgrew its original scope and now holds code
unlikely to survive the redesign. He plans to **archive the file and start fresh
in a new module** when he begins the new detection work. Do not plan
refactors-in-place against it — treat the design below as specifying a new file,
and treat `live_frame.py` as a reference to salvage from, not a base to edit.

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

### Unresolved architectural fork — decide before building stage 3

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

### 1. Settle detection (camera-agnostic — plan is settled)

Per-frame mean absolute difference against the previous frame, over the ROI,
normalized by frame size. When it stays under threshold for ~0.5s *after having
been above it*, the die has stopped and a new roll occurred. Emit a settle
event. The threshold should be **derived from observed noise** during the first
second of capture, not hardcoded — that is what makes it work on any webcam.

This replaces `newRollDetector` entirely and fixes both the repeated-value and
false-positive problems.

### 2. Locate and crop the die

- **One-time user ROI drag** (`cv2.selectROI` or a tkinter canvas), saved to a
  config file. One click-and-drag on first launch — not a rig requirement — and
  it eliminates the "largest contour in the whole scene" failure mode.
- Capture a **background model of the empty table** during calibration, then
  background-subtract rather than Otsu-thresholding the world.
- Sanity-check the resulting blob's area and aspect ratio before accepting it.

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

## Open question — camera position (still unanswered)

Whether the camera is mounted **overhead or at an angle** was asked twice in a
previous session and never confirmed. It materially affects top-face isolation,
crop geometry, and how much foreshortening the classifier must tolerate.
**Ask Tyler before building stage 2.**

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

**Note on `test.py` — temporary, and slated for deletion.** Tyler's stated
intent: it is a holding pen for code and text he may want to reuse elsewhere,
and **the entire file will be deleted** once he is satisfied the new detection
work stands on its own. Accordingly:

- It **will not run** — it references `cv2`, `math`, `feed`, and `ollamaCall`
  without importing any of them. This is expected. Do not report it as a bug and
  do not "fix" it unprompted.
- Do not propose integrating, refactoring, or preserving it.
- Do not re-track it in git. It is untracked deliberately (it holds the live
  webhook URL).
- Treat it as read-only salvage material until Tyler nukes it.

**Rework:**
- `cropFrame` — user ROI + calibration-time background model + sanity checks
- `refresh` (`interface.py:54-72`) — drive off settle events, not value changes
- `ollama_func.py` prompt — currently says "if it's a non-number symbol reply
  20", which silently masks failures. Should reply `UNKNOWN` so failures can be
  detected and counted.

**Keep as-is:**
- `MAIN.py`, `ui_vars.py`, the tkinter layout in `interface.py`
- `fireMessage` structure — but note `pip_count` arrives as a **string** from the
  VLM path, so the `== 20` / `== 1` comparisons in `discord.py` currently never
  match. Coerce to `int` at the classifier boundary.

**Promoted, not sidelined:** `ollama_func.py` serves double duty as the
zero-setup path *and* the calibration auto-labeler.

## Suggested build order

0. **Blocker:** confirm camera position (overhead vs. angled). The webhook
   security item is already closed — see top of document.
1. Settle detector with adaptive threshold, in a new module
2. ROI selection + config persistence
3. Capture script (settle → crop → save), which doubles as the calibration
   data collector
4. VLM voting path — gives a working end-to-end product
5. Embedding + k-NN classifier and the calibration wizard UI
6. Rewire `interface.py` to consume settle events

Each stage is independently testable, which the current pipeline is not.

## Open threads

- `__pycache__/` tracked in git, with stale entries, and a `.gitignore` typo
  (`__pychache__/`) — hygiene only
- Camera position (overhead vs. angled) — unconfirmed, blocks stage 2/3 design
- Per-digit vs. whole-face classification — fork not yet decided
- Whether d6 pip mode is kept alongside d20 — assumed yes, not confirmed
- Tyler was offered, and has not yet taken up, a detailed sketch of either the
  calibration flow's state machine or the settle detector's adaptive threshold
  logic
