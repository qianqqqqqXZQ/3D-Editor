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
