import io
import json
import math
import os
import shutil
import struct
import tempfile
import threading
import zipfile
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from flask import Flask, jsonify, request, send_file

try:
    import torch
except Exception:
    torch = None

try:
    from plyfile import PlyData
except Exception:
    PlyData = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORT_ROOT = os.path.join(BASE_DIR, "generated")
os.makedirs(EXPORT_ROOT, exist_ok=True)

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 400 * 1024 * 1024

STATE: Dict[str, Any] = {
    "loaded": False,
    "filename": "",
    "n_vertices": 0,
    "xyz": None,
    "quats": None,
    "scales": None,
    "opacities": None,
    "sh0": None,
    "sh_rest": None,
    "sh_degree": 0,
    "part_id_array": None,
    "parts": {},
    "next_part_id": 0,
    "tracks": {},
    "num_frames": 30,
    "interpolation_method": "linear",
    "export_progress": -1,
    "export_dir": None,
    "4dgs_parts": {},
}
STATE_LOCK = threading.RLock()


def _arr(value: Any, shape: Tuple[int, ...], default: float = 0.0) -> np.ndarray:
    if value is None:
        return np.full(shape, default, dtype=np.float64)
    a = np.asarray(value, dtype=np.float64)
    if a.size == int(np.prod(shape)):
        return a.reshape(shape)
    out = np.full(shape, default, dtype=np.float64)
    flat = a.reshape(-1)
    out.reshape(-1)[: min(flat.size, out.size)] = flat[: out.size]
    return out


def _field(obj: Any, names: List[str], default: Any = None) -> Any:
    if isinstance(obj, dict):
        for n in names:
            if n in obj:
                return obj[n]
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return default


def _normalise_frame(obj: Any) -> Dict[str, Any]:
    xyz = _field(obj, ["xyz", "means3D", "means", "positions", "pos", "points"])
    if xyz is None and isinstance(obj, (list, tuple)) and len(obj) >= 1:
        xyz = obj[0]
    xyz = np.asarray(xyz if xyz is not None else np.zeros((0, 3)), dtype=np.float64)
    if xyz.ndim == 1:
        xyz = xyz.reshape((-1, 3))
    if xyz.shape[-1] > 3:
        xyz = xyz[:, :3]
    n = len(xyz)
    quats = _field(obj, ["quats", "rotation", "rotations", "rots"])
    quats = _arr(quats, (n, 4), 0.0)
    if quats.size and np.allclose(quats, 0):
        quats[:, 0] = 1.0
    scales = _field(obj, ["scales", "scale", "scaling"])
    scales = _arr(scales, (n, 3), 0.0)
    opacities = _field(obj, ["opacities", "opacity", "alpha"])
    opacities = _arr(opacities, (n,), 0.0)
    sh0 = _field(obj, ["sh0", "features_dc", "colors", "rgb", "color"])
    sh0 = _arr(sh0, (n, 3), 0.0)
    sh_rest = _field(obj, ["sh_rest", "features_rest"])
    if sh_rest is not None:
        sr = np.asarray(sh_rest, dtype=np.float64)
        if sr.ndim == 2 and sr.shape[0] == n:
            sr = sr.reshape((n, -1, 3)) if sr.shape[1] % 3 == 0 else None
        elif sr.ndim == 3 and sr.shape[0] != n and sr.shape[1] == n:
            sr = np.transpose(sr, (1, 0, 2))
        sh_rest = sr
    degree = int(_field(obj, ["sh_degree", "degree"], 0) or 0)
    return {"xyz": xyz, "quats": quats, "scales": scales, "opacities": opacities,
            "sh0": sh0, "sh_rest": sh_rest, "sh_degree": degree, "n_vertices": n}


def load_ply_bytes(data: bytes) -> Dict[str, Any]:
    if PlyData is None:
        raise RuntimeError("plyfile is required to read PLY files. Install with: pip install plyfile")
    ply = PlyData.read(io.BytesIO(data))
    vertex = ply["vertex"]
    names = set(vertex.data.dtype.names or [])
    xyz = np.stack([vertex[axis] for axis in ("x", "y", "z")], axis=1).astype(np.float64)
    n = len(xyz)
    colors = np.zeros((n, 3), dtype=np.float64)
    for i, c in enumerate(("red", "green", "blue")):
        if c in names:
            colors[:, i] = np.asarray(vertex[c], dtype=np.float64) / (255.0 if np.max(vertex[c]) > 1.0 else 1.0)
    quats = np.zeros((n, 4), dtype=np.float64); quats[:, 0] = 1.0
    qnames = [("rot_0", 0), ("rot_1", 1), ("rot_2", 2), ("rot_3", 3)]
    if all(k in names for k, _ in qnames):
        quats = np.stack([vertex[k] for k, _ in qnames], axis=1).astype(np.float64)
    scales = np.stack([np.asarray(vertex[f"scale_{a}"], dtype=np.float64) if f"scale_{a}" in names else np.zeros(n) for a in ("x", "y", "z")], axis=1)
    opacities = np.asarray(vertex["opacity"], dtype=np.float64) if "opacity" in names else np.zeros(n)
    sh0 = np.zeros((n, 3), dtype=np.float64)
    for i, key in enumerate(("f_dc_0", "f_dc_1", "f_dc_2")):
        if key in names: sh0[:, i] = np.asarray(vertex[key], dtype=np.float64)
    rest_keys = sorted([k for k in names if k.startswith("f_rest_")], key=lambda x: int(x.split("_")[-1]))
    sh_rest = None
    if rest_keys and len(rest_keys) % 3 == 0:
        sh_rest = np.stack([vertex[k] for k in rest_keys], axis=1).reshape((n, -1, 3)).astype(np.float64)
    degree = int(round(math.sqrt((sh_rest.shape[1] + 1) if sh_rest is not None else 1) - 1)) if sh_rest is not None else 0
    return {"xyz": xyz, "quats": quats, "scales": scales, "opacities": opacities,
            "sh0": sh0, "sh_rest": sh_rest, "sh_degree": max(degree, 0), "n_vertices": n}


