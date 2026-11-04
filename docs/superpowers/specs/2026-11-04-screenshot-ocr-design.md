# 星幻OCR —— 截图取字工具设计

日期：2026-11-04 · 状态：待确认
参考：天若OCR（`D:\Other\天若ocr识别\天若ocr.exe`）、Umi-OCR
引擎：PaddleOCR（PaddlePaddle/PaddleOCR）

## 1. 一句话

按下快捷键 → 框选一块区域 → 文字识别出来、自动进剪贴板、浮出一个小窗口。

取天若的「即按即选即出」，取 Umi 的「本地离线 + PaddleOCR」。**克制**：不做批量、PDF、翻译、二维码、标注、插件。

## 2. 已定的决策

用户定：Windows；快捷键→框选→识别；设置界面可改快捷键；自动弹窗 + 自动复制；开机自启；性能优先、亚克力、默认深色；Python 技术栈；保持精简。

我方代定（可覆盖）：

| 项 | 选择 | 理由 |
|---|---|---|
| GUI | PySide6 + PyQt-Fluent-Widgets | 用户清单内；C++ 渲染，亚克力+深色开箱可用 |
| 模型 | **两档都随包**：PP-OCRv6 small（7.7M / 30 MB）+ medium（34.5M / 133 MB）；默认「自动」= GPU 用 medium、CPU 用 small | 屏幕文字 small 79.7% / medium 82.5%；包内双档免去运行时下载，用户随时可切 |
| 引擎 | **ONNX Runtime + RapidOCR 3.10**（跑的是 PaddleOCR 的 PP-OCRv6 ONNX 模型） | CPU 比 Paddle 引擎快 1.4–1.5×，输出一致；无 paddle/paddlex 依赖，打包小 |
| 设备策略 | **GPU 优先**：CUDA EP → DirectML EP → CPU EP 自动降级 | 用户要求；DirectML 覆盖任何 DX12 显卡（N/A 卡通吃），无需装 CUDA |
| Python | 3.12（`D:\Other\Python312`） | 系统 3.15 无 Paddle wheel |
| 命名 | 星幻OCR / StarHuan OCR | 与「星空汉化」同品牌；可改 |
| 配置 | `%APPDATA%\StarHuanOCR\config.json` | 不污染程序目录 |
| 打包 | PyInstaller onedir | 启动快于 onefile |
| 授权 | **开源，GPL-3.0** | 用户已定开源；PyQt-Fluent-Widgets 为 GPLv3，开源即天然合规 |
| 发布形态 | 绿色免安装 zip（主）+ 可选安装包 | 免安装最省事；不做代码签名，SmartScreen 首次会提示 |
| 更新 | 启动后静默查 GitHub Release 版本号，有新版提醒并可一键打开下载页 | 用户已定；只比对版本，不自动替换文件 |
| 构建 | 标准版（CPU）+ GPU 版（DirectML）两个 release 资产，体积差约 10 MB | GPU 版免装 CUDA、A/N/I 通吃；见 §12 |

## 3. 目标 / 非目标 / 反目标

**目标**
1. 蒙层出现 < 120 ms；框选松手到文字出现 < 500 ms（GPU）/ < 1.5 s（CPU）。
2. 识别成功即文字已在剪贴板，结果窗口同时浮出。
3. 托盘常驻、单实例；识别过程零联网。
4. 界面干净：设置项一眼看完，不做二级页面。

**非目标**：批量/PDF/长图/二维码/表格；翻译；截图标注；云同步；macOS/Linux。

**反目标**：按快捷键到蒙层肉眼可见延迟；结果窗拖动掉帧；要用户自己装 CUDA；运行时静默下载模型。

**内存**：常驻内存是软指标，不设硬门槛（ONNX Runtime 热进程 + 模型本身有数百 MB）。实测记录在案即可，若超过 700 MB 再考虑惰性卸载。

## 4. 依赖

