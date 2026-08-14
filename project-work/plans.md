# Part-Level 4DGS Animation Editor Plan

## Baseline

- [x] Establish `project-work/` for working documents and `generated/` for generated exports.
- [x] Implement the initial Flask editor, PLY/PT parsing, Part editing, keyframe tracks, 4DGS import, and exports.
- [x] Verify the baseline with Python compilation and Flask test-client coverage.

## Current Request: Color Handling and HTTP API Contract (2026-08-14)

- [ ] Add the specified SH-to-RGB conversion and fixed Part color palette.
- [ ] Implement compliant initial and append point-cloud uploads, including SH-degree padding.
- [ ] Implement server-directory 4DGS upload and 4DGS/static state initialization.
- [ ] Implement binary point-cloud payload and REST-style Part management APIs.
- [ ] Run compilation plus API regression coverage, review the changed code, then update this checklist.

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
