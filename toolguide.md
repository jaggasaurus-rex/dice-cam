# dice-cam — Tool Guide

Reference for every function used or discussed while building the settle
detector, ROI/polygon selection, and config persistence. Signatures show every
argument with its default so the whole menu of options is visible.

Conventions that bite repeatedly, stated once:

- **numpy is rows-first** — `.shape` and slicing are `(height, width)`.
- **OpenCV arguments are x-first** — `cv2.circle` centers, `cv2.resize` sizes,
  `cv2.selectROI` returns. Mixing the two is the most common source of
  "why is my image sideways" bugs.
- **Colors are `(B, G, R)`**, not RGB. `(0, 255, 0)` is green.
- **Drawing functions modify the image in place** and return nothing useful.

---

## Camera capture

### cv2.VideoCapture

```
Function:
cv2.VideoCapture(index, apiPreference=cv2.CAP_ANY)
    index: which camera device
        0: first/built-in webcam
        1, 2...: additional cameras
    apiPreference: which backend to use
        default cv2.CAP_ANY: let OpenCV choose
        cv2.CAP_DSHOW: DirectShow on Windows — usually opens faster and is
            less noisy than MSMF
        cv2.CAP_MSMF: Media Foundation — the Windows default, source of the
            "async ReadSample() call is failed" warnings
    returns: a VideoCapture object — never raises, even on failure
```

Opens a camera and holds the handle for the life of the object. Create exactly
one per device in one place; two objects on the same camera put it into a broken
state on Windows rather than failing cleanly.

```python
capture = cv2.VideoCapture(0, apiPreference=cv2.CAP_ANY)
```

### capture.isOpened

```
Function:
capture.isOpened()
    takes no arguments
    returns: True if the device opened successfully
```

The correct check after constructing a `VideoCapture`, since the constructor
never raises and hands back a dead object instead. Without it, failure surfaces
much later as a confusing read error.

```python
if not capture.isOpened():
    raise Exception("Could not open camera")
```

### capture.read

```
Function:
capture.read(image=None)
    image: optional preallocated output array — normally omitted
    returns: (ret, frame)
        ret: bool — False means the grab failed
        frame: BGR uint8 array of shape (height, width, 3), or None on failure
```

Grabs the next frame. Always check `ret` before touching `frame` — passing
`None` into `cvtColor` throws an error that reads like a codec problem rather
than "the camera dropped".

```python
ret, frame = capture.read()
if ret is False:
    raise Exception("Camera read error")
```

### capture.set / capture.get

```
Function:
capture.set(propId, value)
    propId: which property to change
        cv2.CAP_PROP_FRAME_WIDTH / cv2.CAP_PROP_FRAME_HEIGHT: resolution
        cv2.CAP_PROP_FPS: frame rate
        cv2.CAP_PROP_AUTOFOCUS: 1 enables, 0 disables
        cv2.CAP_PROP_FOCUS: manual focus position, driver-dependent scale
        cv2.CAP_PROP_EXPOSURE / cv2.CAP_PROP_GAIN: exposure controls
    value: the requested value
    returns: True/False — but drivers frequently return True and then
        ignore the request entirely

capture.get(propId)
    propId: the property to read
    returns: the current value as a float
        0.0 or -1.0 when the driver does not expose that property —
        NOT an error, just an unusable number
```

Requests a camera setting, which the driver may silently decline. Always read the
value back and print it; a webcam that advertises 1080p may deliver 720p, and a
property that returns `0.0` means "unsupported", not "zero".

```python
capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
print(capture.get(cv2.CAP_PROP_FRAME_WIDTH), capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
```

Worth knowing about focus specifically: setting `CAP_PROP_AUTOFOCUS` to 0 does not
freeze the lens where it currently sits. Control passes to `CAP_PROP_FOCUS`, which
may be at a default far from your subject. Reading the focus value first only works
if the driver exposes it — guard with `if focus_value > 0:` before setting it, or a
returned `0.0` will rack the lens to its minimum and every frame afterward will be
unusable.

### capture.release

```
Function:
capture.release()
    takes no arguments
    returns: None
```

Frees the camera handle so other processes — including your next run — can open
it. Best placed in a `finally` block so it runs even when the program exits by
exception.

```python
try:
    main()
finally:
    capture.release()
    cv2.destroyAllWindows()
```

---

## Frame preparation

### cv2.cvtColor

```
Function:
cv2.cvtColor(src, code, dst=None, dstCn=0)
    src: input image
    code: the conversion to perform
        cv2.COLOR_BGR2GRAY: 3 channels to 1
        cv2.COLOR_GRAY2BGR: 1 to 3, for drawing color annotations on a mask
        cv2.COLOR_BGR2RGB: for handing an image to PIL/tkinter
    dst: optional output array
    dstCn: channels in the output — 0 means derive from code
    returns: the converted image (a NEW array)
```

Converts between color spaces; grayscale conversion cuts the data to a third and
stops auto-white-balance shifts from registering as motion. Because it allocates
a new array, it also sidesteps the capture-buffer reuse problem when storing a
previous frame.

```python
gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
```

### cv2.GaussianBlur

```
Function:
cv2.GaussianBlur(src, ksize, sigmaX, dst=None, sigmaY=0, borderType=cv2.BORDER_DEFAULT)
    src: input image
    ksize: kernel size as a (width, height) tuple
        must be ODD numbers — (5,5), (7,7)
        larger = more smoothing, more detail lost
    sigmaX: standard deviation in X
        0: computed automatically from ksize — the usual choice
    sigmaY: standard deviation in Y
        0: same as sigmaX
    borderType: how edge pixels are extrapolated
    returns: the blurred image
```

Damps per-pixel sensor grain, which lowers the idle noise floor and widens the
gap between "still" and "moving". Apply it consistently — comparing a blurred
frame to an unblurred one produces a large false difference everywhere.

```python
blur = cv2.GaussianBlur(gray, (5, 5), 0)
```

### cv2.resize

```
Function:
cv2.resize(src, dsize, dst=None, fx=0, fy=0, interpolation=cv2.INTER_LINEAR)
    src: input image
    dsize: target size as (WIDTH, HEIGHT) — x-first, unlike .shape
        pass None to size by scale factors instead
    fx, fy: scale factors, used when dsize is None
    interpolation: resampling method
        cv2.INTER_AREA: best for shrinking
        cv2.INTER_LINEAR: default, good for enlarging
        cv2.INTER_NEAREST: fastest, blocky
    returns: the resized image
```

