# Part-Level 4DGS Animation Editor 计划

- [x] 检查现有仓库、Python 环境和依赖状态
- [x] 建立 `project-work` 工作文档目录与 `generated` 导出目录
- [x] 在 Git 中保存实现前基线
- [x] 实现 Flask 全局 `STATE`、静态 PLY/PT 解析和多文件 Part 建立
- [x] 实现框选创建 Part、Pivot、颜色、关键帧和线性/Catmull-Rom 插值 API
- [x] 实现 4DGS `.pt` 帧序列导入、变换预览和当前/全部帧导出
- [x] 实现内嵌原生 HTML/CSS/JS Three.js 编辑器界面
- [x] 添加本地 Three.js r128 与 OrbitControls 资源
- [x] 运行 Python 编译检查与内存 API 流程测试
- [x] 回归验证 Part 拆分所有权、4DGS 叠加和 PT 完整字段导出
- [x] 启动 Flask 并验证根页面、静态资源和 `/api/state`
- [x] 添加 CPU 版 `Dockerfile`、`requirements.txt` 和 `.dockerignore`
- [ ] 执行 Docker 镜像构建验证（当前系统未安装 Docker CLI）
- [ ] 在真实浏览器中继续做视觉回归（需要用户侧浏览器/Playwright 环境）

## 运行

```powershell
py -3.13 -m pip install flask numpy torch plyfile
py -3.13 app.py
```

访问 `http://localhost:5011`。

## 验证

```powershell
py -3.13 -m py_compile app.py
```

Docker:

```powershell
docker build -t part-level-4dgs-editor .
docker run --rm -p 5011:5011 -v "${PWD}/generated:/app/generated" part-level-4dgs-editor
```

## 本轮需求：输入、动画与变换接口补齐（2026-08-13）

- [ ] 增加公开的 PLY/PT 文件加载函数及规范化字段映射
- [ ] 增加 `.pt` 帧保存函数，并兼容 gsplat 两种 checkpoint 结构
- [ ] 增加 4DGS 目录加载、帧索引、SH degree 对齐逻辑
- [ ] 增加欧拉角/矩阵/四元数与关键帧插值工具
- [ ] 增加从原始数据重算的单帧/全帧变换逻辑并接入现有 API
- [ ] 运行编译、单元级回归和 Flask API 验证
- [ ] 完成修改后的代码审查并更新本文件