def load_pt_bytes(data: bytes) -> Dict[str, Any]:
    if torch is None:
        raise RuntimeError("PyTorch is required to read .pt files. Install torch first.")
    obj = torch.load(io.BytesIO(data), map_location="cpu", weights_only=False)
    if isinstance(obj, dict) and "frames" in obj and isinstance(obj["frames"], (list, tuple)):
        obj = obj["frames"][0]
    if isinstance(obj, (list, tuple)) and obj and isinstance(obj[0], (dict, tuple, list)):
        obj = obj[0]
    def to_np(v):
        return v.detach().cpu().numpy() if hasattr(v, "detach") else v
    if isinstance(obj, dict):
        obj = {k: to_np(v) for k, v in obj.items()}
    return _normalise_frame(obj)


def _serialize_part(pid: int, part: Dict[str, Any]) -> Dict[str, Any]:
    return {"id": pid, "name": part["name"], "color": part["color"], "pivot": part["pivot"],
            "count": len(part.get("vertex_indices", set())), "is_4dgs": bool(part.get("is_4dgs", False))}


def state_summary() -> Dict[str, Any]:
    with STATE_LOCK:
        return {"loaded": STATE["loaded"], "filename": STATE["filename"], "n_vertices": STATE["n_vertices"],
                "num_frames": STATE["num_frames"], "interpolation_method": STATE["interpolation_method"],
                "export_progress": STATE["export_progress"], "parts": [_serialize_part(k, v) for k, v in STATE["parts"].items()],
                "tracks": {str(k): v for k, v in STATE["tracks"].items()},
                "has_4dgs": bool(STATE["4dgs_parts"])}


def _color_for(pid: int) -> List[float]:
    palette = [[0.20, 0.75, 1.0], [1.0, 0.38, 0.28], [0.42, 0.95, 0.50], [1.0, 0.78, 0.20], [0.75, 0.42, 1.0]]
    return palette[pid % len(palette)]


def _key_rotation(key: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray]:
    rx, ry, rz = [float(key.get(k, 0)) for k in ("rx", "ry", "rz")]
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    R = np.array([[cz*cy, cz*sy*sx-sz*cx, cz*sy*cx+sz*sx], [sz*cy, sz*sy*sx+cz*cx, sz*sy*cx-cz*sx], [-sy, cy*sx, cy*cx]])
    # Same ZYX convention as the rotation matrix above, stored as wxyz.
    q = np.array([math.cos(rz/2)*math.cos(ry/2)*math.cos(rx/2) + math.sin(rz/2)*math.sin(ry/2)*math.sin(rx/2),
                  math.cos(rz/2)*math.cos(ry/2)*math.sin(rx/2) - math.sin(rz/2)*math.sin(ry/2)*math.cos(rx/2),
                  math.cos(rz/2)*math.sin(ry/2)*math.cos(rx/2) + math.sin(rz/2)*math.cos(ry/2)*math.sin(rx/2),
                  math.sin(rz/2)*math.cos(ry/2)*math.cos(rx/2) - math.cos(rz/2)*math.sin(ry/2)*math.sin(rx/2)])
    return R, q


def _transform_xyz(xyz: np.ndarray, pivot: List[float], key: Dict[str, float]) -> np.ndarray:
    p = np.asarray(pivot, dtype=np.float64)
    t = np.asarray([key.get("tx", 0), key.get("ty", 0), key.get("tz", 0)], dtype=np.float64)
    R, _ = _key_rotation(key)
    return (xyz - p) @ R.T + p + t


def _rotate_quats(quats: np.ndarray, key: Dict[str, float]) -> np.ndarray:
    """Apply the Part's Euler rotation to wxyz source quaternions."""
    _, r = _key_rotation(key)
    q = np.asarray(quats, dtype=np.float64)
    if len(q) == 0:
        return q.copy()
    w1, x1, y1, z1 = r
    w2, x2, y2, z2 = q.T
    out = np.column_stack((w1*w2-x1*x2-y1*y2-z1*z2, w1*x2+x1*w2+y1*z2-z1*y2,
                           w1*y2-x1*z2+y1*w2+z1*x2, w1*z2+x1*y2-y1*x2+z1*w2))
    norm = np.linalg.norm(out, axis=1, keepdims=True)
    return out / np.maximum(norm, 1e-12)


