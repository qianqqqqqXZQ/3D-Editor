# Project Notes

## Overview

This is a Flask and Three.js Part-Level 4DGS Animation Editor. Backend state, parsing,
animation, export, and API routes are in `app.py`; the active browser UI is
`static/editor.html`. `app.py` still contains a legacy embedded `HTML_PAGE` fallback, but
the root route serves the static editor when it is present.

## Layout

- `README.md`: English-first project documentation with a Chinese language section.
- `app.py`: Flask application, `STATE`, PLY/PT readers, Part/keyframe/4DGS APIs, and fallback UI.
- `static/`: local Three.js r128 and OrbitControls assets.
- `static/editor.html`: active Three.js editor, binary point-cloud parser, immutable source-position preview, and responsive controls.
- `generated/`: exported PT frames and archives.
- `project-work/`: maintained planning and project-reference documents.
- `requirements.txt`: Flask, NumPy, plyfile, and PyTorch dependencies.

Documentation conventions:

- Keep planning/reference notes in `project-work/`.
- Keep generated exports in `generated/`.
- Keep the English README section first; link to the Chinese section with the language selector at the top.

## Run And Test

```powershell
py -3.13 -m pip install -r requirements.txt
py -3.13 app.py
py -3.13 -m py_compile app.py
```

Ubuntu/Debian equivalent:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

The server listens on `http://localhost:5011`.

## Linux Compatibility (2026-08-17)

- The backend has no Windows-specific paths or system commands. `app.py` listens on
  `0.0.0.0:5011`, so the same Flask entry point works on Linux and can be reached from the
  network when firewall rules permit it.
- `requirements.txt` uses platform-independent Python packages and PyTorch from regular PyPI. The
  documented native path targets 64-bit Ubuntu/Debian with Python 3.10+ and a glibc-based
  distribution. CUDA is not required for parsing or export.
- `Dockerfile` uses the Linux `python:3.11-slim` base image and is the portable container path.
  Docker was not installed in the current Windows environment on 2026-08-17, so a local Linux
  image build/run validation could not be performed here.

## Current API Work (2026-08-14)

The current task adds a specified SH DC color conversion, binary `GET /api/pointcloud`, and
REST-style Part APIs while retaining legacy UI routes. State changes hold `STATE_LOCK`; static
point clouds use global arrays plus `part_id_array`, while source 4DGS frames are held in
`STATE['4dgs_parts']`. `GET /api/pointcloud` is intentionally source-data-only: it does not
apply keyframe transforms, emits little-endian count/xyz/rgb/part-id arrays, and colors unassigned
static points from SH DC. Verify this work using Flask's test client and in-memory PLY/PT fixtures.

## API Contract Notes (2026-08-15)

- `GET /api/frame/<frame>` emits `count + xyz` for static-only workspaces and adds RGB plus Part ids when a 4DGS Part exists. Keyframe preview transforms remain client-side.
- `POST /api/export` serializes in a background thread using `export_active`, `export_progress`, and `export_done`; `POST /api/export_current` applies Part transforms before writing a `.pt` file.
- Static vertices unassigned after Part deletion remain in point-cloud and export data with SH-derived display colors.
- Verification is the compile command plus the Flask-client regression and browser desktop/mobile checks recorded in `plans.md`.

## Frontend Contract Notes (2026-08-16)

- `static/editor.html` is the only active UI. It uses local Three.js r128 and OrbitControls files and never loads a CDN.
- `originalPositions` is immutable source geometry for every preview pass. `previewAllTransforms()` applies the active Part's degree-based slider values (converted to radians) and `/api/frame_transforms/<frame>` values to each Part using the same ZYX matrix as `app.py`.
- `setupSelectionEvents`, `onMouseDown`, `onMouseMove`, `onMouseUp`, and `performBoxSelect` implement Orbit/Select modes. Box selection projects displayed positions with `projectionMatrix * matrixWorldInverse`, rejects points behind/outside the clip volume, and supports Shift additive selection.
- 4DGS playback uses `/api/frame/<frame>` for variable-point source frames; static playback uses `/api/pointcloud?frame=<frame>`. Both are followed by `/api/frame_transforms/<frame>` and a fresh immutable preview.
- Exported checkpoints contain top-level `means`, `quats`, `scales`, `opacities`, `sh0`, `shN`, and `sh_degree`, plus a nested `splats` object for compatibility.

## Rendering Bugfix Notes (2026-08-16)

- Point-cloud `PointsMaterial` uses `sizeAttenuation: false`. The UI point-size slider is a pixel-size control; enabling attenuation here made the default value `3` world units and produced giant black point sprites that covered the viewport.
- Coordinate axes are rendered by `addThickAxes()` as red, green, and blue cylinders with `depthTest: false`, which keeps them stable over the grid and avoids origin z-fighting.