Rescales an image to fixed dimensions, needed to give a classifier uniform
input. Note `dsize` is `(width, height)` while `.shape` reports
`(height, width)`.

```python
small = cv2.resize(die_crop, (28, 28), interpolation=cv2.INTER_AREA)
```

---

## Measuring change

### cv2.absdiff

```
Function:
cv2.absdiff(src1, src2, dst=None)
    src1: first image
    src2: second image — must match src1 in shape AND dtype
        mismatches raise cv2.error
    dst: optional output array
    returns: per-pixel |src1 - src2|
```

Gives the magnitude of change between two images without caring which direction
it went. The absolute value is why shadows (darker) and bright objects both show
up — use `cv2.subtract` when you need only one direction.

```python
diff = cv2.absdiff(current_frame, prev)
```

### cv2.subtract

```
Function:
cv2.subtract(src1, src2, dst=None, mask=None, dtype=-1)
    src1, src2: same-size images
    mask: optional — only masked pixels are computed
    dtype: output depth, -1 means same as inputs
    returns: src1 - src2, SATURATED at 0 (negatives clamp to zero,
        they do not wrap around)
```

A signed difference that keeps only "brighter than" and discards "darker than".
Useful for isolating a light die from its own shadow, which is always darker
than the background.

```python
brighter_only = cv2.subtract(processed_frame, background)
```

### cv2.mean

```
Function:
cv2.mean(src, mask=None)
    src: input array
    mask: uint8 array — only non-zero pixels are averaged
        None: the whole image
        a polygon mask: restricts the average to that region, and divides
            by the masked pixel count, so normalization is automatic
    returns: a 4-tuple, one entry per channel — grayscale uses index [0]
```

Collapses an image to a single average value, turning a whole diff into one
comparable number. Forgetting the `[0]` yields a confusing tuple rather than a
float.

```python
result = cv2.mean(diff, mask=poly_mask)[0]
```

### cv2.threshold

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
        cv2.THRESH_OTSU: added as a flag — picks thresh automatically from
            the image histogram; pass thresh=0 when using it
    returns: (used_threshold, output_image) — you usually want index [1]
```

Converts a grayscale image into a black-and-white mask by a single cutoff. Note
it is `threshold` with one `h`, unlike the `threshhold` variables in this
project.

```python
_, mask = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
```

### cv2.adaptiveThreshold

```
Function:
cv2.adaptiveThreshold(src, maxValue, adaptiveMethod, thresholdType, blockSize, C, dst=None)
    src: single-channel 8-bit image
    maxValue: value assigned to passing pixels, typically 255
    adaptiveMethod: how the local threshold is computed
        cv2.ADAPTIVE_THRESH_MEAN_C: mean of the neighborhood
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C: Gaussian-weighted mean
    thresholdType: cv2.THRESH_BINARY or cv2.THRESH_BINARY_INV
    blockSize: neighborhood size in pixels — must be ODD and > 1
    C: constant subtracted from the computed mean; higher = stricter
    returns: the thresholded image (single return value, not a tuple)
```

Computes a separate threshold for every local neighborhood, so it survives
uneven lighting across the frame where a global threshold fails. Unlike
`cv2.threshold` it returns just the image, with no tuple to unpack.

```python
bw = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                           cv2.THRESH_BINARY_INV, 41, 8)
```

### cv2.countNonZero

```
Function:
cv2.countNonZero(src)
    src: single-channel array
    returns: int count of non-zero pixels
```

Counts *how many* pixels changed rather than *how much on average*, which
preserves the signal from small localized objects that averaging buries. Has no
`mask` parameter, so intersect with `cv2.bitwise_and` first to restrict it.

```python
occupied = cv2.countNonZero(mask)
```

### cv2.bitwise_and

```
Function:
cv2.bitwise_and(src1, src2, dst=None, mask=None)
    src1, src2: same-size arrays
    dst: optional output array
    mask: optional additional region restriction
    returns: per-pixel AND — a pixel survives only if set in BOTH inputs
```

With one 0/255 mask this means "keep only what lies inside the mask region".
The standard way to restrict a binary result to a polygon before counting or
finding contours.

```python
changed = cv2.bitwise_and(changed, poly_mask)
```

### cv2.bitwise_not

```
Function:
cv2.bitwise_not(src, dst=None, mask=None)
    src: input array
    returns: per-pixel inversion — 0 becomes 255, 255 becomes 0
```

Flips a binary mask, used when a threshold produced white-on-black but the rest
of the pipeline expects black-on-white. A quick fix when more than half the
image came out white.

```python
if cv2.countNonZero(bw) > bw.size / 2:
    bw = cv2.bitwise_not(bw)
```

---

## Shape cleanup and analysis

### cv2.getStructuringElement

```
Function:
cv2.getStructuringElement(shape, ksize, anchor=(-1,-1))
    shape: the kernel form
        cv2.MORPH_ELLIPSE: rounded — best for organic/real-world blobs
        cv2.MORPH_RECT: square
        cv2.MORPH_CROSS: plus-shaped
    ksize: (width, height) tuple — larger removes more
    anchor: kernel origin, (-1,-1) means center
    returns: a uint8 kernel array
```

Builds the kernel that morphological operations use to decide what counts as
"small". Size is the main knob — too small leaves noise, too large starts eating
the object you want.

```python
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
```

### cv2.morphologyEx

```
Function:
cv2.morphologyEx(src, op, kernel, dst=None, anchor=(-1,-1), iterations=1,
                 borderType=cv2.BORDER_CONSTANT, borderValue=None)
    src: binary or grayscale image
    op: the operation
        cv2.MORPH_OPEN: erode then dilate — removes small specks, and severs
            thin necks such as a shadow joined to an object
        cv2.MORPH_CLOSE: dilate then erode — fills small holes
        cv2.MORPH_GRADIENT: outline of shapes
    kernel: from getStructuringElement, or np.ones((5,5), np.uint8)
    iterations: how many times to repeat
    returns: the processed image