def _key_for(pid: int, frame: int) -> Dict[str, float]:
    keys = sorted(STATE["tracks"].get(pid, []), key=lambda x: x["frame"])
    if not keys: return {"tx": 0, "ty": 0, "tz": 0, "rx": 0, "ry": 0, "rz": 0}
    if frame <= keys[0]["frame"]: return keys[0]
    if frame >= keys[-1]["frame"]: return keys[-1]
    for a, b in zip(keys, keys[1:]):
        if a["frame"] <= frame <= b["frame"]:
            u = (frame - a["frame"]) / max(1, b["frame"] - a["frame"])
            if STATE["interpolation_method"] == "catmull-rom" and len(keys) >= 4:
                i = keys.index(a); p0, p3 = keys[max(0, i-1)], keys[min(len(keys)-1, i+2)]
                out = {"frame": frame}
                for k in ("tx", "ty", "tz", "rx", "ry", "rz"):
                    v0, v1, v2, v3 = p0[k], a[k], b[k], p3[k]
                    out[k] = 0.5 * ((2*v1) + (-v0+v2)*u + (2*v0-5*v1+4*v2-v3)*u*u + (-v0+3*v1-3*v2+v3)*u*u*u)
                return out
            return {"frame": frame, **{k: a.get(k, 0) * (1-u) + b.get(k, 0) * u for k in ("tx", "ty", "tz", "rx", "ry", "rz")}}
    return keys[-1]


def _write_pt(path: str, frame: Dict[str, Any]) -> None:
    if torch is None: raise RuntimeError("PyTorch is required for export")
    payload = {"xyz": torch.from_numpy(np.asarray(frame["xyz"], dtype=np.float32)),
               "quats": torch.from_numpy(np.asarray(frame["quats"], dtype=np.float32)),
               "scales": torch.from_numpy(np.asarray(frame["scales"], dtype=np.float32)),
               "opacities": torch.from_numpy(np.asarray(frame["opacities"], dtype=np.float32)),
               "sh0": torch.from_numpy(np.asarray(frame["sh0"], dtype=np.float32)),
               "sh_degree": int(frame.get("sh_degree", 0))}
    if frame.get("sh_rest") is not None: payload["sh_rest"] = torch.from_numpy(np.asarray(frame["sh_rest"], dtype=np.float32))
    torch.save(payload, path)


def frame_data(frame: int) -> Dict[str, Any]:
    with STATE_LOCK:
        xyzs, quats, scales, opacities, sh0s, rests, cols, ids, source_indices = [], [], [], [], [], [], [], [], []
        for pid, part in STATE["parts"].items():
            if part.get("is_4dgs"):
                info = STATE["4dgs_parts"].get(pid); src = info["frames"][frame % len(info["frames"])] if info and info["frames"] else None
                if src is None: continue
                idx = None
            else:
                idx = sorted(part.get("vertex_indices", set()))
                if not idx or STATE["xyz"] is None: continue
                src = {k: STATE[k][idx] if k != "sh_rest" and STATE[k] is not None else (STATE[k][idx] if STATE[k] is not None else None)
                       for k in ("xyz", "quats", "scales", "opacities", "sh0", "sh_rest")}
                src["sh_degree"] = STATE["sh_degree"]
            key = _key_for(pid, frame)
            xyzs.append(_transform_xyz(src["xyz"], part["pivot"], key)); quats.append(_rotate_quats(src["quats"], key))
            scales.append(src["scales"]); opacities.append(src["opacities"]); sh0s.append(src["sh0"])
            rests.append(src.get("sh_rest")); cols.append(np.tile(part["color"], (len(src["xyz"]), 1))); ids.append(np.full(len(src["xyz"]), pid))
            source_indices.append(np.asarray(idx, dtype=np.int32) if idx is not None else np.full(len(src["xyz"]), -1))
        if not xyzs:
            return {"xyz": np.zeros((0,3)), "quats": np.zeros((0,4)), "scales": np.zeros((0,3)), "opacities": np.zeros(0),
                    "sh0": np.zeros((0,3)), "sh_rest": None, "sh_degree": 0, "colors": np.zeros((0,3)), "part_ids": np.zeros(0, dtype=np.int32), "source_indices": np.zeros(0, dtype=np.int32), "frame": frame}
        valid_rests = [r for r in rests if r is not None]
        rest_shape = valid_rests[0].shape[1:] if valid_rests else None
        combined_rest = np.concatenate(rests, axis=0) if rest_shape and all(r is not None and r.shape[1:] == rest_shape for r in rests) else None
        return {"xyz": np.concatenate(xyzs), "quats": np.concatenate(quats), "scales": np.concatenate(scales), "opacities": np.concatenate(opacities),
                "sh0": np.concatenate(sh0s), "sh_rest": combined_rest, "sh_degree": max([STATE["sh_degree"]] + [STATE["4dgs_parts"][p]["sh_degree"] for p in STATE["4dgs_parts"]]),
                "colors": np.concatenate(cols), "part_ids": np.concatenate(ids), "source_indices": np.concatenate(source_indices), "frame": frame}


def frame_payload(frame: int) -> Dict[str, Any]:
    data = frame_data(frame)
    return {"xyz": data["xyz"].astype(float).tolist(), "colors": data["colors"].astype(float).tolist(),
            "part_ids": data["part_ids"].astype(int).tolist(), "source_indices": data["source_indices"].astype(int).tolist(), "frame": frame}


