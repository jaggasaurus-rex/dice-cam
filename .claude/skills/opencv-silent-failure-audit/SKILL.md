---
name: opencv-silent-failure-audit
description: Audit OpenCV and camera code for calls that fail by returning junk instead of raising, and report them as findings the user fixes themselves. Use this skill whenever the user writes, pastes, or asks for review of code using cv2, VideoCapture, imread, imwrite, imencode, findContours, or camera properties — and especially when something "works but the output is wrong", an image is blank/black/None, a capture property seems ignored, or a value came back as 0 when it shouldn't have. Also trigger on "check my code", "why is this not working", or any OpenCV bug with no traceback. Report findings only — never edit the user's files.
---

# OpenCV Silent Failure Audit

OpenCV is a Python wrapper over C++. It inherits C-style error handling: on failure
it returns a sentinel value — `False`, `None`, `0`, or a dead object — rather than
raising. Python programmers reasonably expect exceptions, so these failures pass
straight through the code that should have caught them and surface much later,
somewhere unrelated, looking like a completely different bug.

This skill finds those unguarded calls and reports them.

## Hard constraint: read-only

**Never edit, write, or create files in this project.** The user is learning by
writing every line themselves. Editing the code robs them of the thing they are
here for.

Report findings with file, line number, what fails, and how it fails. Describe the
fix in prose, or show a short snippet illustrating the *pattern* — but never apply
it. If asked to "just fix it", explain that this project is set up as read-only and
offer the finding in enough detail that typing the fix is trivial.

## Why this matters more than it sounds

A real example from this project: `capture.get(cv2.CAP_PROP_FOCUS)` returned `0.0`
because the webcam driver does not expose that property for reading. That `0.0` was
passed to `capture.set(cv2.CAP_PROP_FOCUS, 0.0)`, which racked the lens to its
minimum. Every subsequent capture was unreadable — a 20x drop in image sharpness —
and nothing anywhere raised an error. The symptom appeared as "the VLM can't read my
dice", three layers away from the cause.

A single `if focus_value > 0:` guard would have caught it at the source.

## The audit checklist

Walk the code and check each of these. Report every unguarded instance.

### Returns `None` on failure

| Call | Fails when | Symptom if unguarded |
|---|---|---|
| `cv2.imread(path)` | file missing, unreadable, or an undecodable format | `None` flows into the next call; error mentions the wrong function |
| `cv2.VideoCapture(idx)` | device busy, missing, or held by another handle | constructor succeeds, object is dead — check `.isOpened()` |

Note `.webp` is commonly not decodable by default builds, and a path containing
spaces that was passed unquoted through a shell will arrive wrong.

### Returns `False` on failure

| Call | Fails when | Symptom if unguarded |
|---|---|---|
| `cv2.imwrite(path, img)` | directory missing, path invalid, bad extension | file silently never written; discovered when a folder is empty later |
| `cv2.imencode(ext, img)` | unsupported extension, bad array | `buffer` unusable; confusing error at `.tobytes()` |
| `capture.read()` | device dropped, stream ended | `frame` is `None`; `cvtColor` then throws something that reads like a codec problem |

### Returns something plausible but wrong

| Call | Fails when | Symptom if unguarded |
|---|---|---|
| `capture.set(PROP, value)` | driver ignores the request | returns `True` anyway — always read back with `.get()` and compare |
| `capture.get(PROP)` | property unsupported for reading | returns `0.0` or `-1.0`, which then gets used as a real value |

Resolution is the common case: a webcam may accept `CAP_PROP_FRAME_WIDTH = 1920`,
report success, and deliver 1280. Only a readback reveals it.

### Version-dependent return shapes

`cv2.findContours` returns **2 values in OpenCV 4.x** and **3 in 3.x**. Most
tutorials online still unpack three. If code unpacks three values, flag it — it will
raise `ValueError` on a modern install.

### Raises rather than returning — but for a surprising reason

These do throw, but the message rarely names the real problem:

- `cv2.absdiff(a, b)` — raises if shapes **or dtypes** differ. A grayscale-vs-color
  or blurred-vs-unblurred mismatch is the usual cause.
- `max(contours, key=cv2.contourArea)` — `ValueError: max() arg is an empty
  sequence` when `findContours` found nothing. Guard with `if not contours:`.
- `statistics.stdev(samples)` — `StatisticsError` on fewer than 2 samples, which
  happens when a collection loop broke early.

## Convention traps worth checking in the same pass

These produce no error at all — just wrong geometry — so they belong in this audit:

- **Slice order.** numpy is rows-then-columns: `frame[y:y+h, x:x+w]`. Reversing it
  crops the wrong region silently.
- **`.shape` order.** `(height, width)` — but `cv2.resize` takes `(width, height)`.
- **Clamp direction.** Lower bounds use `max(0, v)`, upper bounds use
  `min(limit, v)`. Swapping them is silent: an upper clamp written with `max` always
  returns the full dimension, so the crop runs to the image edge every time.
- **Color order.** `(B, G, R)`, not RGB.
- **In-place drawing.** `circle`, `polylines`, `fillPoly`, `drawContours` mutate the
  array they are given. Drawing on a frame you intend to redraw needs `.copy()`.
- **Slices are views.** `frame[a:b, c:d]` shares memory with the parent; writing to
  it modifies the original.

## Output format

Report findings ranked by severity — things that fail silently and corrupt
downstream results first, cosmetic issues last. For each:

```
N. <one-line description> (file.py:LINE)

   What fails: <the call, and the condition that makes it fail>
   How it fails: <the sentinel value returned, and where it surfaces>
   Guard: <prose description of the check, or a 2-3 line pattern>
```

Close with the count of findings and which one to fix first. If nothing is found,
say so plainly rather than inventing marginal issues — a clean audit is a useful
result.
