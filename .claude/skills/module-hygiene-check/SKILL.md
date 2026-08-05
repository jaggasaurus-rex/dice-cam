---
name: module-hygiene-check
description: Check a multi-file Python project for duplicate function definitions, circular imports, star-import ambiguity, module-level side effects, and stale imports left behind after a refactor. Use this skill whenever the user splits a file, moves functions between modules, adds a new module, or reports an ImportError, NameError, AttributeError on a module, or code that "runs the old version" of something. Also trigger on "check my code", "did I miss anything", or after any reorganization. Report findings with file and line — never edit the user's files.
---

# Module Hygiene Check

Refactoring a growing script into modules produces the same small set of problems
every time, and they share a nasty property: the program often still runs. It just
runs the wrong code, or opens a camera it was not asked to open, or resolves a name
from a module nobody intended.

## Hard constraint: read-only

**Never edit, write, or create files in this project.** The user writes every line.
Report each finding with file, line, and what specifically goes wrong.

## Read every file fresh, every time

Before reporting anything, re-read the files from disk — including ones already read
earlier in the conversation. Refactors invalidate context constantly, and a review
based on a stale copy is worse than no review: it sends the user hunting for a
problem they already fixed, and it costs trust that is hard to rebuild.

This has already happened once in this project. A confident report of duplicate
functions was based on a copy of a file from earlier in the session; the user had
already migrated them and had to push back. Re-read first.

## What to check

### 1. Duplicate definitions across modules

The signature failure of an incomplete migration: a function is copied into its new
home but never deleted from the old one. Both definitions exist, both are valid
Python, and which one runs depends entirely on where the caller imports from.

The damaging case is when the two copies have *drifted* — the new one takes an extra
parameter, or reads a config key the old one does not. Callers pointed at the old
copy then fail in ways that look nothing like "you have two of these."

Report every function name defined in more than one module, and state which one the
entry point is actually reaching.

### 2. Circular imports

Module A imports B, B imports A. Python tolerates this in some import orders and
fails in others with a partially-initialized module — an error that names a symbol
rather than the cycle, so it reads like a typo.

When one is found, work out which direction the dependency genuinely runs (which
module actually uses names from the other) and report that the reverse import is the
one to remove. Usually only one direction is real; the other is a leftover.

### 3. Star imports hiding the source of a name

`from x import *` makes it impossible to tell where a name came from by reading the
file. Three specific consequences worth reporting:

- **Collisions resolve silently by import order.** Two modules exporting the same
  name means the last import wins, with no warning.
- **Names arrive by accident.** A module that does `from camera import capture` will
  re-export `capture` to anyone who star-imports *it*. Code can depend on a name it
  never imported, and it breaks later when the intermediate module is reorganized.
- **Deleting a star import breaks things invisibly**, because nothing states what was
  being used through it.

Flag star imports in files that have grown past a handful of functions, and flag
specifically any name being used that arrives only via re-export.

### 4. Module-level side effects

Code at module scope runs on **import**, not just on execution. A module that opens a
camera, shows a window, or calls a test function at the bottom of the file does all
of that the moment anything imports it — including importing it for one unrelated
helper.

This project has hit it twice: a legacy module called its own test function at
module scope, so importing it opened a blocking window; and two modules each
constructed their own `VideoCapture(0)`, which on Windows puts the device into a
broken state where reads fail with an opaque MSMF error rather than a clear "already
in use".

Report:
- any function call at module scope that does more than define things
- any shared external resource (camera, file handle, connection) constructed at
  module scope in more than one place
- the fix pattern to describe: guard test entry points with
  `if __name__ == "__main__":`, and construct shared resources in exactly one module
  that everyone else imports from

### 5. Stale imports

Names imported that no longer exist at the source, or no longer exist at all.
Common after folding two functions into one — the import list still names the
function that was absorbed, and it raises `ImportError` on the next run.

Also worth flagging: imports that still resolve *only* because of a star-import
re-export chain. Those work today and break the moment the chain is tidied.

### 6. Dead code left behind

Functions superseded but not deleted, variables assigned and never read,
unreachable statements after a `return`, comments describing work already done.
Low severity — group them into a single short list rather than reporting each as its
own finding.

## Output format

Rank by severity: things that silently run the wrong code first, crashes second,
tidiness last. For each:

```
N. <one-line description> (file.py:LINE)
   What happens: <the concrete failure, not the principle>
   Fix: <prose, or which line to delete>
```

Then a single grouped "dead code" list if there is any.

Close by naming which one or two to fix first and why. A long list of equally
weighted findings is hard to act on; a ranked list with a recommended starting point
is not.
