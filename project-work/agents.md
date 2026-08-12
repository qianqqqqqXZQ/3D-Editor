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
