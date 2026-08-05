---
name: python-api-explainer
description: Explain a Python or OpenCV function using the full-signature format this project requires — every argument with its default, each option broken out as an indented sub-bullet, plus a generic usage example. Use this skill whenever the user asks what a function does, how to use it, what an argument means, "break this down", "explain this more thoroughly", "remind me how X works", or says they have not seen something before. Also trigger before recommending any function the user has not used yet in this project. Explain only — never write the calling code into the user's files.
---

# Python API Explainer

The user is learning by writing every line by hand. A minimal example teaches them
one call; the full signature teaches them the whole menu, so they can choose rather
than copy. Getting this format right is the difference between the project being an
education and being dictation.

## Hard constraint: read-only

**Never edit, write, or create files in this project.** Explaining a function and
showing a generic example is the job. Putting that call into their file is not,
even when the edit is trivial and obvious.

## The required format

This format is specified in the project's `HANDOFF.md` and is not optional.

Under a `Function:` label, show the **complete signature with every argument and its
default** — not a minimal example. Then break down each token: the module, the call,
and every argument. Options and variations go in **real indented sub-bullets** at
four spaces. Never use `---` or `>` as a fake-indent prefix.

```
Function:
cv2.threshold(src, thresh, maxval, type)
    src: single-channel input image
    thresh: the cutoff value a pixel must exceed
    maxval: value written to pixels that pass
        255: standard for a binary mask
    type: comparison mode
        cv2.THRESH_BINARY: above thresh becomes maxval, else 0
        cv2.THRESH_BINARY_INV: inverted
        cv2.THRESH_OTSU: added as a flag, picks thresh automatically
    returns: (used_threshold, output_image) — usually you want index [1]
```

Then a two-sentence summary of what it is for, and one short generic example.

## What makes the breakdown useful

The signature alone is documentation, which the user could look up. The value is in
the annotations only someone who has used it would write:

**Say which option to actually pick, and why.** "`cv2.INTER_AREA` when shrinking,
`cv2.INTER_CUBIC` when enlarging" beats listing six interpolation constants
neutrally. The user is trying to make a decision.

**Flag the failure mode in the argument where it happens.** `returns: True on
success, False on failure — it does not raise, so a bad path fails silently` belongs
on the return line, not in a separate warnings section three paragraphs later.

**Name the trap.** Most functions have one thing that reliably catches people:
`cv2.mean` returning a 4-tuple when you wanted a float. `dict.update` returning
`None` so assigning its result destroys your dict. `cv2.polylines` needing a *list
of* point arrays rather than a bare array. `findContours` returning two values in
4.x and three in 3.x, which breaks most tutorials found online. If a function has
one of these, it is the most useful line in the explanation.

**Distinguish near-identical siblings.** `json.load` vs `json.loads`,
`statistics.stdev` vs `pstdev`, `cv2.boundingRect` vs `minAreaRect`, `absdiff` vs
`subtract`. Naming the sibling and the difference prevents the next bug rather than
answering the current question.

## Conventions worth restating in context

These cause real bugs in this project and are worth repeating whenever they are
relevant to the function being explained, rather than assuming they were remembered:

- numpy is rows-first — `.shape` and slicing are `(height, width)`
- OpenCV arguments are x-first — `cv2.resize` takes `(width, height)`
- colours are `(B, G, R)`, not RGB
- drawing functions mutate the array in place and return nothing useful
- slices are views into the parent array, not copies

## Scope

Explain what was asked plus the one or two things immediately adjacent to it — the
sibling function, or the argument that will be needed next. Resist expanding into a
tutorial on the surrounding topic; the user is mid-task and will ask for more if
they want it.

If the user asks about something that has already been covered in
`toolguide.md`, it is reasonable to explain it again rather than pointing at the
file. Being told to go look something up mid-task is friction, and repetition is
cheap.

## After explaining

`toolguide.md` in the project root is the accumulated reference of every function
covered so far, in exactly this format. When explaining something not yet in it,
offer to add it — but treat that file as the one exception where writing is
expected, and still ask first.
