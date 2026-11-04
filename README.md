# 星幻OCR

Windows 截图取字工具。按下 **F1**，框选屏幕上任意区域，识别出的文字立刻进入剪贴板，并弹出一个小窗可以直接改。

- 本地离线识别，模型随包分发，识别过程**不联网**
- 基于 PaddleOCR 的 **PP-OCRv6** 模型，经 ONNX Runtime 推理
- GPU 优先：有显卡时自动走 CUDA / DirectML，没有就退回 CPU
- 托盘常驻、单实例、可改快捷键、可开机自启
- 深色界面 + 亚克力效果，GPL-3.0 开源

## 使用

1. 解压到任意目录，双击 `StarHuanOCR.exe`
2. 按 `F1`，屏幕变暗后拖拽框选
3. 松手 → 文字已复制，结果窗口浮现在选区下方

| 操作 | 说明 |
|---|---|
| `F1` | 截图并识别（可在设置里改） |
| `Esc` | 取消框选 / 关闭结果窗口 |
| 右键 / 双击 | 取消框选 |
| `Ctrl+Enter` | 复制结果并保持窗口 |

托盘菜单可截图、打开设置、退出。

## 设置

| 项 | 默认 | 说明 |
|---|---|---|
| 截图快捷键 | `F1` | 任意按键与组合键（Ctrl/Alt/Shift/Win + 字母、数字、F1–F24、PrintScreen、方向键、小键盘等）；裸键会全局接管该键 |
| 自动复制到剪贴板 | 开 | |
| 识别后弹出结果窗口 | 开 | 关掉时只复制并托盘提示 |
| 优先使用 GPU | 开 | 关闭则强制 CPU |
| 识别精度 | 自动 | 自动 = GPU 用 medium、CPU 用 small |
| 开机自启 | 关 | 写入 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` |
| 检查更新 | 开 | 唯一联网行为，可关闭 |

## 已知限制

- **独占全屏 / 受保护内容**（部分全屏播放器、DRM 视频）截不到，会得到黑屏。
- 不识别手写、艺术字、竖排文字。
- 绿色版未做代码签名，首次运行 SmartScreen 会提示「未知发布者」。
- 跨屏幕拖拽框选不支持，请在单块屏幕内框选。

## 隐私

识别全程在本机完成，不上传任何图片或文字。唯一的联网请求是检查 GitHub Releases 的最新版本号（只发送程序版本，不发送任何本机信息），可在设置中关闭。

## 从源码运行

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

模型放在 `models\`（`PP-OCRv6_{det,rec}_{small,medium}.onnx`）。

CPU 版用 `onnxruntime`；想要 GPU 把 `onnxruntime` 换成 `onnxruntime-directml`（任何 DX12 显卡）或 `onnxruntime-gpu`（需 CUDA），代码无需改动。

## 打包

```powershell
powershell -ExecutionPolicy Bypass -File build\build.ps1          # CPU 版
powershell -ExecutionPolicy Bypass -File build\build.ps1 -Gpu     # GPU 版（DirectML）
```

产物在 `dist\StarHuanOCR\`。

- CPU 版约 510 MB，GPU 版约 550 MB（含 DirectML.dll）
- 打包前会先清空 `dist\StarHuanOCR`：残留的旧 onnxruntime DLL 会让 GPU 版静默退回 CPU

## 字体

界面使用思源黑体（Noto Sans SC），随包分发于 `assets/fonts/`，SIL Open Font License 1.1。

## 许可

GPL-3.0。依赖：PySide6（LGPL-3.0）、PySide6-Fluent-Widgets（GPLv3）、RapidOCR（Apache-2.0）、ONNX Runtime（MIT）、PP-OCRv6 模型（Apache-2.0）。