```

Cleans up a raw thresholded mask, which is always speckly. Opening is the usual
choice for motion/occupancy masks because it removes noise without shrinking the
main blob.

```python
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
```

### cv2.findContours

```
Function:
cv2.findContours(image, mode, method, contours=None, hierarchy=None, offset=None)
    image: 8-bit single-channel binary image; non-zero is foreground
    mode: which contours to retrieve
        cv2.RETR_EXTERNAL: outermost only — ignores holes such as the numerals
            printed inside a die outline
        cv2.RETR_LIST: all contours, flat, no hierarchy
        cv2.RETR_TREE: all contours plus full nesting information
    method: how much of each contour to store
        cv2.CHAIN_APPROX_SIMPLE: collapses straight runs to endpoints
        cv2.CHAIN_APPROX_NONE: every boundary pixel
    offset: shifts all returned points by this amount
    returns (OpenCV 4.x): (contours, hierarchy)
        contours: list of (N,1,2) int arrays
        NOTE: OpenCV 3.x returned THREE values — most online examples
        unpack three and will raise ValueError on 4.x
```

Traces the outlines of white regions in a binary image so they can be measured
individually. Only trustworthy when the input mask contains just what you care
about — running it on a whole-scene threshold returns the table as often as the
subject.

```python
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
```

### cv2.contourArea

```
Function:
cv2.contourArea(contour, oriented=False)
    contour: a single contour from findContours
    oriented: signed vs unsigned
        False: absolute pixel area — the normal choice
        True: signed, negative for clockwise contours
    returns: float area
```

Measures how many pixels a contour encloses, most often as the `key` for picking
the largest blob. Combine with a minimum area to reject noise contours outright.

```python
die = max(contours, key=cv2.contourArea)
```

### cv2.boundingRect

```
Function:
cv2.boundingRect(array)
    array: a contour, or any (N,1,2)/(N,2) int32 point array
    returns: (x, y, w, h) — the smallest UPRIGHT rectangle containing it
```

Converts a contour or point list into a plain rectangle suitable for slicing.
"Upright" means it never rotates to fit a tilted object — use `cv2.minAreaRect`
for that.

```python
x, y, w, h = cv2.boundingRect(np.array(points, dtype=np.int32))
```

### cv2.minAreaRect

```
Function:
cv2.minAreaRect(points)
    points: a contour or point array
    returns: ((center_x, center_y), (width, height), angle_degrees)
        NOT the (x, y, w, h) format of boundingRect
        cv2.boxPoints(rect) converts it to four corner points
```

Finds the smallest rotated rectangle around a shape, which fits tilted objects
far more tightly than an upright box. Its return format differs from
`boundingRect`, so it cannot be dropped in as a replacement.

```python
rect = cv2.minAreaRect(die)
box = np.int32(cv2.boxPoints(rect))
```

### cv2.moments

```
Function:
cv2.moments(array, binaryImage=False)
    array: a contour or a single-channel image
    binaryImage: treat all non-zero pixels as 1
    returns: a dict of moment values
        m00: the area
        m10, m01: first-order moments; centroid is m10/m00, m01/m00
```

Produces statistical descriptors of a shape, most commonly used to find its
centroid. Always guard against `m00 == 0`, which happens for degenerate contours
and would otherwise divide by zero.

```python
M = cv2.moments(c)
if M["m00"] != 0:
    cx, cy = M["m10"] / M["m00"], M["m01"] / M["m00"]
```

---

## Windows, input, and drawing

### cv2.imshow

```
Function:
cv2.imshow(winname, mat)
    winname: window title — also the handle used by setMouseCallback
        and destroyWindow, so keep it consistent
    mat: the image to display
    returns: None
```

Displays an image in a named window, creating the window if it does not exist.
Nothing actually appears until `cv2.waitKey` runs.

```python
cv2.imshow("dice cam", display)
```

### cv2.waitKey

```
Function:
cv2.waitKey(delay)
    delay: milliseconds to wait for a keypress
        0: block forever until a key is pressed
        1: wait ~1ms then continue — use inside a live loop
    returns: the key code, or -1 if no key was pressed
```

Pumps OpenCV's event queue — without it, windows never repaint and mouse
callbacks never fire. Mask with `& 0xFF` to strip platform-specific high bits
before comparing to a key code.

```python
key = cv2.waitKey(1) & 0xFF
if key == 27:      # ESC
    return None
```

Key codes seen in this project: `13` ENTER, `27` ESC, `32` SPACE, `8` BACKSPACE.
For printable keys use `ord('q')` instead.

### cv2.namedWindow

```
Function:
cv2.namedWindow(winname, flags=cv2.WINDOW_AUTOSIZE)
    winname: the window title/handle
    flags: window behavior
        cv2.WINDOW_AUTOSIZE: fixed to image size, not user-resizable
        cv2.WINDOW_NORMAL: user-resizable
    returns: None
```

Creates a window explicitly, before any image is ready to show. Needed because
`setMouseCallback` requires the window to already exist.

```python
cv2.namedWindow("dice cam")
```

### cv2.destroyWindow / cv2.destroyAllWindows

```
Function:
cv2.destroyWindow(winname)
    winname: which window to close
    returns: None

cv2.destroyAllWindows()
    takes no arguments
    returns: None
```

Closes OpenCV windows, which do not clean themselves up — `selectROI` in
particular leaves its window on screen after returning. Call the targeted
version when other windows should survive.

```python
cv2.destroyWindow("Calibration Window")
```

### cv2.selectROI

```
Function:
cv2.selectROI(windowName, img, showCrosshair=True, fromCenter=False)
    windowName: title of the popup
    img: a single still frame to drag on — not a live feed
    showCrosshair: draws crosshair guides while dragging
    fromCenter: drag anchor
        False: corner-to-corner — the expected behavior
        True: outward from the center point
    returns: (x, y, w, h) ints
        ENTER or SPACE confirms; C cancels and returns (0, 0, 0, 0)
    blocks until confirmed or cancelled
```

Built-in rectangle picker for one-time setup, saving the need to write a drag
UI. Only does rectangles — anything else needs a custom mouse-callback loop.

```python
roi = cv2.selectROI("Calibration Window", frame, showCrosshair=True, fromCenter=False)
if roi[2] == 0 or roi[3] == 0:
    return None
```

### cv2.setMouseCallback

```
Function:
cv2.setMouseCallback(windowName, onMouse, param=None)
    windowName: must name an EXISTING window
    onMouse: callback with the fixed signature (event, x, y, flags, param)
    param: any object passed through to the callback — pass a mutable
        list to collect results without needing a global
    returns: None
