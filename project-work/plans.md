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

## Bugfix: black viewport on initial point-cloud render (2026-08-16)

- [x] Reproduce the black viewport with a real uploaded `.pt` file and inspect the rendered canvas.
- [x] Identify the cause as `PointsMaterial.sizeAttenuation` interpreting the default point size as world units.
- [x] Render point sizes in pixels with `sizeAttenuation: false` and verify the grid/points at desktop and mobile viewport sizes.

## Bugfix: axis-line flicker (2026-08-16)

- [x] Replace the thin `AxesHelper` with thicker red/green/blue cylinder axes.
- [x] Disable depth testing and depth writes for the axes to prevent grid z-fighting at the origin.
- [x] Verify the empty editor viewport visually and confirm no browser console errors.

## Current Request: Linux Quick Start (2026-08-17)

- [x] Inspect the server, dependencies, and container definition for platform-specific constraints.
- [x] Add an Ubuntu/Debian Linux Quick Start to the English README section.
- [x] Run available validation checks, review the documentation change, and record the Linux verification boundary.

2026-08-17 verification completed:

- `python -m py_compile app.py`
- Flask test client `GET /` and `GET /static/editor.html` smoke checks (both returned HTTP 200).
- README Linux Quick Start content check and `git diff --check`.
- Static platform review found no Windows-specific backend paths or commands. Docker is not
  installed and WSL has no Linux distribution in the current environment, so a native Linux or
  container run was not available for this checkout.

## Bugfix: static Part transform preview (2026-08-17)

- [x] Trace the static point-cloud load path and compare its binary metadata contract with the
  browser parser.
- [x] Preserve static Part IDs in the active editor so translation and rotation are applied to
  point positions, not only to the pivot marker.
- [x] Run Python, JavaScript, API/coordinate, page smoke, and diff checks; review the focused
  frontend change and record the browser upload-tool limitation.

2026-08-17 verification completed:

- `py -3.13 -m py_compile app.py`
- Active `static/editor.html` script parsed with `new Function`.
- Flask test client regression confirmed `/api/pointcloud` returns Part IDs and a keyframe with
  translation plus 90-degree rotation produces the expected transformed coordinates.
- Local browser opened `http://127.0.0.1:5011/`, rendered the active editor DOM with no startup
  console errors. Automated hidden-file chooser upload timed out, so no visual point movement
  assertion was made through the browser.
- `git diff --check`
