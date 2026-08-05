---
name: cv-pipeline-visual-debug
description: Diagnose a computer-vision pipeline that produces wrong output with no error, by dumping each intermediate stage to disk and inspecting it rather than theorizing from source code. Use this skill whenever an image pipeline "isn't working", a crop is the wrong size or region, a mask is empty or too big, a detection fires at the wrong time or not at all, contours find the wrong object, or a saved image looks blurry, blank, or wrong. Also trigger on "why is my crop weird", "the mask isn't right", or any OpenCV result that is wrong-but-not-crashing. Report findings and name the dumps to add — never edit the user's files.
---

# CV Pipeline Visual Debug

An image pipeline that throws an exception is easy. An image pipeline that runs
cleanly and produces the wrong picture is where the time goes, because the code
reads correctly and every intermediate is invisible.

The reliable move is not to reason harder about the source. It is to **write each
stage to disk and look at it.** One glance at a mask answers a question that thirty
minutes of reading the code will get wrong.

## Hard constraint: read-only

**Never edit, write, or create files in this project.** The user writes every line.

You may — and should — *read* the user's images: open their captures and debug
dumps, measure them, and report what you see. Reading their output is how this skill
works. Writing to their source files is not.

Name the dump the user should add and where. They add it, they run it, and either
they describe what they see or they point you at the file.

## Why theorizing loses

A worked example from this project. Symptom: the die was correctly positioned in the
top-left of the crop, but the crop extended far to the right and bottom.

The theory — reasoned confidently from the code — was that the object's shadow was
being merged into its contour, joined by a thin neck, and the fix was morphological
opening or a higher per-pixel threshold. Plausible, consistent with the symptom,
and completely wrong.

The actual cause was two clamp lines using `max` where they needed `min`, so the
crop's far edge was always forced to the full image dimension. It was found by
re-reading the file, not by reasoning about optics. Had the mask been dumped
first, the mask would have looked *fine* — immediately ruling out the entire shadow
theory and pointing at the crop arithmetic instead.

Dumping a stage is cheap. Being confidently wrong about a stage is expensive.

## The method

### 1. List the stages

Write out the pipeline as a chain of transformations before touching anything. For a
typical detection pipeline:

```
raw frame
  -> cropped to region
  -> grayscale
  -> blurred
  -> differenced against a reference
  -> thresholded to a binary mask
  -> masked to a polygon
  -> contours
  -> bounding box
  -> final crop
```

The bug lives at exactly one transition. The goal is to find which.

### 2. Dump every stage

`cv2.imwrite("stage_NN_name.png", img)` after each step. Binary masks save fine as
PNG — white is 255, black is 0.

Suggest a numeric prefix so the files sort in pipeline order. It makes flipping
through them in a file browser match the flow of the code.

For stages that are not images — a count, a bounding box, a contour list length —
print the value. `.shape` in particular is worth printing at every stage; a
dimension that changes when it should not, or does not change when it should, localizes
a bug instantly.

### 3. Look, and find the first wrong one

Walk forward through the dumps. The first stage that looks wrong is where the bug
is. Everything after it is downstream damage, and everything before it is fine.

This is the whole technique. Its value is that it converts "the pipeline is broken"
into "stage 6 is broken", which is usually a one-line fix.

### 4. Ask for numbers alongside images

Images answer "is this the right region". Numbers answer "is this the right size".
Both are needed, and the numbers often matter more:

- `img.shape` at each stage
- `cv2.countNonZero(mask)` for masks
- `len(contours)`, and the area of the largest
- `w / h` of a bounding box
- `cv2.Laplacian(gray, cv2.CV_64F).var()` for sharpness, when blur is suspected

A set of saved crops whose dimensions cluster into two distinct groups — some ~130px,
some ~40px — says something no single image does.

## What each stage looks like when it is wrong

| Dump | Healthy | Wrong, and what it means |
|---|---|---|
| region crop | the intended area, correct size | wrong region: slice order reversed (`[y:y+h, x:x+w]` is correct). Full-frame-sized: a clamp using `max` where `min` was needed |
| background reference | the empty scene, slightly soft | contains the object: captured at the wrong moment. All black: never assigned |
| difference | object bright, rest near-black | bright everywhere: reference is stale, or one input was blurred and the other was not |
| binary mask | clean object silhouette | speckled: per-pixel cutoff too low. Object plus a trailing blob: shadow attached. Empty: cutoff too high, or inputs identical |
| polygon mask | white shape on black, filling most of the frame | all black: points not shifted into crop-local coordinates. Shape crammed in a corner: shift applied twice or with the wrong origin |
| contour overlay | one contour around the object | many small ones: mask needs cleanup. One huge one: object merged with something adjacent |
| final crop | object filling the frame | object in one corner with space beyond: clamp arithmetic. Fragment of the object: mask only captured part of it |

## Two failure modes that look like pipeline bugs but are not

- **Insufficient resolution.** If the feature is only 15 pixels across, nothing
  downstream can recover it. Measure the object in pixels before blaming any stage.
  Check `.shape` on the saved crop, not on the upscaled version sent to a model.
- **Low contrast between object and background.** Background subtraction can only
  find what differs from the reference. A translucent object matching the surface
  colour produces a fragmentary mask, and every stage after it is doing its job
  correctly on bad input.

Both are physical problems. Name them as such rather than continuing to hunt in the
code — and note that upscaling makes an image bigger without making it more legible.

## Output format

```
Pipeline stages:
  1. <stage>  -> dump as stage_01_<name>.png
  2. <stage>  -> dump as stage_02_<name>.png
  ...

Also print: <the specific numbers worth printing, and where>

What to look for at each stage: <only the ones plausibly involved in this symptom>

Most likely stage, given the symptom: <N>, because <reasoning>
```

State the most likely stage as a *prediction to be checked*, not a conclusion. The
point of the method is that predictions from source code are often wrong — say so,
and ask for the dumps before committing to a diagnosis.