```

Registers a mouse handler on a window; register once, before the display loop.
Events only reach the callback while a `waitKey` loop is running.

```python
points = []
cv2.namedWindow("dice cam")
cv2.setMouseCallback("dice cam", onMouse, param=points)

def onMouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        param.append([x, y])
```

Event constants: `cv2.EVENT_LBUTTONDOWN`, `EVENT_LBUTTONUP`,
`EVENT_RBUTTONDOWN`, `EVENT_MOUSEMOVE`.

### cv2.circle

```
Function:
cv2.circle(img, center, radius, color, thickness=1, lineType=cv2.LINE_8, shift=0)
    img: drawn on IN PLACE — no return value
    center: (x, y) tuple — x first
    radius: in pixels
    color: (B, G, R) tuple
    thickness: outline width
        -1 or cv2.FILLED: solid fill
    lineType: cv2.LINE_AA for antialiasing
    returns: the image (but it was modified in place anyway)
```

Draws a marker, typically to show a placed point. Because it mutates the array,
draw onto a per-frame copy so an undo can actually erase it.

```python
cv2.circle(display, tuple(p), 4, (0, 255, 0), -1)
```

### cv2.polylines

```
Function:
cv2.polylines(img, pts, isClosed, color, thickness=1, lineType=cv2.LINE_8, shift=0)
    img: drawn on in place
    pts: a LIST of point arrays — the wrapper is required even for one
    isClosed: join the last point back to the first
        False: open chain — good while placing points
        True: closed shape — previews the finished polygon
    color: (B, G, R)
    thickness: line width in pixels
```

Draws connected line segments between points, giving live feedback during
polygon selection. Passing a bare array instead of a list of arrays fails with
an unhelpful error.

```python
cv2.polylines(display, [np.array(points, dtype=np.int32)], False, (0, 255, 0), 2)
```

### cv2.fillPoly

```
Function:
cv2.fillPoly(img, pts, color, lineType=cv2.LINE_8, shift=0, offset=None)
    img: drawn on in place
    pts: a LIST of int32 point arrays — same wrapper rule as polylines
    color: 255 for a single-channel mask (white = included)
    offset: shifts all points before drawing
```

Fills a polygon solid, which is how an arbitrary shape becomes a usable mask.
Points must be in the coordinate space of the target image — subtract the crop
origin when filling a mask sized to a bounding rectangle.

```python
poly_mask = np.zeros((h, w), dtype=np.uint8)
cv2.fillPoly(poly_mask, [pts - [x, y]], 255)
```

### cv2.drawContours

```
Function:
cv2.drawContours(image, contours, contourIdx, color, thickness=1,
                 lineType=cv2.LINE_8, hierarchy=None, maxLevel=INT_MAX, offset=None)
    image: drawn on in place
    contours: the list returned by findContours
    contourIdx: which one to draw
        -1: all of them
    color: (B, G, R)
    thickness: -1 fills the contour solid
```

Overlays detected contours for visual debugging, usually on a color copy of the
mask. Filling with `thickness=-1` turns contours back into a mask.

```python
vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
cv2.drawContours(vis, contours, -1, (0, 255, 0), 2)
```

### cv2.imread

```
Function:
cv2.imread(filename, flags=cv2.IMREAD_COLOR)
    filename: path to the image file
    flags: how to load it
        cv2.IMREAD_COLOR: 3-channel BGR, drops any alpha — the default
        cv2.IMREAD_GRAYSCALE: single channel
        cv2.IMREAD_UNCHANGED: keeps the alpha channel if present
    returns: a numpy array, or None if the file is missing or undecodable
        NOTE: returns None rather than raising — the same silent-failure
        pattern as imwrite
```

Loads an image file from disk into an array. A path string is not an image — any
function expecting pixel data needs `imread` first, and forgetting that step
produces errors naming the *next* function rather than this one.

```python
img = cv2.imread(path)
if img is None:
    raise Exception(f"Could not read {path}")
```

### cv2.imwrite

```
Function:
cv2.imwrite(filename, img, params=None)
    filename: output path — the EXTENSION decides the format
        ".png": lossless, larger — correct for training/classifier data
        ".jpg": lossy — compression artifacts pollute embeddings
    img: the array to write
    params: format options, e.g. [cv2.IMWRITE_PNG_COMPRESSION, 3]
    returns: True on success, False on failure
        NOTE: it returns False rather than raising, so a bad directory
        fails silently
```

Writes an image to disk, the main tool for both saving captures and dumping
debug masks. Always check the return value, since silent failure is the default.

```python
if not cv2.imwrite(file_location, die_crop):
    print("WARNING: failed to write", file_location)
```

### cv2.imencode

```
Function:
cv2.imencode(ext, img, params=None)
    ext: format extension INCLUDING the dot — ".png", ".jpg"
        ".png": lossless, larger payload
        ".jpg": smaller and faster to transmit
    img: the numpy array to encode
    params: format options, e.g. [cv2.IMWRITE_JPEG_QUALITY, 90]
    returns: (success, buffer)
        success: bool
        buffer: a numpy array of encoded bytes — call .tobytes() on it
```

The in-memory twin of `imwrite`: same encoding, no disk. Needed when handing an
image to an API that wants file bytes rather than an array, such as a vision model.

```python
success, buffer = cv2.imencode('.jpg', img)
if not success:
    raise Exception("Failed to encode image")
image_bytes = buffer.tobytes()
```

If the image is already a file on disk, skip this entirely — `open(path, "rb").read()`
gives you the same bytes without decoding and re-encoding.

---

## Image quality

### cv2.Laplacian

```
Function:
cv2.Laplacian(src, ddepth, dst=None, ksize=1, scale=1, delta=0,
              borderType=cv2.BORDER_DEFAULT)
    src: input image, normally grayscale
    ddepth: output depth
        cv2.CV_64F: required so negative gradients are not clipped to 0
        using an unsigned type here silently halves the measured detail
    ksize: aperture size, must be odd
    scale, delta: optional scaling applied to the result
    returns: an image of second derivatives — high where edges are sharp