@app.get("/")
def index(): return HTML_PAGE

@app.get("/api/state")
def api_state(): return jsonify(state_summary())

@app.get("/api/frame/<int:frame>")
def api_frame(frame): return jsonify(frame_payload(max(0, min(frame, STATE["num_frames"] - 1))))

@app.post("/api/upload")
def api_upload():
    files = request.files.getlist("files")
    if not files: return jsonify({"error": "没有收到文件"}), 400
    parsed_files = []
    try:
        for uploaded in files:
            data = uploaded.read()
            ext = os.path.splitext(uploaded.filename)[1].lower()
            if ext not in (".ply", ".pt"):
                continue
            parsed_files.append((uploaded.filename, load_ply_bytes(data) if ext == ".ply" else load_pt_bytes(data)))
    except Exception as exc: return jsonify({"error": str(exc)}), 400
    if not parsed_files: return jsonify({"error": "没有有效的 .ply 或 .pt 文件"}), 400
    first = parsed_files[0][0]
    parsed = {}
    parsed["xyz"] = np.concatenate([p["xyz"] for _, p in parsed_files], axis=0)
    parsed["quats"] = np.concatenate([p["quats"] for _, p in parsed_files], axis=0)
    parsed["scales"] = np.concatenate([p["scales"] for _, p in parsed_files], axis=0)
    parsed["opacities"] = np.concatenate([p["opacities"] for _, p in parsed_files], axis=0)
    parsed["sh0"] = np.concatenate([p["sh0"] for _, p in parsed_files], axis=0)
    rest_shapes = [p["sh_rest"].shape[1:] for _, p in parsed_files if p["sh_rest"] is not None]
    if len(rest_shapes) == len(parsed_files) and len(set(rest_shapes)) == 1:
        parsed["sh_rest"] = np.concatenate([p["sh_rest"] for _, p in parsed_files], axis=0)
    else:
        parsed["sh_rest"] = None
    parsed["sh_degree"] = max(p["sh_degree"] for _, p in parsed_files)
    parsed["n_vertices"] = len(parsed["xyz"])
    with STATE_LOCK:
        for key in ("xyz", "quats", "scales", "opacities", "sh0", "sh_rest"): STATE[key] = parsed[key]
        STATE["sh_degree"], STATE["n_vertices"], STATE["filename"], STATE["loaded"] = parsed["sh_degree"], parsed["n_vertices"], first, True
        STATE["part_id_array"] = np.full(parsed["n_vertices"], -1, dtype=np.int32); STATE["parts"].clear(); STATE["tracks"].clear(); STATE["4dgs_parts"].clear(); STATE["next_part_id"] = 0
        offset = 0
        for filename, source in parsed_files:
            count = source["n_vertices"]
            pid = STATE["next_part_id"]; STATE["next_part_id"] += 1
            indices = set(range(offset, offset + count))
            STATE["parts"][pid] = {"name": os.path.splitext(filename)[0], "color": _color_for(pid),
                                    "pivot": np.mean(parsed["xyz"][offset:offset + count], axis=0).tolist() if count else [0, 0, 0],
                                    "vertex_indices": indices}
            STATE["part_id_array"][list(indices)] = pid
            offset += count
    return jsonify(state_summary())

@app.post("/api/create-part")
def api_create_part():
    body = request.get_json(force=True); indices = sorted(set(int(i) for i in body.get("indices", [])))
    with STATE_LOCK:
        if not STATE["loaded"]: return jsonify({"error": "请先上传点云"}), 400
        indices = [i for i in indices if 0 <= i < STATE["n_vertices"]]
        pid = STATE["next_part_id"]; STATE["next_part_id"] += 1; pivot = np.mean(STATE["xyz"][indices], axis=0).tolist() if indices else [0,0,0]
        # A static point has exactly one owner, otherwise splitting a Part
        # would render and export the same point more than once.
        for existing in STATE["parts"].values():
            if not existing.get("is_4dgs"):
                existing.get("vertex_indices", set()).difference_update(indices)
        STATE["parts"][pid] = {"name": body.get("name") or f"Part {pid}", "color": _color_for(pid), "pivot": pivot, "vertex_indices": set(indices)}
        if STATE["part_id_array"] is not None: STATE["part_id_array"][indices] = pid
    return jsonify(state_summary())

@app.post("/api/part/<int:pid>")
def api_part(pid):
    body = request.get_json(force=True)
    with STATE_LOCK:
        if pid not in STATE["parts"]: return jsonify({"error": "part not found"}), 404
        part = STATE["parts"][pid]
        if "name" in body: part["name"] = str(body["name"])
        if "pivot" in body: part["pivot"] = [float(x) for x in body["pivot"][:3]]
        if "color" in body: part["color"] = [float(x) for x in body["color"][:3]]
    return jsonify(state_summary())

