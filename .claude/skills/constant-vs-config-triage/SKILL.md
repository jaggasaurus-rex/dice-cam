---
name: constant-vs-config-triage
description: Decide whether a tunable value belongs in general_variables.py as a committed constant, in config.json as per-user runtime state, or should be derived at calibration — and flag values currently sitting in the wrong place. Use this skill whenever the user adds or changes a tunable number (threshold, margin, dwell, padding, cutoff, band, timeout), asks "where should this live", says a constant "needed re-tuning again", or is about to hardcode a value measured from their own camera or rig. Also trigger when a value broke after a hardware, resolution, or environment change. Report the triage — never edit the user's files.
---

# Constant vs Config Triage

Values that look identical in source — both are just numbers with names — behave
completely differently depending on where they came from. A number the developer
*chose* is a constant. A number *measured from a particular machine* is user data
that happens to be typed as a literal, and it will be wrong on every other machine.

Getting this wrong is not a style issue. It is the reason a working program fails
for its second user.

## Hard constraint: read-only

**Never edit, write, or create files in this project.** The user writes every line.
Deliver the triage as a table plus reasoning, so acting on it is mechanical.

## The test

Ask one question about each value:

> **Did a human choose this number, or did a measurement produce it?**

- **Chosen** — a design decision. Lives in `general_variables.py`, gets committed,
  changes only when the design changes. Example: how many consecutive frames of
  motion should count as "a roll has started". That is a judgement about behaviour,
  and it is the same judgement on every machine.

- **Measured** — an observation about one physical setup. Belongs in `config.json`,
  gitignored, and ideally is not typed by a human at all but written by a
  calibration step. Example: how many pixels a die covers. That depends on camera
  distance, sensor resolution, die size, and tray colour.

A useful second question when the first is ambiguous: **if a stranger downloaded
this program, would this number still be right?** If no, it is config.

## The tell that a value is misfiled

A constant that needs re-tuning after an environment change was never a constant.

Real history from this project: `occupancy_threshold`, `partial_occupancy_min`, and
`outlier_occupancy` were re-tuned three times — after a capture-resolution change,
after moving the camera, and after trying a differently-coloured die. Three
re-tunes is not bad luck; it is the value announcing what it actually is. Each of
those three lives in `general_variables.py` alongside genuine constants, which is
why the problem kept recurring rather than being fixed once.

When the user reports "I had to change that number again", say so directly. The
re-tune is the diagnosis.

## Three destinations, not two

**1. `general_variables.py` — committed constants.**
Design decisions. Same for every user. Safe in version control.

**2. `config.json` — per-user runtime state.**
Measured from a rig, written by the program, gitignored. Reached through
`loadConfig()` / `saveConfig()` / `writeEntryToConfig()`.

Two properties of the existing config layer worth reminding the user about, because
they change what is safe to do:
- `loadConfig` merges the file over `DEFAULTS.copy()`, so adding a new key does not
  break configs written before it existed — the missing key picks up its default
  instead of raising `KeyError`.
- Adding a key to `DEFAULTS` with value `None` gives you a working "not configured
  yet" signal for free, which is how first-run prompts are triggered.

**3. Derived at calibration — the best answer for measured values.**
Rather than asking the user to type a measured number at all, compute it at startup
from observed data and write the result to `config.json`. The motion threshold in
this project already works this way: it is measured from observed noise on every
launch, which is precisely why it survived every change that broke the occupancy
bands.

When a value is measured, always raise derivation as the option before settling for
"put it in config.json". Config-with-a-settings-menu is the fallback for when
derivation is unreliable, and the two combine well: derive automatically, store the
result, let a settings menu override it.

## Borderline cases

Some values genuinely sit on the line. Name the tension rather than forcing a call:

- **A ratio applied to a measured value** (`error_margin`, multiplied against a
  measured noise floor) is a constant, because the scaling with the environment is
  already handled by the thing it multiplies. This is the reason multiplicative
  margins travel between cameras and additive ones do not.
- **Padding in pixels** (`crop_pad`) is measured-ish — 10px means something
  different at 640x480 than at 1920x1080. Either express it as a fraction of the
  object size, or accept it as config.
- **Durations in seconds** (`roll_dwell`) are usually genuine constants: how long a
  die must be still before you believe it has stopped is physics plus judgement, not
  a property of the camera. Note the contrast with frame *counts*, which are
  framerate-dependent and therefore rig-dependent.

## Output format

Produce a table, then the reasoning for anything non-obvious:

```
| Value | Currently in | Belongs in | Why |
|---|---|---|---|
| roll_dwell | general_variables.py | correct as-is | judgement about physics, framerate-independent |
| occupancy_threshold | general_variables.py | derived at calibration | measured pixel count; re-tuned 3x |
```

Then, for each value in the wrong place, one short paragraph on what specifically
will break and when — "this fails the first time someone with a different camera
runs it" is more actionable than "this is bad practice."

Close with the single highest-value move, since a full migration is rarely worth
doing at once.
