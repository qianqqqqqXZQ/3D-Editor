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

The server listens on `http://localhost:5011`.

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

## Deployment Architecture (2026-08-17)

- Vercel is a frontend/CDN target for this project, not the runtime for the stateful Flask editor API. The public UI can be deployed there, while the Python API must run in a persistent container service with writable ephemeral storage and a production WSGI server.
- Public deployment parses untrusted `.pt` files with `torch.load(..., weights_only=True)`, so it supports tensor-only gsplat checkpoints while rejecting arbitrary Python objects. Trusted local mode retains legacy `weights_only=False` compatibility.
- `STATE` is a `ContextVar`-backed mapping in public mode. Every browser has an unguessable workspace identifier, returned by `/api/state`, retained in session storage, and sent as `X-Workspace-ID`; a HttpOnly Cookie remains a fallback. The backend retains each workspace only for `WORKSPACE_TTL_SECONDS` and removes its export directory on expiry.
- `static/runtime-config.js` is generated at Vercel build time by `scripts/build-runtime-config.js` from `EDITOR_API_ORIGIN`. The static editor uses that origin for all API calls and downloads exports via credentialed `fetch`, so cross-origin downloads retain the workspace header.
- Run the public API with exactly one Gunicorn worker and one service replica unless a shared workspace store is added. The current workspace state is intentionally memory-backed and temporary; restarting or horizontally scaling the API discards active workspaces.
