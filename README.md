# 3D-Editor

[English](#english) | [中文](#中文)

<a id="english"></a>

## English

**3D-Editor** is a browser-based, part-level editor for point clouds and 4D Gaussian Splatting (4DGS) frame sequences. It combines a Three.js viewport with a Flask API so that you can inspect a scene, split points into editable Parts, correct their pose, preview keyframed motion, compare frames, and export the corrected data.

### Features

- Load `.ply` point clouds and `.pt` gsplat checkpoints.
- Append additional `.ply` or `.pt` files into the current static workspace. Spherical-harmonic (SH) tensors are padded to a common degree when needed.
- Load a server-side directory of sorted `.pt` frames as a 4DGS Part, with optional looping when the source sequence is shorter than the editor timeline.
- Orbit, zoom, and frame the scene in a local Three.js/WebGL viewport. Switch to rectangle selection to select static vertices.
- Create, rename, recolor, delete, and reassign Parts. Each Part has a pivot that can be set to its centroid.
- Edit per-Part translation and rotation, then save keyframes over the timeline using linear or Catmull-Rom interpolation.
- Scrub or play the timeline and compare source frames with the client-side transform preview.
- Export the current transformed frame or all timeline frames as `.pt` files.

### Project Structure

| Path | Purpose |
| --- | --- |
| `app.py` | Flask server, point-cloud readers, editor state, REST API, transforms, and export logic. |
| `static/editor.html` | Active Three.js editor UI and browser-side point-cloud renderer. |
| `static/three.min.js` | Local Three.js runtime. |
| `static/OrbitControls.js` | Local orbit-camera controls for the viewport. |
| `generated/` | Default location for exported `.pt` frames and archives. |
| `project-work/` | Maintained planning and project-reference documents. |
| `requirements.txt` | Python runtime dependencies. |
| `Dockerfile` | Reproducible Python 3.11 container image. |

### Quick Start

#### Linux (Ubuntu/Debian)

The editor runs natively on 64-bit Ubuntu and Debian systems with Python 3.10 or newer.
The default dependency set does not require a GPU or CUDA toolkit for parsing and export. A
WebGL-capable browser is required for the editor viewport.

Install Python and Git, clone the repository, and create an isolated environment:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
git clone <repository-url>
cd 3D-editor
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies and run the server:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

Open [http://localhost:5011](http://localhost:5011). To use the editor from another machine on
the same network, allow TCP port `5011` through the Linux firewall and open
`http://<linux-host-ip>:5011` from that machine. The application already listens on all network
interfaces.

The published PyTorch wheels used by `requirements.txt` target mainstream glibc-based Linux
distributions. On Alpine Linux, or on an architecture other than `x86_64` or `ARM64`, use a
PyTorch installation method supported by that platform before installing the remaining requirements.

#### Local Python

Python 3.10 or newer is recommended. PyTorch must be available for `.pt` input and export; the provided requirements install the CPU-compatible dependency set.

```bash
git clone <repository-url>
cd 3D-editor
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS
source .venv/bin/activate
```

Install dependencies and start the server:

```bash
python -m pip install -r requirements.txt
python app.py
```

Open [http://localhost:5011](http://localhost:5011) in a WebGL-capable browser.

#### Docker

```bash
docker build -t 3d-editor .
docker run --rm -p 5011:5011 3d-editor
```

Then open [http://localhost:5011](http://localhost:5011). A 4DGS directory loaded through the UI must be visible inside the container, so mount it when needed:

```bash
docker run --rm -p 5011:5011 -v /path/to/frames:/data/frames 3d-editor
```

Use `/data/frames` as the server directory in the editor's **4DGS Dir** dialog.

### Basic Workflow

1. Click **Upload** and choose one or more `.ply` or `.pt` files. The first upload replaces the current workspace; **Add Files** appends to it and creates Parts for the new files.
2. Choose **Select**, drag a rectangle in the viewport, and click **Create Part**. Select a Part in the left panel to edit its name, color, or pivot.
3. Enter translation and rotation values in the **Transform** panel. Translation uses world units and rotation sliders use degrees (the API stores radians). Set a keyframe at the current timeline frame.
4. Change the frame number or press **Play** to inspect interpolated motion. Use **4DGS Dir** to add a server-side `.pt` frame sequence as a dynamic Part.
5. Use **Export Cur .pt** for one transformed frame or **Export All** for every timeline frame. The output path can be inside `generated/` or another writable directory.

### Supported Data

- **PLY:** vertex positions (`x`, `y`, `z`), optional `red`/`green`/`blue`, Gaussian rotations, scales, opacity, and spherical-harmonic fields.
- **PT:** flat or nested gsplat checkpoints containing fields such as `means`, `quats`, `scales`, `opacities`, `sh0`, and `shN`. A checkpoint containing a `frames` list uses its first frame for static upload.
- **4DGS directory:** a directory containing `.pt` files. Files are sorted by filename and treated as source frames. The editor pads SH data to the maximum degree in the sequence.

Display colors for SH-only data are derived from the DC coefficient. Part colors are shown in the viewport and are preserved in the editor state; the raw point-cloud endpoint intentionally returns source positions so transform preview remains client-side.

### API Entry Points

The UI uses the following REST endpoints, which can also be called from scripts:

- `POST /api/upload` and `POST /api/upload_append` for static files.
- `POST /api/upload_4dgs` for a server-side 4DGS directory.
- `GET /api/state`, `GET /api/pointcloud`, and `GET /api/frame/<frame>` for workspace and binary frame data.
- `GET/POST/PUT/DELETE /api/parts...` for Part management and vertex assignment.
- `GET/POST/DELETE /api/keyframes/<pid>...` for keyframes.
- `GET/PUT /api/settings` for timeline length and interpolation method.
- `POST /api/export`, `GET /api/export/status`, and `POST /api/export_current` for exports.

### Development Checks

```bash
python -m py_compile app.py
```

The project also uses Flask's test client for API regression coverage. Keep generated exports under `generated/` so source files and working documents stay easy to review.

### Background

The idea for this tool came from my internship at Pony.ai. While working on 3D reconstruction, I repeatedly found that reconstructed models were not aligned with the coordinate axes or with the LiDAR ground truth. Existing tools made it difficult to translate and rotate point clouds directly while also keeping point-cloud comparison in the same workflow. 3D-Editor is intended to close that gap with a focused editor for alignment, Part-level transforms, frame comparison, and 4DGS export.

### Acknowledgements

Thanks to Codex for providing vibe-coding support throughout the development of this tool.

<a id="中文"></a>

[English](#english) | [中文](#中文)

## 中文

**3D-Editor** 是一个基于浏览器的点云与 4D Gaussian Splatting（4DGS）分 Part 编辑器。它用 Flask 提供后端 API，用 Three.js 提供三维视口，让你可以检查场景、把点划分为可编辑 Part、修正位置和姿态、预览关键帧动画，并导出修正后的数据。

### 功能

- 加载 `.ply` 点云和 `.pt` gsplat checkpoint。
- 向当前静态工作区追加多个 `.ply` 或 `.pt` 文件；需要时会把球谐（SH）张量补齐到统一阶数。
- 从服务器目录加载按文件名排序的 `.pt` 帧序列作为 4DGS Part；当源序列短于编辑时间线时可选择循环播放。
- 在 Three.js/WebGL 视口中旋转、缩放和自动取景，并切换到矩形框选模式选择静态顶点。
- 创建、重命名、改色、删除和重新分配 Part；每个 Part 都有可设置为质心的 pivot。
- 编辑 Part 的平移和旋转，在时间线上用线性或 Catmull-Rom 插值保存关键帧。
- 拖动时间线或播放动画，比较源帧与浏览器端的变换预览。
- 将当前变换后的帧或完整时间线导出为 `.pt` 文件。

### 项目结构

| 路径 | 用途 |
| --- | --- |
| `app.py` | Flask 服务、点云读取、编辑器状态、REST API、变换和导出逻辑。 |
| `static/editor.html` | 当前使用的 Three.js 编辑器界面和浏览器端点云渲染器。 |
| `static/three.min.js` | 本地 Three.js 运行时。 |
| `static/OrbitControls.js` | 视口的轨道相机控制器。 |
| `generated/` | 默认保存导出的 `.pt` 帧和压缩包。 |
| `project-work/` | 维护中的计划和项目参考文档。 |
| `requirements.txt` | Python 运行时依赖。 |
| `Dockerfile` | 可复现的 Python 3.11 容器镜像。 |

### 快速开始 (Quick Start)

#### 本地 Python

建议使用 Python 3.10 或更高版本。读取 `.pt` 和导出功能需要 PyTorch，项目依赖文件会安装 CPU 兼容的依赖集合。

```bash
git clone <repository-url>
cd 3D-editor
python -m venv .venv
```

Windows PowerShell 激活环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

安装依赖并启动服务：

```bash
python -m pip install -r requirements.txt
python app.py
```

然后在支持 WebGL 的浏览器中打开 [http://localhost:5011](http://localhost:5011)。

#### Docker

```bash
docker build -t 3d-editor .
docker run --rm -p 5011:5011 3d-editor
```

通过界面加载 4DGS 目录时，需要把目录挂载到容器内：

```bash
docker run --rm -p 5011:5011 -v /path/to/frames:/data/frames 3d-editor
```

在编辑器的 **4DGS Dir** 对话框中填写 `/data/frames`。

### 基本流程

1. 点击 **Upload**，选择一个或多个 `.ply` 或 `.pt` 文件。第一次上传会替换当前工作区；**Add Files** 会追加文件，并为新增文件创建 Part。
2. 选择 **Select**，在视口中拖动矩形框选点，然后点击 **Create Part**。在左侧列表选择 Part 后，可以编辑名称、颜色和 pivot。
3. 在 **Transform** 面板输入平移和旋转。旋转单位是弧度。在当前时间线帧设置关键帧。
4. 修改帧号或点击 **Play** 查看插值后的运动。使用 **4DGS Dir** 可以把服务器目录中的 `.pt` 帧序列作为动态 Part 加入。
5. 使用 **Export Cur .pt** 导出当前变换帧，或使用 **Export All** 导出整个时间线。输出路径可以放在 `generated/` 或其他可写目录。

### 支持的数据格式

- **PLY：** 顶点位置（`x`、`y`、`z`），可选的 `red`/`green`/`blue`、Gaussian 旋转、尺度、不透明度和球谐字段。
- **PT：** 支持包含 `means`、`quats`、`scales`、`opacities`、`sh0`、`shN` 等字段的扁平或嵌套 gsplat checkpoint。包含 `frames` 列表的 checkpoint 在静态上传时使用第一帧。
- **4DGS 目录：** 包含多个 `.pt` 文件的目录。文件按文件名排序并作为源帧读取，SH 数据会补齐到序列中的最高阶数。

只有 SH 数据的点会根据 DC 系数计算显示颜色。Part 颜色用于视口显示并保存在编辑器状态中；原始点云接口刻意返回源位置，因此变换预览由浏览器端完成。

### API 入口

- `POST /api/upload` 和 `POST /api/upload_append`：上传静态文件。
- `POST /api/upload_4dgs`：加载服务器端 4DGS 目录。
- `GET /api/state`、`GET /api/pointcloud`、`GET /api/frame/<frame>`：获取工作区和二进制帧数据。
- `GET/POST/PUT/DELETE /api/parts...`：管理 Part 和顶点分配。
- `GET/POST/DELETE /api/keyframes/<pid>...`：管理关键帧。
- `GET/PUT /api/settings`：设置时间线长度和插值方式。
- `POST /api/export`、`GET /api/export/status`、`POST /api/export_current`：导出数据。

### 开发检查

```bash
python -m py_compile app.py
```

项目还使用 Flask test client 做 API 回归测试。请把导出物放在 `generated/`，这样源代码和工作文档更容易审阅。

### 背景 (Background)

这个工具的想法来自我在 Pony.ai 实习期间进行三维重建的经历。当时我经常发现重建模型的方向与坐标轴、LiDAR Ground Truth 并不匹配，而现有工具很难直接对点云进行平移和旋转，也缺少把点云对比放在同一工作流中的编辑能力。3D-Editor 希望用一个专注的工具解决这个问题，提供对齐、Part 级变换、帧对比和 4DGS 导出能力。

### 致谢 (Acknowledgements)

感谢 Codex 在这个工具开发过程中提供的 vibe coding 支持。
