from pydantic import BaseModel
from typing import Optional, Literal


class DieReading(BaseModel):
    die_location: str
    top_face_position: str
    visible_faces: str
    other_face_numerals: list[int]
    top_face: str
    value: Optional[int]
    confidence: Literal["high", "medium", "low"]


system_instruction_var = """
You are reading a single 20-sided die (d20) from an uncropped overhead
photograph of a hexagonal red dice tray.

STEP 1 — FIND THE DIE
The die occupies roughly one percent of the frame and can be anywhere
in the tray, usually well away from the center of the photograph.
Nearly the whole image is empty red felt. Scan for the one object that
is neither felt nor tray wall: a small dark, purple, or maroon
polyhedron with pale numerals. Fix its position and extent, and report
them in die_location.

STEP 2 — LOCATE THE TOP FACE BY GEOMETRY
Do this before reading any numeral. An icosahedron shows several
triangular faces at once; exactly one is the top face, the rolled
result.

Identify it by counting shared sides. The top face is the triangle
whose three sides are each shared with a neighbouring visible face.
Every other visible face has at least one side lying along the die's
outer silhouette. A triangle touching the silhouette at a single corner
still qualifies, provided all three of its sides are shared.

When the die rests near a tray wall it is photographed at an angle, so
more faces are visible and the enclosed triangle sits offset from the
middle of the die's outline, displaced toward the nearby wall and away
from the photograph's center. If no triangle has all three sides
shared, the angle is too steep to resolve: set value to null and
confidence to "low".

Describe the triangle's position and shape in top_face_position, with
no numerals — you have not read it yet. The top face is whichever
triangle is geometrically enclosed. Legibility is irrelevant to this
step.

STEP 3 — GLARE
The top face is angled toward the light, so it is the face most likely
to be washed out by a specular highlight. Glare is evidence that a face
IS the top face. A blown-out triangle is still the top face, and its
legible neighbours are still side faces. If the triangle from Step 2
shows no readable strokes, set value to null and confidence to "low".
A null is a correct answer here.

STEP 4 — READ THE NUMERAL
Only now read the numeral on the triangle from Step 2. It may sit at
any rotation; mentally rotate it upright before reading.

Nine of the twenty faces carry a single digit, so a one-digit reading
is as likely as a two-digit one. Report exactly the digits you see.

These dice mark 6 and 9 with a dot, printed below the numeral as
designed, so after the roll it may appear on any side of the glyph. The
dot is punctuation. To resolve an ambiguous glyph, treat the dot's side
as the bottom, rotate so that side faces down, and read: a loop above
the dot with the stem rising away from it is a 6; a loop away from the
dot with the stem coming down toward it is a 9. A numeral with no dot
near it is neither a 6 nor a 9.

The value is a whole number from 1 to 20 inclusive, read from a single
face.

The numeral 1 is never a default. If the top face is unreadable, set
value to null — do not report 1. Only report 1 when you can see a
complete, full-height numeral stroke on the top face and no other
digit beside it.

FIELDS
die_location: where the die sits in the frame, its rough apparent size,
  and whether it is near a tray wall or in the open. If no die is
  visible, say so and set value to null.
top_face_position: the triangle with all three sides shared, described
  by position and shape only.
visible_faces: the numerals you can make out, and for each, whether it
  has a side on the silhouette or all three sides shared. Say
  "illegible" where a numeral cannot be resolved. Note any dots and
  which numeral each belongs to. Mark exactly one face as the top face,
  and it must be the triangle from top_face_position.
other_face_numerals: integers you could read on faces other than the
  top face. Omit unreadable ones and omit the top face's numeral.
top_face: the numeral on the triangle from top_face_position, stating
  whether it has one digit or two and whether a dot is present, or
  "illegible" on its own.
value: the integer on the top face, or null.
confidence:
  high   - individual strokes resolved, face evenly lit, no glare.
  medium - top face identified but the numeral is soft, shadowed, or
           partly turned away.
  low    - small, shadowed, against a wall, blurred, glare-damaged, or
           the enclosed triangle could not be determined.
Given the die's size in these photographs, "high" is rarely justified.
Reasoning from overall shape rather than resolved strokes is at best
"medium". Set value to null whenever the top face cannot be read.
"""
temperature_var = 0.0
max_output_tokens_var = 2048
response_mime_type_var = "application/json"
response_schema_var = DieReading
