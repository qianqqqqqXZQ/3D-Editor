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