| 组件 | 版本 |
|---|---|
| Python | 3.12.x，venv 在 `D:\444\.venv` |
| PySide6 | 与 qfluentwidgets 1.11.3 实测兼容版（初选 6.8.3，不行再降） |
| PyQt-Fluent-Widgets | 1.11.3 |
| **rapidocr** | 3.10.0 —— 纯 ONNX 封装，默认即 PP-OCRv6，模型随 wheel，无 paddlex/paddle 依赖 |
| onnxruntime | 1.31.1 —— 标准版；**不含 paddlepaddle** |
| onnxruntime-directml | 1.24.4 —— GPU 版，仅 23.9 MB（比 CPU 版多约 10 MB） |
| onnxruntime-gpu | 1.31.1（160 MB）—— 不随包分发，用户自装即自动启用 CUDA EP |

模型：**PP-OCRv6_small_det + PP-OCRv6_small_rec**（共约 30 MB）预置到 `models\`，代码用 `text_detection_model_name` / `text_recognition_model_name` 显式指定，禁止运行时联网下载。

> 注意：PaddleOCR 3.7 里 `lang` / `ocr_version` 只能选到 medium 档，要 small 必须显式传模型名；RapidOCR 侧等价做法是 `Det.model_type` / `Rec.model_type` + `ocr_version=OCRVersion.PPOCRV6`。
> 另：PaddlePaddle 3.3.1 与 PaddleOCR 3.7 在 CPU 上不兼容（`ConvertPirAttribute2RuntimeAttribute`），这也是不走 Paddle 引擎的原因之一。

## 5. 目录

```
D:\444\
  main.py                  单实例 → 日志 → QApplication → 托盘/热键/引擎预热
  app/
    config.py              Config + 默认值 + JSON 读写
    hotkey.py              RegisterHotKey + QAbstractNativeEventFilter
    capture.py             虚拟桌面截图（多屏、DPI）
    overlay.py             全屏蒙层 + 框选
    ocr/engine.py          单例 + 单工作线程队列 + 预热
    ocr/layout.py          检测框 → 行分组 → 文本
    ui/result_window.py    结果窗
    ui/settings_window.py  设置窗
    ui/tray.py             托盘
    ui/theme.py            深色 + 亚克力
    winapi.py              DWM 亚克力、DPI、自启注册表
    single_instance.py     QLocalServer
  assets/icon.ico  models/  docs/  build/StarHuanOCR.spec
```

## 6. 主流程

```
托盘常驻 ─ WM_HOTKEY → 抓虚拟桌面位图 → 每屏一个暗化蒙层
  → 拖拽框选（Esc/右键取消；<5×5 px 取消）→ 裁剪
  → 工作线程识别 → 结果窗浮出 + 写入剪贴板