```

Measures edge intensity, and `.var()` on the result collapses it to a single
sharpness score. This is the standard blur metric: high variance means crisp edges,
low means smooth or out of focus.

```python
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
```

Only meaningful as a *comparison* between images of the same scene — there is no
absolute "sharp" value. In this project, autofocus-on captures scored 418 and 237
while focus-locked ones scored 15.7 and 20.4, which settled the question
immediately. Measure the natively-saved image, not an upscaled copy: interpolation
smooths edges and drags the score down regardless of the true focus.

---

## numpy

### np.zeros

```
Function:
np.zeros(shape, dtype=float)
    shape: tuple of dimensions — (h, w) for a single-channel image,
        height first to match .shape ordering
    dtype: element type
        np.uint8: REQUIRED for an OpenCV mask
        default float64 will be rejected by mask parameters
    returns: an array filled with 0
```

Creates a blank canvas, most often an all-black mask about to be filled. Getting
`dtype` wrong produces errors deep inside OpenCV rather than at the call site.

```python
poly_mask = np.zeros((h, w), dtype=np.uint8)
```

### np.array

```
Function:
np.array(object, dtype=None, copy=True, order='K', subok=False, ndmin=0)
    object: a list, tuple, or nested sequence to convert
    dtype: element type
        np.int32: required by OpenCV geometry functions
        np.uint8: image data
        None: inferred, which gives int64 on 64-bit Windows and is
            silently rejected by contour functions
    copy: whether to copy the input data
    returns: a numpy array
```

Converts Python lists into the typed arrays OpenCV requires. Always state
`dtype` explicitly for point data — the inferred default is the wrong width.

```python
pts = np.array(cfg["roi_points"], dtype=np.int32)
```

### .shape / .size

```
Attribute:
array.shape
    a tuple of dimension sizes — NOT a method, no parentheses
        [0]: height (rows)
        [1]: width (columns)
        [2]: channels — present only on color images

array.size
    total number of elements — height * width * channels
```

Reports the dimensions of an array, used for bounds-clamping crops and for
telling color from grayscale. `len(frame)` returns only the row count, which is
rarely what you want.

```python
y2 = min(roi_crop.shape[0], y + h + crop_pad)
x2 = min(roi_crop.shape[1], x + w + crop_pad)
```

### ndarray.copy

```
Function:
array.copy(order='C')
    order: memory layout of the copy — leave default
    returns: an independent array with its own memory
```

Produces a real duplicate, needed because slices are views and OpenCV's drawing
functions mutate in place. Drawing onto a shared array makes marks permanent, so an
undo can remove a point from your list while its dot stays on screen.

```python
while True:
    display = frame.copy()      # fresh canvas every iteration
    for p in points:
        cv2.circle(display, tuple(p), 4, (0, 255, 0), -1)
```

Distinct from `dict.copy()` despite the identical name — and note that
`cvtColor`, `absdiff`, and `resize` all allocate new arrays anyway, so results from
those are already independent.

### Array slicing

```
Syntax:
array[row_start:row_end, col_start:col_end]
    rows correspond to y, columns to x — the reverse of (x, y, w, h)
    negative indices count from the END rather than erroring, so an
        unclamped negative silently crops the wrong region
    returns: a VIEW into the original array, not a copy
```

Crops an image to a rectangle. Because it returns a view, drawing on the result
also modifies the parent array — use `.copy()` when that matters.

```python
def cropToRoi(frame, roi):
    x, y, w, h = roi
    return frame[y:y+h, x:x+w]
```

---

## Config persistence

### json.load / json.loads

```
Function:
json.load(fp)
    fp: an OPEN FILE OBJECT, not a path string
        passing a string raises AttributeError: 'str' has no attribute 'read'
    returns: the parsed Python object
        raises json.JSONDecodeError on malformed content

json.loads(s)
    s: a JSON string already in memory
    returns: the parsed Python object
```

Parses JSON into Python objects, translating `null`/`true` into `None`/`True`.
The trailing `s` in `loads` means "string", the single most common mix-up
between the two.

```python
with open(CONFIG_PATH, "r") as f:
    cfg.update(json.load(f))
```

### json.dump

```
Function:
json.dump(obj, fp, indent=None, sort_keys=False, default=None)
    obj: the object to serialize — dicts, lists, str, int, float, bool, None
        tuples are written as arrays and come back as LISTS
        numpy int64 raises "Object of type int64 is not JSON serializable"
    fp: an open file object in write mode
    indent: pretty-printing
        None: one long line
        2 or 4: human-readable and diff-friendly
    sort_keys: alphabetize keys for stable output
    returns: None
```

Serializes a dict to a file, the write half of config persistence. Convert numpy
values to plain `int` first, since the error only appears at save time and not
where the value originated.

```python
with open(CONFIG_PATH, "w") as f:
    json.dump(cfg, f, indent=4, sort_keys=True)
```

### dict.get

```
Function:
dict.get(key, default=None)
    key: the key to look up
    default: returned when the key is absent
    returns: the value or the default — never raises KeyError
```

Reads a key that may not exist, so a missing config field becomes a usable
"not set yet" signal instead of a crash. Essential once configs written by older
versions of the code are in circulation.

```python
if cfg.get(entry_name) is not None:
    ...
```

### dict.update

```
Function:
dict.update(other)
    other: another dict, or an iterable of key/value pairs
    effect: copies other's keys in, IN PLACE
        keys in both: other's value WINS
        keys only in self: untouched
    returns: None — assigning the result gives you None
```

Layers one dict over another; starting from defaults and updating with the file
means missing keys self-heal while user settings still win. The more specific
source must always be the one passed to `update`.

```python
cfg = DEFAULTS.copy()
cfg.update(json.load(f))
```

### dict.copy

```
Function:
dict.copy()
    takes no arguments
    returns: a SHALLOW copy — nested dicts/lists are still shared
```

Prevents callers from mutating a module-level defaults dict through the value
they were handed. Shallow is sufficient for flat configs but not once values are
themselves dicts.

```python
return DEFAULTS.copy()
```

---

## Paths and files

### os.path.abspath / dirname / basename / join

```
Function:
os.path.abspath(path)
    resolves a relative path against the CWD; does not require existence
    returns: absolute normalized path string

os.path.dirname(path)
    returns: everything before the last separator
        "config.py" -> "" — which is why abspath comes first

os.path.basename(path)
    returns: the last component only

os.path.join(path, *paths)
    joins components with the OS-correct separator
    WARNING: an absolute later component discards everything before it
```

Composed together, these anchor a file path to the source file's own directory
rather than the working directory. A bare `"config.json"` resolves against
wherever the user launched from, silently creating a second file.

```python
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
```

### os.path.exists / isfile / isdir

```
Function:
os.path.exists(path)
    returns: True for a file OR a directory

