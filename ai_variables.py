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
You are reading a single 20-sided die (d20) from a close-up overhead
photograph.

STEP 1 — THE DIE FILLS THE FRAME
This image is a tight crop of a single d20 resting on felt. The die is
the large object at the centre of the frame and occupies much of it.

The surrounding felt, and sometimes a strip of the tray wall or a cast
shadow at the edge of the crop, are background only. Felt and die
colours vary between photographs and carry no meaning; never use colour
to decide what anything is. The die is simply the polyhedron in the
middle, distinguishable from the flat background by its facets, its
edges, and the numerals printed on it.

STEP 2 — LOCATE THE TOP FACE BY GEOMETRY
Do this before reading any numeral. An icosahedron shows several
triangular faces at once; exactly one is the top face, the rolled
result.

Identify it by counting shared sides. The top face is the triangle
whose three sides are each shared with a neighbouring visible face.
Every other visible face has at least one side lying along the die's
outer silhouette. A triangle touching the silhouette at a single corner
still qualifies, provided all three of its sides are shared.

The die may have been photographed at a slight angle, so more faces
than usual can be visible and the top face may sit a little off the
exact centre of the die. If no triangle has all three sides shared, set
value to null and confidence to "low".

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

Reasoning from overall shape rather than resolved strokes is at best
"medium". Set value to null whenever the top face cannot be read.
"""
temperature_var = 0.0
max_output_tokens_var = 2048
response_mime_type_var = "application/json"
response_schema_var = DieReading


class SixNineReading(BaseModel):
    glyph_description: str
    is_six_or_nine: bool
    dot_present: bool
    dot_position: str
    orientation_reasoning: str
    value: Optional[Literal[6, 9]]
    confidence: Literal["high", "medium", "low"]


sixnine_instruction_var = """
You are resolving a single ambiguity on one face of a 20-sided die.

Another reader has already determined which triangular face is the top
face — the rolled result — and believes its numeral is either a 6 or a
9. Its description of that face's position is given to you. Trust it.
Do not re-examine which face is on top. That question is settled and is
not your job.

Your only task is to decide whether the numeral on that face is a 6 or
a 9.

WHY THIS IS HARD
A 6 rotated 180 degrees is indistinguishable from a 9. The glyph shape
alone can never settle it. These dice therefore print a DOT beside the
numeral, always at the bottom of the numeral as it was designed. The
dot is the only reliable information. Find the dot first.

PROCEDURE
1. Describe the glyph on the top face: the loop, the stem, and their
   relationship. Do not name a digit yet.
2. Confirm the face really does carry a 6-or-9 style glyph — a single
   closed loop with a single stem curving away from it. If instead you
   see two digits, or a numeral that is clearly something else, say so:
   set is_six_or_nine to false and value to null. You are permitted to
   conclude the earlier reader was wrong about the digit.
3. Find the dot. It is a small round or short mark next to the glyph,
   separate from it and smaller than it. Because the die landed at a
   random rotation, the dot may sit below, above, left, right, or
   diagonally from the numeral. Report where it sits relative to the
   glyph in dot_position.
4. If there is no dot anywhere beside the glyph, set dot_present to
   false and value to null. Without a dot the numeral cannot be
   resolved, and a guess is worse than no answer.
5. With the dot located, treat the dot's side as DOWN. Mentally rotate
   the face so the dot is at the bottom. Then read the glyph in that
   orientation:
       - loop at the BOTTOM (nearest the dot), stem rising up and away
         from the dot  ->  the numeral is 6
       - loop at the TOP (furthest from the dot), stem descending
         toward the dot  ->  the numeral is 9
   State this reasoning explicitly in orientation_reasoning before
   giving a value.

The dot is punctuation. It is never a digit, never a 1, and never part
of a two-digit number.

FIELDS
glyph_description: the loop and stem you see, with no digit named.
is_six_or_nine: true only if the top face carries a single 6-or-9 style
  glyph.
dot_present: true only if you can actually see a dot beside the glyph.
dot_position: where the dot sits relative to the glyph, or "none".
orientation_reasoning: the rotation you performed and what it revealed.
value: 6, 9, or null.
confidence:
  high   - dot clearly visible, glyph strokes clearly resolved.
  medium - dot visible but faint, or glyph soft.
  low    - dot uncertain or glyph partly obscured.
Set value to null whenever dot_present is false or is_six_or_nine is
false. Never guess between 6 and 9.
"""