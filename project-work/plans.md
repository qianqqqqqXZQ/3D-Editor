# Part-Level 4DGS Animation Editor Plan

## Baseline

- [x] Establish `project-work/` for working documents and `generated/` for generated exports.
- [x] Implement the initial Flask editor, PLY/PT parsing, Part editing, keyframe tracks, 4DGS import, and exports.
- [x] Verify the baseline with Python compilation and Flask test-client coverage.

## Current Request: Color Handling and HTTP API Contract (2026-08-14)

- [x] Add the specified SH-to-RGB conversion and fixed Part color palette.
- [x] Implement compliant initial and append point-cloud uploads, including SH-degree padding.
- [x] Implement server-directory 4DGS upload and 4DGS/static state initialization.
- [x] Implement binary point-cloud payload and REST-style Part management APIs.
- [x] Run compilation plus API regression coverage, review the changed code, then update this checklist.

## Current Request: Complete HTTP API and Editor Contract (2026-08-15)

- [x] Create a Git checkpoint before the implementation changes.
- [x] Complete REST-style keyframe, settings, frame, export, and current-export endpoints.
- [x] Correct binary frame/point-cloud payloads and state/export concurrency behavior.
- [x] Replace the damaged embedded editor page with `static/editor.html`, covering the requested upload, selection, transform, timeline, and modal workflows.
- [x] Run compilation, API regression coverage, browser rendering checks, and a focused code review.

## Run

```powershell
py -3.13 -m pip install -r requirements.txt
py -3.13 app.py
```

Open `http://localhost:5011`.

## Verification

```powershell
py -3.13 -m py_compile app.py
```

2026-08-15 verification completed:

- `py -3.13 -m py_compile app.py`
- Flask test-client regression for initial/append uploads, SH normalization, REST Part and keyframe operations, static/4DGS binary payloads, settings, and both export paths.
- Browser checks at desktop and `390x844` mobile viewports: Three.js canvas rendered, controls appeared in their responsive layout, and no console errors were reported.

## Current Request: Project Documentation (2026-08-15)

- [x] Create a Git checkpoint before documentation changes.
- [x] Rewrite the root README with an English-first language switch and a Chinese translation.
- [x] Document the current structure, Quick Start, workflow, supported data, API entry points, Background, and Acknowledgements.
- [x] Synchronize `project-work/agents.md` with the active static editor and run a documentation/code review.
- [x] Run compilation and repository checks after the documentation changes.

2026-08-15 verification completed:

- `py -3.13 -m py_compile app.py`
- Flask test client `GET /` check confirming the active `static/editor.html` page is served.
- Explicit UTF-8 README section checks for both language sections and required headings.
- `git diff --check`

## Current Request: Frontend transform, selection, timeline, and export contract (2026-08-16)

- [x] Create a recoverable Git checkpoint before the implementation changes.
- [x] Replace the active editor UI with explicit Orbit/Select modes, crosshair box selection, Shift additive selection, yellow selected points, and clip-space projection checks.
- [x] Implement immutable `originalPositions` preview with ZYX Euler rotation, per-Part backend transforms, active slider override, and translation-only Pivot marker motion.
- [x] Implement Part loading/list rendering, 4DGS labels, Pivot editing/centroid reset, degree-based transform sliders, keyframe operations, per-Part timeline markers, and 20 FPS playback.
- [x] Connect static and 4DGS frame endpoints, background export polling, and visible fetch error handling to the local Three.js r128 assets.
- [x] Enforce unloaded-workspace 400 responses for frame/point-cloud/transform endpoints and expose exported `.pt` fields at top level plus nested `splats` compatibility.
- [x] Run JavaScript syntax, Python compilation, Flask API regression, 4DGS variable-point/export regression, startup HTTP, and `git diff --check` verification.