os.path.isfile(path)
    returns: True only for a regular file

os.path.isdir(path)
    returns: True only for a directory
```

Tests for presence before reading or writing. `isfile` is the precise choice for
a config check, since it also rules out a directory accidentally created with
the same name.

```python
if not os.path.isfile(CONFIG_PATH):
    saveConfig(DEFAULTS)
```

### os.makedirs

```
Function:
os.makedirs(name, mode=0o777, exist_ok=False)
    name: directory path, including any intermediate directories
    mode: permission bits — ignored on Windows
    exist_ok: behavior when it already exists
        False: raises FileExistsError
        True: silently succeeds — required to call it on every run
    returns: None
```

Creates a directory tree for output files. It makes *directories* — pointing it
at a filename creates a folder with that name, which then breaks every attempt
to open that path as a file.

```python
os.makedirs(capture_directory, exist_ok=True)
```

### open

```
Function:
open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None)
    file: path string or Path object
    mode: how to open it
        "r": read text
        "w": write text, TRUNCATING any existing content
        "a": append
        "rb"/"wb": binary variants
    encoding: text codec — "utf-8" is worth stating explicitly on Windows,
        where the default is the system codepage
    returns: a file object
```

Opens a file for reading or writing; always use it as a `with` block so the
handle closes even when an exception is raised mid-parse. Mode `"w"` truncates
immediately, which is correct when rewriting a whole config.

```python
with open(CONFIG_PATH, "w") as f:
    json.dump(cfg, f, indent=4)
```

### glob.glob

```
Function:
glob.glob(pathname, *, root_dir=None, dir_fd=None, recursive=False,
          include_hidden=False)
    pathname: the wildcard pattern to match
        "*": any run of characters within one path component
        "?": exactly one character
        "[0-9]": one character from the set
        "**": recursive descent — only when recursive=True
    root_dir: directory the pattern is relative to
        None: the current working directory
    recursive: enables "**"
    returns: a LIST of matching path strings
        order is arbitrary, NOT alphabetical
        an empty list if nothing matches — it does not raise
```

Finds files by wildcard, the programmatic form of `dir *.png`. An empty result looks
identical to a working script that found nothing, so anchor the pattern to a known
directory rather than relying on the working directory.

```python
for path in sorted(glob.glob(os.path.join(CAPTURE_DIR, "*.png"))):
    img = cv2.imread(path)
```

The `pathlib` equivalent is a method on the directory: `Path(CAPTURE_DIR).glob("*.png")`.

### pathlib.Path

```
Function:
Path(*pathsegments)
    .resolve(): absolute path, also resolving symlinks
    .parent: the containing directory
    / operator: joins path components
    .exists() / .is_file() / .is_dir(): presence tests
    .read_text() / .write_text(): whole-file IO in one call
    accepted directly by open() and the json module
```

The object-oriented alternative to `os.path`, doing the same work with less
nesting. Pick one style per file rather than mixing them.

```python
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
```

---

## Statistics and timing

### statistics.mean / stdev / pstdev

```
Function:
statistics.mean(data)
    data: any iterable of numbers
    returns: the arithmetic mean
        raises StatisticsError on an empty input

statistics.stdev(data, xbar=None)
    data: needs AT LEAST 2 values or it raises StatisticsError
    xbar: precomputed mean, if already known
    returns: SAMPLE standard deviation (n-1 denominator)

statistics.pstdev(data, mu=None)
    returns: POPULATION standard deviation (n denominator)
```

`mean + 4 * stdev` estimates a ceiling on idle noise that ignores a single freak
sample, unlike `max`. Guard the sample count, since a short calibration run
raises rather than returning something usable.

```python
floor = statistics.mean(samples) + 4 * statistics.stdev(samples)
```

### time.time / time.monotonic

```
Function:
time.time()
    takes no arguments
    returns: seconds since the Unix epoch, as a float
        can jump backwards if the system clock is adjusted (NTP, DST)

time.monotonic()
    takes no arguments
    returns: seconds from an undefined origin, as a float
        guaranteed never to go backwards
        only meaningful as a difference between two calls
```

Used to measure how long a condition has held — the dwell that distinguishes a
settled die from a momentary pause mid-bounce. Timestamps keep the dwell at a
fixed duration regardless of framerate, unlike counting frames.

```python
if time.monotonic() - quiet_since >= roll_dwell:
    yield "SETTLE"
```

### time.strftime

```
Function:
time.strftime(format, t=None)
    format: a format string
        %Y year, %m month, %d day, %H hour, %M minute, %S second
        one-second resolution — two calls in the same second collide
    t: a time tuple; defaults to now
    returns: the formatted string
```

Builds timestamped filenames that sort chronologically. **One-second resolution
is not enough for capture filenames** — see the next entry. Superseded in
`capture_generator.py` for exactly that reason.

```python
file_name = f"roll_{time.strftime('%Y%m%d_%H%M%S')}.png"   # collides
```

### datetime.datetime.now / .strftime

```
Function:
datetime.datetime.now(tz=None)
    tz: timezone to express the result in
        default None: naive local time — correct for filename labels
    returns: a datetime object

Function:
datetime.datetime.strftime(format)
    format: the same directives time.strftime takes, plus one more
        %f: microseconds, zero-padded to 6 digits — the field time.strftime lacks
    returns: the formatted string
```

The fix for timestamp collisions. `time.strftime` has **no sub-second directive
at all**, so there is nothing to widen — you need a different clock. A measured
demonstration: five `saveSingleFrame` calls in a loop under `%H%M%S` produced
**one** file, because each write silently overwrote the last. Under `%f`, five.

Import it one way and stay consistent — `import datetime` then
`datetime.datetime.now()`, or `from datetime import datetime` then
`datetime.now()`. The doubled name catches people out.

```python
stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
file_name = f"roll_{stamp}.png"
```

---

## Python builtins worth noting

### max / min with key

```
Function:
max(iterable, *, key=None, default=...)
    iterable: the sequence to search
    key: a function applied to each item; the comparison uses its result
    default: returned for an empty iterable
        without it, an empty sequence raises ValueError
    returns: the largest item ITSELF, not the key value

min(iterable, *, key=None, default=...)
    same, returning the smallest
