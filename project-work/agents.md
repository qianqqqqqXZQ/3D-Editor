# Project Notes

## Overview

This is a single-file Flask and Three.js Part-Level 4DGS Animation Editor. Backend state,
parsing, animation, export, and API routes are in `app.py`; the browser UI is embedded in
`HTML_PAGE` in the same file.

## Layout

- `app.py`: Flask application, `STATE`, PLY/PT readers, Part/keyframe/4DGS APIs, and UI.
- `static/`: local Three.js r128 and OrbitControls assets.
- `generated/`: exported PT frames and archives.
- `project-work/`: maintained planning and project-reference documents.
- `requirements.txt`: Flask, NumPy, plyfile, and PyTorch dependencies.

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
`STATE['4dgs_parts']`. Verify this work using Flask's test client and in-memory PLY/PT fixtures.