```

**蒙层**：覆盖虚拟桌面（含多屏、负坐标）；背景为静态位图 + 暗色蒙版；选区内恢复原亮度（开洞），1 px 主题色边框 + 细虚线内框；左上角显示 `宽 × 高`；Esc/右键/双击空白取消。不做放大镜、不做标注工具。

**等待态（识别中）**：松手后蒙层立即收起，选区右下角浮出一个小的亚克力胶囊——旋转指示器 + 「识别中」。它只是占位，不抢焦点、不阻塞键盘。结果到达后胶囊在同一位置展开成结果窗。

- **防闪烁**：识别若在 150 ms 内返回，直接出结果窗，胶囊不出现；超过 150 ms 才淡入。宁可少一次闪现，也不要「闪一下加载态再闪一下结果」。
- 胶囊里显示的是占位骨架（三条灰条模拟文字行）而不是纯 spinner，视觉上更接近「马上就有字」。
- 识别失败（引擎异常）→ 胶囊原地变成一行错误提示 + 「重试」，不弹出模态框。

**结果窗**：无边框圆角 + 亚克力，定位在选区下方（下方空间不足则上方），跟随鼠标所在屏；与胶囊同一锚点展开，尺寸过渡不跳。内容 = 可编辑文本框（等宽字体）+ 右下角「复制」「关闭」。`Ctrl+Enter` 复制，`Esc` 关闭。识别为空时显示「未识别到文字」，不动剪贴板。

## 7. 设置（一页，四组）

- **快捷键**：截图并识别（默认 `F1`）。点一下进入录制态，按下组合键写入；拒绝裸字母/数字（须含修饰键或 F1–F12）；与系统或其他程序冲突时标红提示并保留旧键。
- 裸 F 键作为全局热键会抢占所有程序的同名快捷键（例如 F1 帮助、F4 在 Excel 里）。默认沿用 `F1`，首次启动用一次托盘气泡说明「`F1` 已被星幻OCR 接管，可在设置里改」。
- **行为**：自动复制到剪贴板（默认 开）、识别后弹出结果窗口（默认 开，关掉则只复制并托盘气泡提示）。
- **识别**：**优先使用 GPU**（默认 开）。关闭则强制 CPU。当前实际设备（CUDA / DirectML / CPU）显示在「关于」页。
- **识别精度**：自动（默认，GPU→medium / CPU→small）/ 快速（small）/ 高精度（medium）。切换即时生效，不需重启。
- **语言不做设置项**：PP-OCRv6 small 单模型覆盖中/英/日 + 46 种拉丁语系。
- **通用**：开机自启（默认 关，写 `HKCU\...\Run`）、检查更新（默认 开）、当前版本与「检查更新」按钮。
- **关于**：版本、PaddleOCR 版本、当前设备（GPU/CPU）、日志目录。

就这些，不加第二页。

## 8. 技术要点与风险

1. **热键**：`RegisterHotKey` + 原生事件过滤器，无需钩子与管理员权限。注册失败（被占用）→ 设置页标红、启动时气泡提示。
2. **多屏 / DPI**：Per-Monitor DPI Aware v2；虚拟桌面边界用 `SM_XVIRTUALSCREEN` 等；每屏独立覆盖窗口，按屏 `devicePixelRatio` 换算。最易出 bug，优先双屏 + 150% 验证。
3. **截图**：`BitBlt` + `CAPTUREBLT`（Qt `QScreen.grabWindow(0)`）。**已知限制**：D3D 独占全屏 / 受保护内容（部分播放器、DRM）会黑屏——写进说明，不做绕过。
4. **引擎**：PaddleOCR 非线程安全，单工作线程 + `queue.Queue` 串行；结果经 Qt signal 回 UI。启动后空闲时用 32×32 空白图预热，把首帧 1–3 s 藏到用户看不见的地方。
5. **模型离线**：把 PP-OCRv6 small/medium 的 ONNX 文件预置到 `models\`，用 `Det.model_path` / `Rec.model_path` 指向本地文件，确保运行期零下载。
6. **打包**：onedir，`--collect-all onnxruntime --collect-all rapidocr`，剔冗余；目标 **150–250 MB**（vs 原 Paddle 方案 400–600 MB）。GPU 版只换 onnxruntime 的那一个包。
7. **单实例**：`QLocalServer`，第二实例转发参数后退出。

## 9. 验收

1. 冷启动到托盘出现 < 3 s（预热在后台）。
2. `F1` → 蒙层 < 120 ms（基准机：双 2560×1440 @100%，共约 7.4 MP）。
3. 框选 20–50 中文字，松手到结果：GPU 版 < 500 ms；**CPU 版（主发布物）< 1.5 s**，目标 800 ms 内。
3b. 识别耗时超过 150 ms 时必须出现等待胶囊，且胶囊出现时不遮挡选区内容、不抢焦点；识别在 150 ms 内返回时不出现胶囊（无闪烁）。
4. 识别成功时剪贴板 == 文本框内容。
5. 关掉结果窗后仍在托盘，再按 `F1` 正常。
6. 改快捷键立即生效，旧键失效。
7. 自启开关正确增删注册表值。
8. 无 GPU 环境自动 CPU，不崩溃；GPU 版在无独显机器上启动也正常。
9. DPI：基准桌面为双 2560×1440 @100%；另需把单屏临时切到 150% 缩放复测框选位置与裁剪内容一致，测完改回。
10. 断网全功能正常，更新检查静默失败不弹窗。
11. 构造一个版本号更高的 release（或 mock 接口）→ 托盘气泡与「关于」页正确提示；点击能打开对应 release 页。

## 10. 实施顺序

环境 → 引擎命令行验证 → 截图+蒙层 → 结果窗+剪贴板 → 热键+托盘+单实例 → 设置+自启 → 主题打磨与多屏 → 打包验收。

## 11. 留给实施者

PySide6 小版本、亚克力实现方式（`AcrylicWindow` 或自绘 DWM blur-behind）、行合并启发式阈值、图标。


## 12. 开源与发布

**授权**：GPL-3.0（被 PyQt-Fluent-Widgets 的 GPLv3 传导）。仓库含 `LICENSE`、中文 `README.md`（含截图、快捷键说明、DPI/独占全屏等已知限制、隐私声明：**全本地推理，不联网、不收集任何数据**）。

**构建矩阵**

| 产物 | 内容 | 目标用户 |
|---|---|---|
| `StarHuanOCR-CPU.zip` | PySide6 + onnxruntime + PP-OCRv6 small | 默认下载 |
| `StarHuanOCR-GPU.zip` | 同上 + onnxruntime-directml（+10 MB） | 任何 DX12 显卡（N/A/I 通吃），免装 CUDA |

GPU 路径三级，全部在运行时自动探测，用户无需配置：

1. 装了 `onnxruntime-gpu` 且 CUDA 可用 → **CUDA EP**（最快，160 MB，用户自装）
2. 装了 `onnxruntime-directml` → **DirectML EP**（GPU 版发布物自带，任何 DX12 显卡）
3. 其余 → **CPU EP**

DirectML 已被微软标记为向 Windows ML 过渡的弃用项（ORT 停在 1.24.4），但功能稳定、体积只有 24 MB，仍是目前 Windows 上"免装 CUDA 用上 GPU"的最省事路径。**每级都要实测；任何一级失败都必须静默降级到下一级，不能崩。**

**CPU 版必须在没有 NVIDIA 显卡的机器上验证。**

**发布流程**：版本号写进 `app/__init__.py` 与「关于」页；release 附 zip + 校验和。

**自动更新（版本检查）**

- 端点：`https://api.github.com/repos/<OWNER>/<REPO>/releases/latest`，取 `tag_name`（形如 `v1.2.0`），与 `__version__` 做语义化版本比较，忽略 `-beta` 等预发布后缀（预发布明确不提示）。
- 时机：启动后延迟 10 s 首次检查；之后每 24 h 一次；设置里可手动「检查更新」。结果缓存 24 h，写进 config。
- 交付方式：**只提醒，不自动替换文件**。托盘气泡 + 「关于」页出现「发现新版本 vX.Y.Z → 查看」，点击用默认浏览器打开 Release 页面。理由：自替换运行中的 exe 在 Windows 上要处理杀软误报、文件占用、权限提升，成本与失败率远高于收益。
- 网络失败、超时（3 s）、被墙、无 release：一律静默，不弹任何错误，不影响任何功能。
- 隐私：请求只带 User-Agent 与默认 TLS，不发送任何本机信息；README 明写「检查更新是唯一联网行为，可在设置关闭」。
- `<OWNER>/<REPO>` 以常量形式集中在一处，创建仓库后填写；未填写时检查功能整体关闭。

**分发注意**：GitHub Release 的单个文件上限 2 GB，CPU 版预计 300–400 MB，无需分卷。模型随包分发，首次启动不下载。