```

`max(..., key=...)` picks the biggest contour by area; the two-argument form
`max(0, v)` and `min(limit, v)` clamp a value into range. Clamping a crop needs
`max` for the lower bound and `min` for the upper — swapping them silently
produces a full-size crop.

```python
die = max(contours, key=cv2.contourArea)
x1 = max(0, x - crop_pad)
x2 = min(roi_crop.shape[1], x + w + crop_pad)
```

### sorted

```
Function:
sorted(iterable, *, key=None, reverse=False)
    iterable: any sequence
    key: a function applied to each item; sorting uses its result
    reverse: descending order when True
    returns: a NEW list — the original is unchanged
        contrast with list.sort(), which sorts in place and returns None
```

Puts an iterable into a predictable order, which matters for anything whose order is
undefined — `glob.glob` results, dictionary iteration, set contents. Timestamped
filenames in `YYYYMMDD_HHMMSS` form sort chronologically under a plain alphabetical
sort, which is the reason to name files that way.

```python
for path in sorted(glob.glob("captures/*.png")):
    ...
```

### try / except

```
Syntax:
try:
    <code that might fail>
except <ExceptionType>:
    <what to do about it>
    the exception TYPE goes on the except line itself
    a bare `except:` catches everything — including KeyboardInterrupt
        and SystemExit, so Ctrl+C gets swallowed
    multiple types: except (ValueError, TypeError):
finally:
    <runs whether or not an exception occurred — for cleanup>
```

Handles the failures that *do* raise, as opposed to the OpenCV calls that return
sentinels. Catch the specific type you expect; a bare `except` hides bugs by
swallowing errors you would rather see.

```python
try:
    value = int(response.strip())
except ValueError:
    value = None        # unparseable — abstain rather than guess
```

Exception types worth knowing here: `json.JSONDecodeError` for a corrupt config,
`ValueError` from `int()` on non-numeric text and from `max()` on an empty sequence,
`StatisticsError` from `stdev` with under two samples, `FileNotFoundError` from
`open`. `finally` is the right home for `capture.release()`, since it runs even when
the program exits by exception.

### ord

```
Function:
ord(c)
    c: a single character string
    returns: its integer code point — ord('q') is 113
```

Converts a character to the integer `cv2.waitKey` returns, so key comparisons
can be written readably. Non-printable keys such as ENTER and ESC have no
character, so their codes (13, 27) are written as literals.

```python
if cv2.waitKey(1) & 0xFF == ord('q'):
    break
```

### yield

```
Syntax:
yield value
    turns the enclosing function into a GENERATOR
    execution SUSPENDS at the yield and hands `value` to the caller
    resumes at that exact point on the next iteration, with all local
        state intact
    contrast with `return`, which exits permanently
```

Lets an endless detection loop emit events one at a time while keeping its state
between them. Note that `return "SETTLE"` in a `for` loop iterates the string's
six characters instead — a bug that looks exactly like repeated detections.

```python
for event in dieRollDetection(threshold, roi):
    ...
```

### if \_\_name\_\_ == "\_\_main\_\_"

```
Syntax:
if __name__ == "__main__":
    __name__ is "__main__" when a file is RUN directly
    it is the module's name when the file is IMPORTED
```

Guards code that should only run on direct execution, keeping test harnesses
from firing on import. Without it, importing a module for one helper can open a
camera or a blocking window as a side effect.

```python
if __name__ == "__main__":
    codeTester()
```

---

## Vision model calls

### ollama.generate — RETIRED

`ollama_func.py` has been deleted and the local-VLM path abandoned (accuracy on
d20 numerals was poor at every model tried). Kept here for the prompt-design
lessons at the end of the entry, which transfer to any vision model. Do not
build on this API.

```
Function:
ollama.generate(model, prompt=None, images=None, options=None, stream=False,
                format=None, system=None, keep_alive=None)
    model: the model tag, e.g. "qwen2.5vl:7b"
        must already be pulled — check with `ollama list`
    prompt: the instruction text
    images: a LIST of images — bytes, base64 strings, or file paths
        the list allows several images per prompt; a single image
        still needs the [ ] wrapper
        .webp is not decoded — convert to .png/.jpg first
        paths containing spaces are a recurring source of trouble;
        passing bytes avoids the whole category
    options: sampling parameters, e.g. {"temperature": 0}
        temperature 0 makes repeated calls more consistent, which
        matters when voting across frames
    stream: False returns one complete response; True yields chunks
    format: "json" constrains output to valid JSON
    returns: a response object — text is at response.response
        the older chat API returns it at response["message"]["content"]
```

Sends a prompt plus images to a locally-hosted model. The reply is always a
**string**, so convert at the boundary and treat unparseable output as an abstain
rather than letting it flow downstream as text.

```python
success, buffer = cv2.imencode('.jpg', upscaled)
response = ollama.generate(
    model="qwen2.5vl:7b",
    prompt="...Reply with only the number. If you cannot identify it, reply UNKNOWN",
    images=[buffer.tobytes()],
)
```

Two prompt-design notes learned here: never give the model a *valid-looking* default
for failure cases ("if unsure, reply 20"), because it makes failures indistinguishable
from real answers and uncountable. And a model reading a flat image has no notion of
"the top" of a die — "the face directly facing the camera, in the centre of the
image" is something it can actually act on.

---

## Gemini API (google-genai)

Package is **`google-genai`**, imported as `from google import genai`. The older
`google-generativeai` package is deprecated and has a different client shape —
tutorials written against it will not work.

Three conventions that bite:

- **`genai.Client` is keyword-only.** See the entry below; the error message is
  misleading.
- **Never name a project file `google.py`, `genai.py`, or `types.py`.** The first
  two shadow the package; `types.py` shadows a *standard library* module and
  breaks unrelated code. This project has already lost time to `ollama.py` and
  `discord.py` doing exactly this.
- **`models.list()` is not an availability check.** It lists what the API knows
  about, not what your tier may call. Verified: `gemini-2.5-flash` appears in the
  listing and 404s when invoked.

### genai.Client

```
Function:
genai.Client(*, enterprise=None, vertexai=None, api_key=None, credentials=None,
             project=None, location=None, debug_config=None, http_options=None)
    api_key: your Gemini API key
        must be passed BY NAME — see the note below
        default None: falls back to the GEMINI_API_KEY environment variable
    vertexai: use Google Cloud Vertex AI instead of the Developer API
        default None: the Developer API — what a free-tier key uses
        True: Vertex, which needs a GCP project and different auth
    project / location / credentials: Vertex-only; leave unset
    enterprise: enterprise routing; leave unset
    debug_config: request/response logging for debugging
    http_options: timeouts and retry configuration
        default None: SDK defaults
    returns: a Client object
