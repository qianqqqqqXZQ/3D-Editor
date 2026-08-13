# 项目备忘录

## 项目概述

这是一个单文件 Flask + Three.js 的 Part-Level 4DGS Animation Editor。后端状态、解析、动画、导出 API 全部位于根目录 `app.py`；前端 HTML/CSS/JavaScript 通过 `HTML_PAGE` 内嵌。

## 代码结构

- `app.py`: Flask 应用、`STATE`、PLY/PT 解析、Part/关键帧/4DGS API、内嵌编辑器
- `static/three.min.js`: Three.js r128 本地构建
- `static/OrbitControls.js`: Three.js r128 OrbitControls
- `generated/`: 当前帧与全部帧 PT 导出目录
- `project-work/`: 活文档与工作备忘录
- `Dockerfile`: Python 3.11 CPU 运行镜像
- `requirements.txt`: Flask、NumPy、PyTorch、plyfile 运行依赖
- `.dockerignore` / `.gitignore`: 排除点云输入、导出帧和本地缓存

## 运行和测试

```powershell
py -3.13 -m pip install flask numpy torch plyfile
py -3.13 app.py
py -3.13 -m py_compile app.py
```

Docker 构建与运行：

```powershell
docker build -t part-level-4dgs-editor .
docker run --rm -p 5011:5011 -v "${PWD}/generated:/app/generated" part-level-4dgs-editor
```

服务监听 `0.0.0.0:5011`，浏览器访问 `http://localhost:5011`。

## API 速查

- `GET /api/state`, `GET /api/frame/<frame>`
- `POST /api/upload`, `POST /api/import-4dgs`
- `POST /api/create-part`, `POST /api/part/<pid>`, `POST /api/keyframes`
- `POST /api/settings`
- `POST /api/export/current`, `POST /api/export/all`, `GET /api/export/progress`

## 本轮变更备忘

需求来源为附件 `pasted-text.txt`：要求提供 `load_ply`、`load_pt`、`save_frame_as_pt`、`load_4dgs_dir`、旋转/四元数、关键帧插值及从原始状态重算帧数据的公开函数。实现应保持现有 Flask API 和前端兼容，并统一返回 NumPy `float64` 数据。

本轮已完成上述接口；验证命令为 `py -3.13 -m py_compile app.py`，并使用内存 PLY/PT、目录 SH 补齐和 Flask `test_client` 做回归。