## Rendering Bugfix Notes (2026-08-17)

- Static `/api/pointcloud` responses include positions, colors, and four-byte Part IDs. The active
  editor must parse this endpoint with metadata enabled; passing `false` filled every `partIds`
  entry with `-1`, so `previewAllTransforms()` skipped all static vertices while the pivot marker
  still moved.
- `loadPointCloud()` now parses both active binary endpoints with metadata enabled. `/api/frame` is
  selected only for 4DGS workspaces, where it also carries colors and Part IDs.

## Comparison Notes (2026-08-18)

- Comparison is isolated from `STATE` through `COMPARISON_STATE`; it never changes the active Parts,
  keyframes, timeline, or export state.
- `POST /api/comparison` accepts exactly two multipart `files` (`.ply` or `.pt`) and returns metadata.
  `GET /api/comparison/a` and `/api/comparison/b` emit little-endian `count + xyz + rgb` binary payloads;
  `DELETE /api/comparison` clears the session.
- Canonical PLY/PT frames retain `colors` and `has_colors` metadata. Comparison prefers explicit RGB,
  then SH DC conversion, then neutral gray. Existing editor uploads continue using their established
  Part/SH color behavior.
- `static/editor.html` keeps `comparisonPointsA` and `comparisonPointsB` in the same Three.js scene and
  camera. Comparison mode hides editor-only controls and the original point object, supports A/B checkboxes
  plus A-only/B-only/Both shortcuts, and disposes comparison geometry/materials on exit.
- Mobile comparison mode overrides the legacy hidden left sidebar with a scrollable overlay panel so the
  two file inputs and visibility controls remain reachable at narrow widths.

## Comparison Dual view Notes (2026-08-18)

- Comparison now has four peer modes: A only, B only, Both (single viewport overlay), and Dual view.
- Dual view creates two pane-local Three.js scenes/renderers/cameras/OrbitControls only while Comparison is
  active. Cloud A and Cloud B are shown in separate panes, side-by-side on desktop and stacked on narrow screens.
- Dual panes clone the point objects while sharing the source geometries; pane materials and helper scene
  resources are disposed without releasing the main Comparison geometry twice.
- `Link cameras` is enabled by default. Camera position, quaternion, zoom, and OrbitControls target are copied
  with a recursion guard. Linked reset fits the union of both clouds; unlinked reset fits each pane separately.
- Dual view forces both clouds visible and disables the single-view visibility checkboxes. Switching back to a
  single mode restores A-only/B-only/Both visibility semantics. Exiting Comparison removes pane canvases,
  controls, renderers, and helper resources before refreshing the editor.
- Frontend verification includes Node syntax parsing, Flask compile/startup checks, desktop and `390x844`
  browser layout/lifecycle checks, console error inspection, and `git diff --check`.

## Comparison Dual View Visibility Fix (2026-08-18)

- Switching from `A only` or `B only` to Dual view previously let a pane clone inherit the source point
  object's `visible=false` state, leaving that pane without a point cloud.
- `createDualPane`, `ensureDualView`, and Dual-mode visibility refresh now force pane point objects visible.
  Single-view A/B visibility remains controlled by `comparisonVisibility`; Dual view always shows both clouds.

## Comparison Cloud Transform Export Notes (2026-08-18)

- Comparison keeps immutable base XYZ arrays and independent `{tx, ty, tz, rx, ry, rz}` transforms for Cloud A
  and Cloud B. Rotation reuses the editor's ZYX matrix and uses each cloud's base-geometry centroid as pivot.
- Transform edits update the shared Three.js geometry and recompute its bounding sphere, so both single and Dual
  view reflect the selected cloud without changing the editor `STATE` or backend comparison session.
- `Export selected .ply` downloads a binary little-endian PLY containing transformed float32 XYZ and uint8 RGB;
  it is a browser-local download and leaves original uploaded files untouched.

## Raw Tensor PT Notes (2026-08-18)

- `load_pt_bytes` accepts a raw `torch.Tensor` saved directly with `torch.save` when it is two-dimensional
  with at least three columns. Columns 0..2 become `xyz`; columns 3..5 become explicit RGB when present;
  columns 6 and above are intentionally ignored.
- Raw RGB uses the existing `_normalise_rgb` behavior, converting common 0..255 values to clipped 0..1.
- Invalid raw Tensor shapes raise `ValueError("Raw .pt tensors must have shape (N, >=3).")`; gsplat dict/list
  payload handling remains unchanged.
