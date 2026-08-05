---
name: derive-threshold-from-data
description: Guide the user through instrumenting their code to measure real values before setting any cutoff, threshold, tolerance, or magic number — instead of guessing at one. Use this skill whenever the user asks "what should I set this to", "what value should I use", "how do I pick a threshold", or is tuning any cutoff (motion, occupancy, blur, confidence, area, aspect ratio, timing). Also trigger when a detector is over- or under-firing, when a constant stopped working after a hardware or resolution change, or when the user reports a value "seems too high/low". Never edit the user's code — describe the instrumentation and let them write it.
---

# Derive Threshold From Data

Every guessed threshold is a bug with a delay fuse. A number that works on one
camera, one lighting setup, or one screen resolution silently stops working on the
next, and the failure looks like a logic bug rather than a stale constant.

The alternative is always the same shape: **print the raw values first, look at the
two populations, then place the cutoff between them.** This skill drives that loop.

## Hard constraint: read-only

**Never edit, write, or create files in this project.** The user writes every line.
Your job is to tell them exactly what to instrument, what to look for in the output,
and how to convert what they see into a number — not to do it for them.

Describing a two-line print statement in prose is fine. Editing the file is not.

## Why guessing fails specifically

Concrete history from this project: an occupancy threshold of `500` was set by
reading printed values off one rig. It then needed re-tuning three separate times —
once when capture resolution changed (every pixel count roughly quadrupled), once
when the camera moved, and once when a differently-coloured die changed how much of
the object the mask captured. Each time, the symptom was not "the threshold is
wrong"; it was "fragments of dice are being saved as valid rolls."

A threshold derived at runtime from observed data would have survived all three.

## The loop

### 1. Instrument before changing anything

Get the raw number printing on every frame or every event. Nothing else — no
threshold, no branching, no state machine. Just the value.

If the value is expensive or noisy, print it alongside anything that helps interpret
it: a frame counter, a timestamp, the current threshold for comparison.

Tell the user what single line to add and where. Then stop and wait for numbers.

### 2. Produce both populations deliberately

One population is not enough. The user must generate *both* the case that should
fire and the case that should not, several times each:

| Measuring | Negative case | Positive case |
|---|---|---|
| motion | sit still | roll the die |
| occupancy | empty tray | die in tray |
| blur | place the die by hand and let it settle | roll it |
| area / aspect | a clean single object | two objects, or object plus shadow |

Six or more samples of each. One sample tells you nothing about spread.

Ask for the actual numbers back. Do not proceed on "it seemed higher."

### 3. Read the separation before setting anything

With both ranges in hand, the ratio between them decides what happens next:

- **Wide separation (10x or more).** Comfortable. Place the cutoff anywhere in the
  gap; the exact value barely matters.
- **Narrow separation (2-3x).** Workable but fragile. Worth improving the *measure*
  before setting a cutoff — see "when the measure is wrong" below.
- **Overlapping.** The measurement cannot distinguish the cases. No threshold will
  fix this. Change what you are measuring.

State the separation explicitly to the user. It is the single most informative
number in this whole process, and it tells them whether they are tuning or
redesigning.

### 4. Derive rather than hardcode, where possible

Prefer a value computed from observed data at runtime over a literal:

```
floor      = mean(idle_samples) + 4 * stdev(idle_samples)
threshold  = floor * k
```

The `mean + 4*stdev` form estimates a ceiling on the quiet population that one freak
sample cannot poison, unlike `max`. `k` is then the only hand-tuned number, and it
is a *ratio*, so it scales across cameras — where an additive margin would be
enormous for a quiet sensor and useless for a noisy one.

Two things to warn about:
- Discard the first 30-60 frames of any calibration. Webcams auto-adjust exposure
  and white balance on open, and those frames inflate the floor badly.
- Guard the sample count. `statistics.stdev` raises on fewer than two values, which
  happens whenever a collection loop breaks early.

### 5. Verify with a deliberate negative

A threshold is only proven by the case it is supposed to reject. After setting it,
ask for the specific test that should produce *nothing*: a hand waving outside the
region, an empty tray, a static scene left running for a minute.

If that test fires, the threshold is wrong regardless of how well the positive case
works.

## When the measure is wrong, not the threshold

If separation is poor, changing the number will not help. Consider whether the
*metric* is diluting the signal:

- **Averaging over a large region buries small objects.** A die occupying 2% of the
  measured pixels barely moves the mean. Counting *how many* pixels changed
  (`countNonZero` on a thresholded diff) preserves localized change that averaging
  destroys.
- **The region includes irrelevant area.** Restricting to a mask or tighter ROI
  raises the object's share of the measured pixels and improves separation without
  touching any constant.
- **The signal is absolute where it should be relative**, or vice versa.

Raise these as options with the tradeoff stated, and let the user choose.

## Output format

Structure the response as the stage the user is actually at:

**Stage 1 — instrument.** What line to add, where, and what to do with the program
while it runs. Then explicitly: "run it and give me the numbers."

**Stage 2 — interpret.** Once numbers arrive: state both ranges, state the
separation ratio, say whether it is comfortable/fragile/hopeless, then recommend the
cutoff and how to express it (literal, derived, or config-stored).

**Stage 3 — verify.** Name the specific negative test and what result proves it.

Never skip stage 1 and jump to a recommended value. A number produced without
measurement is the exact failure this skill exists to prevent, and offering one
teaches the habit it is trying to break.