@app.post("/api/keyframes")
def api_keyframes():
    body = request.get_json(force=True); pid = int(body.get("pid", -1)); keys = body.get("keyframes", [])
    with STATE_LOCK:
        if pid not in STATE["parts"]: return jsonify({"error": "part not found"}), 404
        clean = []
        for k in keys:
            clean.append({"frame": max(0, min(int(k.get("frame", 0)), STATE["num_frames"]-1)), **{n: float(k.get(n, 0)) for n in ("tx", "ty", "tz", "rx", "ry", "rz")}})
        STATE["tracks"][pid] = sorted(clean, key=lambda x: x["frame"])
    return jsonify(state_summary())

@app.post("/api/settings")
def api_settings():
    body = request.get_json(force=True)
    with STATE_LOCK:
        STATE["num_frames"] = max(1, min(10000, int(body.get("num_frames", STATE["num_frames"]))))
        STATE["interpolation_method"] = body.get("interpolation_method", STATE["interpolation_method"])
    return jsonify(state_summary())

@app.post("/api/import-4dgs")
def api_import_4dgs():
    files = request.files.getlist("files"); names = request.form.getlist("filenames") or [f.filename for f in files]
    if not files: return jsonify({"error": "请选择 .pt 帧序列"}), 400
    frames = []
    try:
        for f in files:
            if os.path.splitext(f.filename)[1].lower() != ".pt": continue
            frames.append(load_pt_bytes(f.read()))
    except Exception as exc: return jsonify({"error": str(exc)}), 400
    if not frames: return jsonify({"error": "没有有效的 .pt 文件"}), 400
    with STATE_LOCK:
        pid = STATE["next_part_id"]; STATE["next_part_id"] += 1; base = frames[0]
        STATE["parts"][pid] = {"name": request.form.get("name") or f"4DGS Part {pid}", "color": _color_for(pid), "pivot": np.mean(base["xyz"], axis=0).tolist() if base["n_vertices"] else [0,0,0], "vertex_indices": set(), "is_4dgs": True}
        STATE["4dgs_parts"][pid] = {"frames": frames, "n_frames_src": len(frames), "sh_degree": base["sh_degree"], "loop": True, "filenames": names}
        STATE["tracks"][pid] = []
    return jsonify(state_summary())

@app.post("/api/export/current")
def api_export_current():
    if torch is None: return jsonify({"error": "PyTorch 未安装，无法导出"}), 400
    frame = int((request.get_json(silent=True) or {}).get("frame", 0)); payload = frame_payload(frame)
    path = os.path.join(EXPORT_ROOT, f"frame_{frame:04d}.pt")
    _write_pt(path, frame_data(frame)); return jsonify({"path": path, "filename": os.path.basename(path), "download": f"/api/download/current/{frame}"})

@app.post("/api/export/all")
def api_export_all():
    if torch is None: return jsonify({"error": "PyTorch 未安装，无法导出"}), 400
    def worker():
        with STATE_LOCK: STATE["export_progress"] = 0; count = STATE["num_frames"]
        out = tempfile.mkdtemp(prefix="4dgs_export_", dir=EXPORT_ROOT)
        for i in range(count):
            _write_pt(os.path.join(out, f"frame_{i:04d}.pt"), frame_data(i))
            with STATE_LOCK: STATE["export_progress"] = int((i+1)*100/count)
        with STATE_LOCK: STATE["export_dir"] = out
    threading.Thread(target=worker, daemon=True).start(); return jsonify({"started": True})

@app.get("/api/export/progress")
def api_export_progress():
    with STATE_LOCK: return jsonify({"progress": STATE["export_progress"], "dir": STATE["export_dir"]})


@app.get("/api/download/current/<int:frame>")
def api_download_current(frame):
    path = os.path.join(EXPORT_ROOT, f"frame_{frame:04d}.pt")
    if not os.path.isfile(path): return jsonify({"error": "文件尚未导出"}), 404
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