```

**Note the bare `*` immediately after the opening paren: every parameter is
keyword-only.** `genai.Client(key)` raises

```
TypeError: Client.__init__() takes 1 positional argument but 2 were given
```

which reads like an arity bug but is not. Python passes the new instance as
`self` — that is positional argument 1 — and the key becomes argument 2, which
has nowhere to go because `*` closes the positional slots. **On a method,
subtract one from both numbers to get the count in your own code:** "takes 1,
got 2" means "takes 0, you passed 1."

```python
client = genai.Client(api_key=gemini_api_key)   # keyword, not positional
```

### client.models.generate_content

```
Function:
client.models.generate_content(model, contents, config=None)
    model: the model ID string
        "gemini-3.6-flash": current free-tier Flash (verified working 2026-08-07)
        "gemini-flash-latest": alias that auto-tracks the newest Flash —
            convenient, but the model changes underneath without a code edit,
            so measured accuracy numbers stop being reproducible
        model IDs expire; see "Finding a working model" below
    contents: the prompt
        a plain string, for a text-only smoke test
        a list mixing Part objects and strings, for multimodal:
            [image_part, "your question"]
    config: a types.GenerateContentConfig instance
        default None: unconstrained free-text output, fine for a smoke test
    returns: a response object
        .text: the reply as a string
        .parsed: the reply deserialized into the response_schema type
        .usage_metadata.prompt_token_count / .candidates_token_count
```

```python
response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents="Reply with the word OK.",
)
print(response.text)
```

### types.Part.from_bytes

```
Function:
types.Part.from_bytes(data, mime_type)
    data: raw image bytes
        from OpenCV: cv2.imencode(".png", crop)[1].tobytes()
        pass RAW bytes — the SDK base64-encodes internally. Do not pre-encode.
    mime_type: the format string
        "image/png": lossless, matches what capture_generator.py writes
        "image/jpeg": only if there is a reason to re-compress
    returns: a Part suitable for the contents list
```

Measured on this rig: a 114x109 die crop bills **~1110 input tokens**. Gemini
tiles images and has a per-image floor, so the Anthropic `w*h/750` estimate does
not transfer — do not size budgets with it.

```python
ok, buf = cv2.imencode(".png", die_crop)
part = types.Part.from_bytes(data=buf.tobytes(), mime_type="image/png")
```

### types.GenerateContentConfig

```
Function:
types.GenerateContentConfig(system_instruction=None, temperature=None,
                            max_output_tokens=None, response_mime_type=None,
                            response_schema=None, thinking_config=None,
                            safety_settings=None, top_p=None, top_k=None)
    system_instruction: standing instructions, separate from the per-call prompt
        put the "you are reading a d20" framing here, not in contents
    temperature: randomness, roughly 0.0-2.0
        0.0: near-deterministic — correct for classification, where the goal is
            one right answer rather than creative variety
    max_output_tokens: cap on the reply
        256: ample for a small JSON object
    response_mime_type: the output format
        "application/json": REQUIRED for structured output. Setting
            response_schema without this does not reliably constrain the reply.
    response_schema: the shape to enforce
        a Pydantic BaseModel class — read the result back from response.parsed
        a plain dict JSON schema — also accepted
    thinking_config: reasoning budget on 2.5+ models
        default None: model default
    safety_settings: content filter thresholds
        default None: defaults. Dice are uncontroversial; revisit only if an
            empty response comes back with a blocked finish reason.
    top_p / top_k: sampling controls; leave unset when temperature is 0
```

Structured output is the abstain mechanism. Returning a typed object rather than
a string also closes a long-standing bug here: `discord_webhook.py` compares
`== 20` and `== 1`, which never match when the value arrives as text.

```python
class DieReading(BaseModel):
    value: Optional[int]                          # None means "could not read"
    confidence: Literal["high", "medium", "low"]

config = types.GenerateContentConfig(
    temperature=0.0,
    response_mime_type="application/json",
    response_schema=DieReading,
)
reading = response.parsed        # a validated DieReading; value is a real int
```

### client.models.list

```
Function:
client.models.list()
    takes no required arguments
    returns: an iterable of model objects
        .name: "models/gemini-3.6-flash" — note the "models/" prefix
        .supported_actions: e.g. ["generateContent"]
        .input_token_limit / .output_token_limit
```

Use it to *discover candidates*, never to confirm availability — see the
convention note at the top of this section.

### Finding a working model

Model IDs expire. `gemini-2.5-flash` and `gemini-2.5-flash-lite` both went 404
("no longer available to new users") while still appearing in `models.list()`.
The reliable procedure is to call each candidate and see what comes back:

```python
for m in ["gemini-3.6-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]:
    try:
        r = client.models.generate_content(model=m, contents="Say OK")
        print(m, "WORKS", r.text.strip())
    except Exception as e:
        print(m, "FAILS", type(e).__name__, str(e)[:100])
```

Distinguish the two failure modes — they mean different things:

- **404 NOT_FOUND** — permanently unavailable to this account. Pick another model.
- **503 UNAVAILABLE** — transient overload. The model is available, just busy.
  Retry, or prefer a less contended one.

As measured 2026-08-07 on this key: `gemini-3.6-flash`, `gemini-3.1-flash-lite`,
`gemini-3-flash-preview`, and `gemini-flash-latest` all worked;
`gemini-3.5-flash` returned 503; both 2.5 Flash variants returned 404.

### Free tier constraints

- **No credit card required**, and image input is included — the reason this
  provider was chosen over Anthropic and OpenAI, which have no free tier.
- **~10 requests per minute** is the binding limit, not cost or tokens. At ~1110
  tokens per die crop, the 1M tokens-per-minute ceiling is irrelevant.
- **This makes frame-voting expensive in requests, not dollars.** Voting over
  5 frames means 5 requests per roll, i.e. two rolls per minute before
  throttling. Measure single-call accuracy before spending that budget.
- **Treat HTTP 429 as a normal condition**, not an exception — it should surface
  as "try again" in the UI, never a traceback.