@app.get("/api/download/all")
def api_download_all():
    with STATE_LOCK: export_dir = STATE["export_dir"]
    if not export_dir or not os.path.isdir(export_dir): return jsonify({"error": "尚未完成全部帧导出"}), 404
    zip_path = os.path.join(EXPORT_ROOT, "4dgs_animation_frames.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(os.listdir(export_dir)):
            if name.endswith(".pt"): archive.write(os.path.join(export_dir, name), name)
    return send_file(zip_path, as_attachment=True, download_name="4dgs_animation_frames.zip")


HTML_PAGE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Part-Level 4DGS Animation Editor</title>
<style>
:root{--bg:#0b1020;--panel:#121a2b;--panel2:#18233a;--line:#273650;--text:#e7edf7;--muted:#8fa1bf;--accent:#43b7ff;--good:#48d597;--danger:#ff6b6b}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.4 system-ui,-apple-system,Segoe UI,sans-serif;overflow:hidden}button,input,select{font:inherit;color:inherit}button{border:1px solid var(--line);background:#1c2a43;padding:8px 11px;border-radius:5px;cursor:pointer}button:hover{border-color:var(--accent);background:#233856}.app{height:100vh;display:grid;grid-template-columns:280px 1fr 320px;grid-template-rows:58px 1fr 190px}.top{grid-column:1/-1;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:16px;padding:0 18px;background:#0f1729}.brand{font-weight:700;letter-spacing:.3px;font-size:16px}.status{color:var(--muted);font-size:12px}.toolbar{margin-left:auto;display:flex;gap:8px}.side{background:var(--panel);padding:14px;border-right:1px solid var(--line);overflow:auto}.right{background:var(--panel);padding:14px;border-left:1px solid var(--line);overflow:auto}.section{border-bottom:1px solid var(--line);padding-bottom:15px;margin-bottom:15px}.section h3{margin:0 0 10px;font-size:13px;color:#c3d1e8}.row{display:flex;gap:7px;align-items:center;margin:7px 0}.row>*{min-width:0}.grow{flex:1}.small{font-size:12px;color:var(--muted)}input[type=text],input[type=number],select{width:100%;background:#0c1425;border:1px solid var(--line);border-radius:4px;padding:7px}.file{width:100%;border:1px dashed #385071;padding:10px;border-radius:5px}.part{display:flex;align-items:center;gap:8px;padding:8px;border:1px solid transparent;border-radius:5px;cursor:pointer}.part:hover,.part.active{background:var(--panel2);border-color:var(--line)}.swatch{width:11px;height:11px;border-radius:50%}.viewport{position:relative;min-width:0;background:#080d18}.viewport canvas{display:block;width:100%;height:100%}.hint{position:absolute;left:14px;top:12px;color:var(--muted);font-size:12px;pointer-events:none}.selection{position:absolute;border:1px dashed var(--accent);background:rgba(67,183,255,.12);pointer-events:none;display:none}.timeline{grid-column:1/-1;border-top:1px solid var(--line);background:#0f1729;padding:12px 18px;display:flex;flex-direction:column;gap:10px}.timeline-head{display:flex;align-items:center;gap:10px}.timeline-head input{width:80px}.track{height:36px;position:relative;background:#0b1220;border:1px solid var(--line);border-radius:4px}.ticks{display:flex;justify-content:space-between;color:var(--muted);font-size:10px;padding:3px 5px}.key{position:absolute;top:17px;width:9px;height:9px;background:var(--accent);transform:translateX(-50%) rotate(45deg)}.playhead{position:absolute;top:0;bottom:0;width:2px;background:var(--danger);transform:translateX(-50%)}.kv{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.kv label{font-size:11px;color:var(--muted)}.kv input{margin-top:2px}.log{font-size:12px;color:var(--muted);white-space:pre-wrap;max-height:80px;overflow:auto}
@media(max-width:1000px){.app{grid-template-columns:220px 1fr;grid-template-rows:58px 1fr 190px}.right{display:none}}
</style></head><body><div class="app"><header class="top"><div class="brand">Part-Level 4DGS Animation Editor</div><div id="status" class="status">未加载点云</div><div class="toolbar"><button id="uploadBtn">上传 PLY / PT</button><button id="importBtn">导入 4DGS 帧</button><button id="exportCurrent">导出当前帧</button><button id="exportAll">导出全部帧</button></div></header>
<aside class="side"><div class="section"><h3>数据</h3><input id="fileInput" class="file" type="file" multiple accept=".ply,.pt"><input id="frameInput" class="file" type="file" multiple accept=".pt" webkitdirectory directory style="display:none"><div id="progress" class="small"></div></div><div class="section"><h3>Parts</h3><div id="parts"></div><button id="newPart" style="width:100%;margin-top:8px">从选区创建 Part</button></div><div class="section"><h3>视图</h3><div class="row"><label class="grow">点大小 <input id="pointSize" type="range" min="1" max="12" step=".5" value="3"></label></div><div class="row"><button id="resetView" class="grow">重置视角</button><button id="clearSelection">清除选区</button></div></div><div class="section"><h3>日志</h3><div id="log" class="log"></div></div></aside>
<main id="viewport" class="viewport"><div class="hint">拖拽矩形框选点 · 左键旋转 · 右键平移 · 滚轮缩放</div><div id="selection" class="selection"></div></main>
<aside class="right"><div class="section"><h3>Part 属性</h3><div class="row"><label class="grow small">名称<input id="partName" type="text"></label></div><div class="small">Pivot</div><div class="kv"><label>X<input id="px" type="number" step=".01"></label><label>Y<input id="py" type="number" step=".01"></label><label>Z<input id="pz" type="number" step=".01"></label></div><button id="savePart" style="margin-top:8px;width:100%">保存属性</button></div><div class="section"><h3>关键帧</h3><div class="row"><label class="grow small">帧<input id="kfFrame" type="number" min="0" value="0"></label><button id="addKey">添加/更新关键帧</button></div><div class="small">平移</div><div class="kv"><label>X<input id="tx" type="number" step=".01" value="0"></label><label>Y<input id="ty" type="number" step=".01" value="0"></label><label>Z<input id="tz" type="number" step=".01" value="0"></label></div><div class="small" style="margin-top:8px">旋转 (弧度)</div><div class="kv"><label>X<input id="rx" type="number" step=".01" value="0"></label><label>Y<input id="ry" type="number" step=".01" value="0"></label><label>Z<input id="rz" type="number" step=".01" value="0"></label></div><div id="keyList" class="small" style="margin-top:8px"></div></div><div class="section"><h3>动画设置</h3><div class="row"><label class="grow small">总帧数<input id="numFrames" type="number" min="1" max="10000" value="30"></label><label class="grow small">插值<select id="interp"><option value="linear">Linear</option><option value="catmull-rom">Catmull-Rom</option></select></label></div><button id="saveSettings" style="width:100%">应用设置</button></div></aside>
<section class="timeline"><div class="timeline-head"><button id="play">播放</button><button id="stop">停止</button><span>当前帧</span><input id="currentFrame" type="number" min="0" value="0"><input id="scrub" class="grow" type="range" min="0" max="29" value="0"><span id="frameLabel" class="small">0 / 29</span></div><div id="track" class="track"><div class="ticks"><span>0</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div><div id="playhead" class="playhead" style="left:0%"></div></div></section></div>
<script src="/static/three.min.js"></script><script src="/static/OrbitControls.js"></script><script>
const $=id=>document.getElementById(id); let state={parts:[],tracks:{},num_frames:30}; let selectedPid=null, selectedIndices=[], visibleSourceIndices=[], points, scene, camera, renderer, controls, animTimer=null, drag=null;
function log(s){$('log').textContent=new Date().toLocaleTimeString()+' '+s+'\n'+$('log').textContent}
async function api(url,opts={}){const r=await fetch(url,opts); const d=await r.json(); if(!r.ok) throw Error(d.error||r.statusText); return d}
async function refresh(){state=await api('/api/state'); $('status').textContent=state.loaded?`${state.filename} · ${state.n_vertices} 点`:'未加载点云'; $('numFrames').value=state.num_frames; $('interp').value=state.interpolation_method; $('scrub').max=Math.max(0,state.num_frames-1); renderParts(); renderTrack(); loadFrame(+$('currentFrame').value||0)}
function renderParts(){ $('parts').innerHTML=''; state.parts.forEach(p=>{const d=document.createElement('div');d.className='part '+(p.id===selectedPid?'active':'');d.onclick=()=>selectPart(p.id);d.innerHTML=`<span class="swatch" style="background:rgb(${p.color.map(x=>x*255).join(',')})"></span><span class="grow">${p.name}</span><span class="small">${p.count}</span>`;$('parts').appendChild(d)}) }
function selectPart(pid){selectedPid=pid;const p=state.parts.find(x=>x.id===pid);if(!p)return;$('partName').value=p.name;['x','y','z'].forEach((a,i)=>$('p'+a).value=p.pivot[i]);renderParts();renderKeyList()}
function renderKeyList(){const ks=state.tracks[String(selectedPid)]||[];$('keyList').innerHTML=ks.length?ks.map(k=>`帧 ${k.frame}: T(${k.tx.toFixed(2)}, ${k.ty.toFixed(2)}, ${k.tz.toFixed(2)}) R(${k.rx.toFixed(2)}, ${k.ry.toFixed(2)}, ${k.rz.toFixed(2)})`).join('<br>'):'暂无关键帧'}
function renderTrack(){const t=$('track');t.querySelectorAll('.key').forEach(x=>x.remove());if(selectedPid===null)return;(state.tracks[String(selectedPid)]||[]).forEach(k=>{const e=document.createElement('div');e.className='key';e.style.left=(k.frame/Math.max(1,state.num_frames-1)*100)+'%';t.appendChild(e)})}
function init3d(){scene=new THREE.Scene();scene.background=new THREE.Color(0x080d18);camera=new THREE.PerspectiveCamera(55,1,.01,10000);camera.up.set(0,0,1);camera.position.set(3,-4,2.5);renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(devicePixelRatio);$('viewport').appendChild(renderer.domElement);controls=new THREE.OrbitControls(camera,renderer.domElement);controls.target.set(0,0,0);scene.add(new THREE.GridHelper(20,20,0x385071,0x1b2940));scene.children[0].rotation.x=Math.PI/2;window.addEventListener('resize',resize);resize();renderer.setAnimationLoop(()=>renderer.render(scene,camera));renderer.domElement.addEventListener('pointerdown',startDrag);renderer.domElement.addEventListener('pointermove',moveDrag);renderer.domElement.addEventListener('pointerup',endDrag)}
function resize(){const r=$('viewport').getBoundingClientRect();camera.aspect=r.width/r.height;camera.updateProjectionMatrix();renderer.setSize(r.width,r.height)}
function startDrag(e){if(e.button!==0)return;drag={x:e.offsetX,y:e.offsetY};$('selection').style.display='block';$('selection').style.left=e.offsetX+'px';$('selection').style.top=e.offsetY+'px';$('selection').style.width='0';$('selection').style.height='0'}
function moveDrag(e){if(!drag)return;const x=Math.min(drag.x,e.offsetX),y=Math.min(drag.y,e.offsetY),w=Math.abs(e.offsetX-drag.x),h=Math.abs(e.offsetY-drag.y);Object.assign($('selection').style,{left:x+'px',top:y+'px',width:w+'px',height:h+'px'})}
function endDrag(e){if(!drag)return;const box=$('selection').getBoundingClientRect(), rect=renderer.domElement.getBoundingClientRect();selectedIndices=[];if(points){const pos=points.geometry.attributes.position;for(let i=0;i<pos.count;i++){const v=new THREE.Vector3().fromBufferAttribute(pos,i).project(camera);const sx=rect.left+(v.x+1)*rect.width/2,sy=rect.top+(-v.y+1)*rect.height/2;if(sx>=box.left&&sx<=box.right&&sy>=box.top&&sy<=box.bottom&&visibleSourceIndices[i]>=0)selectedIndices.push(visibleSourceIndices[i])}}selectedIndices=[...new Set(selectedIndices)];log(`选中 ${selectedIndices.length} 个静态点`);drag=null}
async function loadFrame(f){if(!state.loaded&&!state.parts.length)return;try{const d=await api('/api/frame/'+f);visibleSourceIndices=d.source_indices||[];if(points)scene.remove(points);const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(d.xyz.flat(),3));geo.setAttribute('color',new THREE.Float32BufferAttribute(d.colors.flat(),3));const mat=new THREE.PointsMaterial({size:+$('pointSize').value,vertexColors:true,sizeAttenuation:true});points=new THREE.Points(geo,mat);scene.add(points);if(d.xyz.length&&!camera.userData.fitted){const b=new THREE.Box3().setFromObject(points),c=b.getCenter(new THREE.Vector3()),s=b.getSize(new THREE.Vector3()).length();controls.target.copy(c);camera.position.copy(c).add(new THREE.Vector3(s,-s,s*.7));camera.userData.fitted=true}}catch(e){log(e.message)}}
async function upload(){const fs=$('fileInput').files;if(!fs.length)return;const fd=new FormData();[...fs].forEach(f=>fd.append('files',f));$('progress').textContent='上传中…';try{await api('/api/upload',{method:'POST',body:fd});log('点云加载完成');await refresh()}catch(e){log(e.message)}$('progress').textContent=''}
async function import4d(){const fs=$('frameInput').files;if(!fs.length)return;const fd=new FormData();[...fs].sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true})).forEach(f=>{fd.append('files',f);fd.append('filenames',f.name)});try{await api('/api/import-4dgs',{method:'POST',body:fd});log('4DGS 帧序列导入完成');await refresh()}catch(e){log(e.message)}}
$('uploadBtn').onclick=()=>$('fileInput').click();$('fileInput').onchange=upload;$('importBtn').onclick=()=>$('frameInput').click();$('frameInput').onchange=import4d;$('pointSize').oninput=()=>{if(points)points.material.size=+$('pointSize').value};$('resetView').onclick=()=>{camera.userData.fitted=false;camera.position.set(3,-4,2.5);controls.target.set(0,0,0)};$('clearSelection').onclick=()=>{selectedIndices=[];$('selection').style.display='none'};
$('newPart').onclick=async()=>{if(!selectedIndices.length)return log('请先框选点');try{await api('/api/create-part',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({indices:selectedIndices})});selectedIndices=[];log('已创建新 Part');await refresh()}catch(e){log(e.message)}};
$('savePart').onclick=async()=>{if(selectedPid===null)return;try{await api('/api/part/'+selectedPid,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('partName').value,pivot:[+$('px').value,+$('py').value,+$('pz').value]})});await refresh();selectPart(selectedPid)}catch(e){log(e.message)}};
$('addKey').onclick=async()=>{if(selectedPid===null)return;const ks=[...(state.tracks[String(selectedPid)]||[])];const k={frame:+$('kfFrame').value,tx:+$('tx').value,ty:+$('ty').value,tz:+$('tz').value,rx:+$('rx').value,ry:+$('ry').value,rz:+$('rz').value};const i=ks.findIndex(x=>x.frame===k.frame);if(i>=0)ks[i]=k;else ks.push(k);try{await api('/api/keyframes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pid:selectedPid,keyframes:ks})});await refresh();selectPart(selectedPid)}catch(e){log(e.message)}};
$('saveSettings').onclick=async()=>{try{await api('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({num_frames:+$('numFrames').value,interpolation_method:$('interp').value})});await refresh()}catch(e){log(e.message)}};
$('scrub').oninput=()=>{$('currentFrame').value=$('scrub').value;$('frameLabel').textContent=`${$('scrub').value} / ${state.num_frames-1}`;movePlayhead();loadFrame(+$('scrub').value)};$('currentFrame').onchange=()=>{$('scrub').value=$('currentFrame').value;$('scrub').oninput()};function movePlayhead(){$('playhead').style.left=(+$('currentFrame').value/Math.max(1,state.num_frames-1)*100)+'%'};$('play').onclick=()=>{if(animTimer)return;animTimer=setInterval(()=>{let f=(+$('currentFrame').value+1)%state.num_frames;$('currentFrame').value=f;$('scrub').value=f;$('scrub').oninput()},100)};$('stop').onclick=()=>{clearInterval(animTimer);animTimer=null};
$('exportCurrent').onclick=async()=>{try{const d=await api('/api/export/current',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({frame:+$('currentFrame').value})});log('已导出 '+d.filename);window.location=d.download}catch(e){log(e.message)}};$('exportAll').onclick=async()=>{try{await api('/api/export/all',{method:'POST'});const poll=setInterval(async()=>{const d=await api('/api/export/progress');$('progress').textContent=d.progress>=0?`导出进度 ${d.progress}%`:'';if(d.progress>=100){clearInterval(poll);log('全部帧导出完成');window.location='/api/download/all'}} ,300)}catch(e){log(e.message)}};
init3d();refresh();
</script></body></html>'''


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5011, debug=False, threaded=True)
