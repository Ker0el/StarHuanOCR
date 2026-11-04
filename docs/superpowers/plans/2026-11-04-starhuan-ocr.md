# 星幻OCR 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 做出一款 Windows 托盘常驻的截图取字工具：按 `F1` → 暗色蒙层框选 → 文字进剪贴板并浮出可编辑结果小窗。

**Architecture:** 单进程 PySide6 桌面应用。截屏与框选在 GUI 线程完成（快、无阻塞），识别走一个独立工作线程串行消费队列（ONNX Runtime 会话非线程安全）。配置存 JSON，托盘承载生命周期，单实例靠 QLocalServer。UI 用 PyQt-Fluent-Widgets 深色主题 + DWM 亚克力。

**Tech Stack:** Python 3.12 · PySide6 · PyQt-Fluent-Widgets 1.11.3 · rapidocr 3.10.0 · onnxruntime 1.31.1（GPU 版换 onnxruntime-directml）· PP-OCRv6（small + medium）· pytest

**Spec:** `docs/superpowers/specs/2026-11-04-screenshot-ocr-design.md`

## Global Constraints

- 平台：Windows 10 1903+ / Windows 11。Python 3.12（`D:\Other\Python312\python.exe`），venv 在 `D:\444\.venv`。
- 依赖上限：`PySide6`、`PyQt-Fluent-Widgets==1.11.3`、`rapidocr==3.10.0`、`onnxruntime==1.31.1`、`numpy`、`pytest`、`pytest-qt`、`opencv-python-headless`。**不得引入 paddlepaddle / paddlex / opencv-python（有 GUI 版冲突）**。
- 模型：PP-OCRv6 `small` 与 `medium` 的 det+rec ONNX 全部预置在 `models\`，运行期零下载。
- 配置目录：`%APPDATA%\StarHuanOCR\`（`config.json`、`logs\`）。
- 默认值：热键 `F1`；自动复制 开；自动弹窗 开；优先 GPU 开；精度 `auto`；开机自启 关；检查更新 开。
- 所有用户可见文案为简体中文。授权 GPL-3.0。程序名「星幻OCR」。
- 不改系统全局设置、不请求管理员权限；任何 GPU / 模型 / 网络失败必须静默降级，不得崩溃。
- UI 线程不做 OCR、不阻塞 > 16 ms；识别在工作线程。

## Review Focus

以下五类输入，规格书没有逐条写死，但用户一定会碰到；每个都在 owning task 里配了测试。

1. **多显示器 + 负坐标 + 非 100% 缩放**：副屏在主屏左侧时坐标为负，框选结果必须精确对应该屏像素，否则裁出来是错的区域。
2. **极小 / 空白 / 全屏选区**：<5×5 px 视为取消；全屏选区不能卡死或在超大图上崩。
3. **热键被占用**：`RegisterHotKey` 返回失败时必须提示且保留旧键可用，不能静默失效。
4. **模型或 ONNX Runtime 缺失/损坏**：必须明确报错到托盘并禁用截图功能，而不是按 `F1` 后静默无响应。
5. **更新检查异常**（断网 / 超时 / JSON 异常 / 预发布版本）：一律静默，绝不阻塞启动或弹窗报错。

---

### Task 0: 环境、仓库与引擎基准

**Files:**
- Create: `.gitignore`, `requirements.txt`, `tools/bench_ocr.py`, `docs/decisions/ocr-engine.md`

**Interfaces:**
- Produces: 可运行的解释器 `D:\444\.venv\Scripts\python.exe`；实测数据写入 `docs/decisions/ocr-engine.md`；后续任务一律使用该 venv。

- [ ] **Step 1: 初始化仓库与虚拟环境**

```bash
cd /d/444 && git init && /d/Other/Python312/python.exe -m venv .venv
```

- [ ] **Step 2: 写 `.gitignore` 与 `requirements.txt`**

`.gitignore` 至少包含：`.venv/`、`__pycache__/`、`build/`、`dist/`、`.pytest_cache/`、`models/*.onnx`（模型走单独分发，不进 git）。

`requirements.txt` 写入 Global Constraints 里的精确版本号，一行一个。

- [ ] **Step 3: 安装依赖**

Run: `D:/444/.venv/Scripts/python.exe -m pip install -r requirements.txt`
Expected: 全部安装成功，`python -c "import rapidocr, onnxruntime, PySide6, qfluentwidgets"` 无异常。

- [ ] **Step 4: 写基准脚本 `tools/bench_ocr.py`**

脚本行为：从命令行接收一张图片路径与 `--model small|medium`、`--provider cpu|dml|cuda`，构造 RapidOCR（`OCRVersion.PPOCRV6` + 对应 `ModelType`），跑 3 次取中位数，打印 `model, provider, ms, text`。用 `time.perf_counter()` 计时，只计 `engine(img)` 调用。

- [ ] **Step 5: 跑基准并记录**

用一张真实的中英混排截图（可从 `D:\Other\天若ocr识别\识别内容` 里取一张，或现场截一张）分别测 small/cpu、medium/cpu、small/dml、medium/dml。
Run: `D:/444/.venv/Scripts/python.exe tools/bench_ocr.py shot.png --model small --provider cpu`
Expected: 打印毫秒数与识别文本。

- [ ] **Step 6: 写决策记录 `docs/decisions/ocr-engine.md`**

内容：CPU / DirectML 实测数据、所选默认档位、DirectML 是否可用。若 DirectML 无法在 ORT 1.24.4 上跑通 PP-OCRv6，明确写下「GPU 版推迟，首发仅 CPU 版」。

- [ ] **Step 7: 提交**

```bash
git add .gitignore requirements.txt tools/ docs/decisions/
git commit -m "chore: 环境搭建与 OCR 引擎基准"
```

---

### Task 1: 配置模块

**Files:**
- Create: `app/__init__.py`, `app/config.py`, `tests/test_config.py`

**Interfaces:**
- Produces:
  - `APP_NAME = "星幻OCR"`、`APP_VERSION = "0.1.0"`、`CONFIG_DIR: Path`、`CONFIG_PATH: Path`
  - `@dataclass Config`，字段与默认值：`hotkey="F1"`, `auto_copy=True`, `show_result=True`, `prefer_gpu=True`, `precision="auto"`, `autostart=False`, `check_updates=True`, `last_update_check=0.0`, `latest_known_version=""`, `first_run_done=False`
  - `load_config(path: Path = CONFIG_PATH) -> Config`
  - `save_config(cfg: Config, path: Path = CONFIG_PATH) -> None`

- [ ] **Step 1: 写失败测试**

```python
def test_load_config_returns_defaults_when_file_missing(tmp_path):
    cfg = load_config(tmp_path / "none.json")
    assert cfg.hotkey == "F1"
    assert cfg.auto_copy is True
    assert cfg.precision == "auto"

def test_save_then_load_roundtrip(tmp_path):
    p = tmp_path / "c.json"
    cfg = Config(hotkey="Ctrl+Alt+Q", auto_copy=False)
    save_config(cfg, p)
    assert load_config(p).hotkey == "Ctrl+Alt+Q"
    assert load_config(p).auto_copy is False

def test_unknown_or_corrupt_file_falls_back_to_defaults(tmp_path):
    p = tmp_path / "c.json"
    p.write_text("{ not json", encoding="utf-8")
    assert load_config(p).hotkey == "F1"

def test_unknown_keys_are_ignored(tmp_path):
    p = tmp_path / "c.json"
    p.write_text('{"hotkey": "F2", "legacy": 1}', encoding="utf-8")
    assert load_config(p).hotkey == "F2"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_config.py -v`
Expected: FAIL，`ModuleNotFoundError` 或 `NameError`

- [ ] **Step 3: 实现 `app/config.py`**

`load_config` 读 JSON 后只取 dataclass 已声明字段，破损/缺失一律回落默认值；`save_config` 写前 `mkdir(parents=True, exist_ok=True)`，用 `json.dump(..., ensure_ascii=False, indent=2)`，先写临时文件再 `os.replace` 保证原子性。

- [ ] **Step 4: 跑测试确认通过**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_config.py -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add app/config.py app/__init__.py tests/test_config.py
git commit -m "feat: 配置模块与持久化"
```

---

### Task 2: 热键解析与注册

**Files:**
- Create: `app/hotkey.py`, `tests/test_hotkey.py`

**Interfaces:**
- Produces:
  - `parse_hotkey(text: str) -> tuple[int, int]` 返回 `(modifiers, vk)`，非法输入抛 `ValueError`
  - `hotkey_to_string(mods: int, vk: int) -> str` 用于设置页回显
  - `HotkeyManager(QObject)`：`activated = Signal()`、`register(text: str) -> bool`、`unregister() -> None`、`is_registered: bool`
  - 常量 `MOD_ALT=0x1`、`MOD_CONTROL=0x2`、`MOD_SHIFT=0x4`、`MOD_WIN=0x8`、`WM_HOTKEY=0x0312`

- [ ] **Step 1: 写失败测试**

```python
def test_parse_function_key():
    assert parse_hotkey("F1") == (0, 0x70)
    assert parse_hotkey("f12") == (0, 0x7B)

def test_parse_modifier_combo():
    mods, vk = parse_hotkey("Ctrl+Alt+Q")
    assert mods == MOD_CONTROL | MOD_ALT
    assert vk == ord("Q")

def test_bare_letter_is_rejected():
    with pytest.raises(ValueError):
        parse_hotkey("Q")

def test_roundtrip_string():
    mods, vk = parse_hotkey("Ctrl+Shift+F5")
    assert hotkey_to_string(mods, vk) == "Ctrl+Shift+F5"

def test_register_returns_false_when_win32_fails(monkeypatch, qapp):
    mgr = HotkeyManager()
    monkeypatch.setattr(mgr, "_call_register", lambda mods, vk: 0)
    assert mgr.register("Ctrl+Alt+Q") is False
```

- [ ] **Step 2: 跑测试确认失败**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_hotkey.py -v`
Expected: FAIL，`ImportError`

- [ ] **Step 3: 实现 `app/hotkey.py`**

用 `ctypes.windll.user32.RegisterHotKey(None, id, mods, vk)`。`HotkeyManager` 实现 `QAbstractNativeEventFilter`，在 `nativeEventFilter` 里匹配 `WM_HOTKEY` 且 `wParam == self._id`，命中后发 `activated`。注册调用单独抽成 `_call_register(mods, vk) -> int`（内部只做 Win32 调用），便于测试注入失败。`register` 先 `unregister` 旧键，注册失败返回 `False`。`parse_hotkey` 大小写不敏感，接受 `F1`–`F12` 与 `Ctrl/Alt/Shift/Win` 组合；裸字母数字、未知键名一律 `ValueError`。

- [ ] **Step 4: 跑测试确认通过**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_hotkey.py -v`
Expected: 5 passed

- [ ] **Step 5: 手工验证注册失败路径**

写一个临时脚本对一个已被占用的组合（如 `Ctrl+C`）调 `register`，确认返回 `False` 而不是抛异常。验证后删除脚本。

- [ ] **Step 6: 提交**

```bash
git add app/hotkey.py tests/test_hotkey.py
git commit -m "feat: 全局热键解析与注册"
```

---

### Task 3: 文本排版（检测框 → 文本）

**Files:**
- Create: `app/ocr/__init__.py`, `app/ocr/layout.py`, `tests/test_layout.py`

**Interfaces:**
- Consumes: 无
- Produces: `boxes_to_text(items: list[tuple[list[list[float]], str, float]]) -> str`，`items` 是 `(四点框, 文本, 置信度)`；返回按阅读顺序拼接的多行文本。

- [ ] **Step 1: 写失败测试**

```python
def box(x, y, w, h):
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]

def test_single_line():
    assert boxes_to_text([(box(0, 0, 100, 20), "你好", 0.99)]) == "你好"

def test_two_lines_sorted_by_y():
    items = [(box(0, 40, 100, 20), "第二行", 0.9), (box(0, 0, 100, 20), "第一行", 0.9)]
    assert boxes_to_text(items) == "第一行\n第二行"

def test_same_line_sorted_by_x():
    items = [(box(120, 0, 60, 20), "世界", 0.9), (box(0, 0, 100, 20), "你好", 0.9)]
    assert boxes_to_text(items) == "你好 世界"

def test_slightly_shifted_boxes_group_into_one_line():
    items = [(box(0, 0, 100, 20), "左侧", 0.9), (box(110, 6, 100, 20), "右侧", 0.9)]
    assert boxes_to_text(items) == "左侧 右侧"

def test_empty_input_returns_empty_string():
    assert boxes_to_text([]) == ""
```

- [ ] **Step 2: 跑测试确认失败**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_layout.py -v`
Expected: FAIL，`ImportError`

- [ ] **Step 3: 实现 `app/ocr/layout.py`**

按框的 y 中心排序后分簇：与当前行 y 中心差 ≤ 行高 0.6 倍则并入同一行；行内按 x 升序；同一行内用单个空格连接；行间用 `\n` 连接。行高取该簇内框高的中位数。

- [ ] **Step 4: 跑测试确认通过**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_layout.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add app/ocr/__init__.py app/ocr/layout.py tests/test_layout.py
git commit -m "feat: 检测框按行排版"
```

---

### Task 4: OCR 引擎封装与工作线程

**Files:**
- Create: `app/ocr/engine.py`, `tests/test_engine.py`, `tests/test_engine_integration.py`

**Interfaces:**
- Consumes: `boxes_to_text`（Task 3）
- Produces:
  - `@dataclass OcrResult`: `text: str`, `elapsed_ms: int`, `device: str`, `line_count: int`
  - `choose_device(prefer_gpu: bool, available: list[str]) -> str` 纯函数，返回 `"cuda" | "dml" | "cpu"`
  - `choose_tier(precision: str, device: str) -> str` 纯函数，返回 `"small" | "medium"`
  - `OcrEngine(models_dir: Path, device: str, tier: str)`：`warmup() -> None`、`recognize(image: numpy.ndarray) -> OcrResult`、属性 `device`、`tier`
  - `OcrWorker(QObject)`：`finished = Signal(object)`、`failed = Signal(str)`、`submit(image) -> None`、`start()`、`stop()`

- [ ] **Step 1: 写失败测试（纯函数部分）**

```python
def test_cuda_wins_when_available():
    assert choose_device(True, ["CUDAExecutionProvider", "CPUExecutionProvider"]) == "cuda"

def test_dml_when_no_cuda():
    assert choose_device(True, ["DmlExecutionProvider", "CPUExecutionProvider"]) == "dml"

def test_cpu_when_gpu_disabled():
    assert choose_device(False, ["CUDAExecutionProvider"]) == "cpu"

def test_cpu_when_nothing_available():
    assert choose_device(True, []) == "cpu"

def test_auto_tier_uses_medium_on_gpu():
    assert choose_tier("auto", "cuda") == "medium"
    assert choose_tier("auto", "cpu") == "small"

def test_explicit_tier_overrides():
    assert choose_tier("fast", "cuda") == "small"
    assert choose_tier("high", "cpu") == "medium"

def test_engine_raises_clear_error_when_models_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        OcrEngine(tmp_path, device="cpu", tier="small")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_engine.py -v`
Expected: FAIL，`ImportError`

- [ ] **Step 3: 实现纯函数与 `OcrEngine`**

`choose_device` 按 `cuda > dml > cpu` 优先级在 `available` 里找。`OcrEngine.__init__` 构造 `RapidOCR`，参数为 `Det.model_type` / `Rec.model_type`（`ModelType.SMALL` / `ModelType.MEDIUM`）、`Det.ocr_version` / `Rec.ocr_version` = `OCRVersion.PPOCRV6`、`engine_type` 依据 device。模型路径显式指向 `models_dir`，禁止联网下载。`warmup()` 用 32×32 全白图跑一次。`recognize()` 内部 `try/except` 后向上抛，由 worker 转成 `failed` 信号。

- [ ] **Step 4: 跑测试确认通过**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_engine.py -v`
Expected: 7 passed

- [ ] **Step 5: 写集成测试（标记 `slow`）**

```python
@pytest.mark.slow
def test_recognizes_rendered_chinese(tmp_path):
    img = render_text_image("星幻OCR 测试", width=400, height=80)  # QImage + QPainter 白底黑字
    engine = OcrEngine(MODELS_DIR, device="cpu", tier="small")
    result = engine.recognize(img)
    assert "星幻" in result.text
```

`render_text_image` 在测试文件内用 `QImage` + `QPainter` 实现，不引入新依赖。

- [ ] **Step 6: 跑集成测试**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_engine_integration.py -v -m slow`
Expected: PASS；若模型缺失则先完成模型预置（Task 0 Step 5）

- [ ] **Step 7: 提交**

```bash
git add app/ocr/engine.py tests/test_engine.py tests/test_engine_integration.py
git commit -m "feat: OCR 引擎封装与设备/档位选择"
```

---

### Task 5: 截屏与虚拟桌面几何

**Files:**
- Create: `app/capture.py`, `tests/test_capture.py`

**Interfaces:**
- Produces:
  - `virtual_desktop_rect() -> QRect`（虚拟桌面全局矩形，可含负坐标）
  - `grab_virtual_desktop() -> QImage`
  - `crop_to_numpy(image: QImage, rect_in_image: QRect) -> numpy.ndarray`

- [ ] **Step 1: 写失败测试**

```python
def test_virtual_rect_matches_win32_metrics(qapp):
    import ctypes
    u = ctypes.windll.user32
    expected = QRect(u.GetSystemMetrics(76), u.GetSystemMetrics(77),
                     u.GetSystemMetrics(78), u.GetSystemMetrics(79))
    assert virtual_desktop_rect() == expected

def test_grab_size_matches_virtual_rect(qapp):
    assert grab_virtual_desktop().size() == virtual_desktop_rect().size()

def test_crop_returns_requested_size(qapp):
    img = QImage(200, 100, QImage.Format.Format_RGB32)
    out = crop_to_numpy(img, QRect(10, 10, 50, 20))
    assert out.shape[:2] == (20, 50)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_capture.py -v`
Expected: FAIL，`ImportError`

- [ ] **Step 3: 实现 `app/capture.py`**

用 `GetSystemMetrics(76..79)` = `SM_XVIRTUALSCREEN / SM_YVIRTUALSCREEN / SM_CXVIRTUALSCREEN / SM_CYVIRTUALSCREEN`。截屏用 `QScreen.grabWindow(0)` 逐屏合成到一张 `QImage`（按 `screen.geometry()` 相对虚拟桌面左上角偏移绘制）。`crop_to_numpy` 用 `img.copy(rect)` 转 `Format_RGB888` 后构造 `numpy` 数组，返回连续内存。

- [ ] **Step 4: 跑测试确认通过**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_capture.py -v`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add app/capture.py tests/test_capture.py
git commit -m "feat: 虚拟桌面截屏与裁剪"
```

---

### Task 6: 框选蒙层

**Files:**
- Create: `app/overlay.py`, `app/ui/__init__.py`, `tests/test_overlay_geometry.py`

**Interfaces:**
- Consumes: `virtual_desktop_rect`、`grab_virtual_desktop`（Task 5）
- Produces:
  - `normalize_selection(start: QPoint, end: QPoint, bounds: QRect) -> QRect`
  - `SelectionOverlay(QWidget)`：`selected = Signal(QRect)`、`cancelled = Signal()`、`begin(image: QImage, screen_geometry: QRect)`
  - `OverlayController(QObject)`：`start() -> None`

- [ ] **Step 1: 写失败测试（纯函数）**

```python
def test_normalize_reversed_drag():
    r = normalize_selection(QPoint(100, 80), QPoint(20, 10), QRect(0, 0, 500, 400))
    assert r == QRect(20, 10, 80, 70)

def test_normalize_clamps_to_bounds():
    r = normalize_selection(QPoint(-50, -50), QPoint(700, 700), QRect(0, 0, 500, 400))
    assert r == QRect(0, 0, 500, 400)

def test_tiny_selection_is_empty():
    assert normalize_selection(QPoint(10, 10), QPoint(13, 13), QRect(0, 0, 500, 400)).isEmpty()

def test_negative_origin_screen_preserves_global_coords():
    bounds = QRect(-1920, 0, 1920, 1080)
    r = normalize_selection(QPoint(-1900, 100), QPoint(-1000, 500), bounds)
    assert r == QRect(-1900, 100, 900, 400)

def test_full_screen_selection_is_accepted():
    r = normalize_selection(QPoint(0, 0), QPoint(500, 400), QRect(0, 0, 500, 400))
    assert r == QRect(0, 0, 500, 400)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_overlay_geometry.py -v`
Expected: FAIL，`ImportError`

- [ ] **Step 3: 实现 `normalize_selection`**

起点落点取 min/max 成矩形，与 `bounds` 求交；宽或高 < 5 px 返回 `QRect()`。

- [ ] **Step 4: 跑测试确认通过**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_overlay_geometry.py -v`
Expected: 5 passed

- [ ] **Step 5: 实现蒙层窗口**

无边框、`Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint`、`WA_DeleteOnClose`；背景绘制该屏位图 + 40% 黑色蒙版；选区内重绘原图（开洞），1 px 主题色边框 + 虚线内框；左上角绘制 `宽 × 高`。光标 `Qt.CrossCursor`。`Esc` / 右键 / 双击空白 → `cancelled`。

- [ ] **Step 6: 手工验证**

临时入口调 `OverlayController.start()`，在双屏、副屏置于左侧、单屏 150% 缩放下各验证一次选区与裁剪一致。验证后删除临时入口。

- [ ] **Step 7: 提交**

```bash
git add app/overlay.py app/ui/__init__.py tests/test_overlay_geometry.py
git commit -m "feat: 全屏蒙层与框选"
```

---

### Task 7: 结果窗口与主题

**Files:**
- Create: `app/ui/result_window.py`, `app/ui/theme.py`, `tests/test_result_window.py`

**Interfaces:**
- Consumes: `OcrResult`（Task 4）
- Produces:
  - `ResultWindow(QWidget)`：`show_result(text: str, anchor: QRect) -> None`，属性 `text_edit`
  - `LoadingChip(QWidget)`：`show_at(anchor: QRect) -> None`、`hide_chip() -> None`；无焦点、`WA_TransparentForMouseEvents`、三条骨架灰条 + 旋转指示器
  - `theme.py`：`apply_dark_theme() -> None`、`enable_acrylic(widget: QWidget) -> None`

- [ ] **Step 1: 写失败测试**

```python
def test_show_result_sets_editable_text(qtbot):
    w = ResultWindow()
    qtbot.addWidget(w)
    w.show_result("第一行\n第二行", QRect(100, 100, 200, 50))
    assert w.text_edit.toPlainText() == "第一行\n第二行"
    assert w.text_edit.isReadOnly() is False

def test_escape_hides_window(qtbot):
    w = ResultWindow()
    qtbot.addWidget(w)
    w.show_result("x", QRect(0, 0, 10, 10))
    qtbot.keyClick(w, Qt.Key.Key_Escape)
    assert w.isVisible() is False
```

- [ ] **Step 2: 跑测试确认失败**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_result_window.py -v`
Expected: FAIL，`ImportError`

- [ ] **Step 3: 实现 `app/ui/theme.py`**

`apply_dark_theme()` 调 `qfluentwidgets.setTheme(Theme.DARK)` 与 `setThemeColor`。`enable_acrylic(widget)` 用 `ctypes` 调 `SetWindowCompositionAttribute`（`ACCENT_ENABLE_ACRYLICBLURBEHIND`）；失败静默返回。

- [ ] **Step 4: 实现 `app/ui/result_window.py`**

无边框圆角；`QPlainTextEdit`（等宽字体 13 px，可编辑）+ 右下角「复制」「关闭」两个 `PushButton`。`show_result` 设置文本后按 `anchor` 定位（下方优先、空间不足翻上方、钳制在当前屏内）。`Ctrl+Enter` 复制、`Esc` 关闭。空文本显示占位「未识别到文字」且**不动剪贴板**。

`LoadingChip` 同文件实现：同样是无边框亚克力小胶囊，锚定在选区右下角，画三条 60%/80%/40% 宽的骨架灰条 + 一个 `QTimer` 驱动的旋转指示器（16 ms 步进，仅在可见时运行）。`show_at` 前先 `setFocusPolicy(Qt.NoFocus)`，不掐焦点。

- [ ] **Step 5: 跑测试确认通过**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_result_window.py -v`
Expected: 2 passed

- [ ] **Step 6: 提交**

```bash
git add app/ui/theme.py app/ui/result_window.py tests/test_result_window.py
git commit -m "feat: 结果窗口与深色亚克力主题"
```

---

### Task 8: 托盘、单实例与主流程

**Files:**
- Create: `app/ui/tray.py`, `app/single_instance.py`, `app/pipeline.py`, `main.py`, `tests/test_single_instance.py`, `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `Config`（Task 1）、`HotkeyManager`（Task 2）、`OcrWorker`（Task 4）、`OverlayController`（Task 6）、`ResultWindow`（Task 7）
- Produces:
  - `SingleInstance(QObject)`：`try_acquire(name: str) -> bool`
  - `Pipeline(QObject)`：`__init__(config, worker, overlay, window, chip, tray)`、槽 `trigger_capture()`、槽 `_on_selection(rect: QRect)`、槽 `_on_result(result: OcrResult)`、属性 `chip`
  - `TrayIcon`：信号 `capture_requested`、`settings_requested`、`quit_requested`
  - `main.py` 可执行入口

- [ ] **Step 1: 写失败测试**

```python
def test_second_instance_is_rejected(qapp):
    a = SingleInstance()
    assert a.try_acquire("starhuan-test") is True
    b = SingleInstance()
    assert b.try_acquire("starhuan-test") is False

@pytest.mark.parametrize("text", ["", "   "])
def test_pipeline_ignores_blank_result(qtbot, text, monkeypatch):
    pipe = make_pipeline()
    copied = []
    monkeypatch.setattr(pipe, "_copy", lambda t: copied.append(t))
    pipe._on_result(OcrResult(text=text, elapsed_ms=10, device="cpu", line_count=0))
    assert copied == []

def test_chip_not_left_visible_when_result_is_fast(qtbot):
    pipe = make_pipeline()
    pipe._on_selection(QRect(0, 0, 100, 50))
    pipe._on_result(OcrResult(text="你好", elapsed_ms=20, device="cpu", line_count=1))
    qtbot.wait(250)
    assert pipe.chip.isVisible() is False
```

- [ ] **Step 2: 跑测试确认失败**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_single_instance.py tests/test_pipeline.py -v`
Expected: FAIL，`ImportError`

- [ ] **Step 3: 实现单实例**

`QLocalServer` + `QLocalSocket`：`try_acquire` 先连接同名 server，连上说明已有实例（发送激活消息后返回 `False`）；连不上则 `removeServer` 后 `listen`，返回 `True`。

- [ ] **Step 4: 实现 `Pipeline`**

`trigger_capture()`：正在截图则忽略 → `overlay.start()`。`overlay.selected(rect)`：裁剪 → 隐藏旧结果窗 → `worker.submit(img)` → `QTimer.singleShot(150, 显示等待胶囊)`。`worker.finished`：取消胶囊 → 非空且 `config.auto_copy` 则写剪贴板 → `config.show_result` 则 `window.show_result`。`worker.failed`：托盘气泡提示。

- [ ] **Step 5: 实现 `app/ui/tray.py` 与 `main.py`**

托盘菜单「截图识别（F1）」「设置」「检查更新」「退出」。`main.py` 顺序：单实例 → `QApplication` → `apply_dark_theme` → 载配置 → 建 worker / overlay / window / chip / tray → 注册热键（失败则气泡提示并保留默认） → 预热 → `app.exec()`。

首次启动（`config.first_run_done is False`）用一次托盘气泡提示「`F1` 已被星幻OCR 接管，可在设置里修改」，随后置 `first_run_done=True` 并保存配置。

- [ ] **Step 6: 跑测试确认通过**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_single_instance.py tests/test_pipeline.py -v`
Expected: 5 passed

- [ ] **Step 7: 手工冒烟**

Run: `D:/444/.venv/Scripts/python.exe main.py`，按 `F1` 框选一行文字，确认剪贴板与结果窗一致；关窗后程序仍在托盘。

- [ ] **Step 8: 提交**

```bash
git add app/ui/tray.py app/single_instance.py app/pipeline.py main.py tests/
git commit -m "feat: 托盘、单实例与主流程串联"
```

---

### Task 9: 设置窗口与开机自启

**Files:**
- Create: `app/ui/settings_window.py`, `app/winapi.py`, `tests/test_winapi.py`, `tests/test_settings_window.py`

**Interfaces:**
- Consumes: `Config`、`load_config` / `save_config`（Task 1）、`parse_hotkey`（Task 2）
- Produces:
  - `autostart_command() -> str`、`set_autostart(enabled: bool, exe_path: str) -> None`、`is_autostart_enabled() -> bool`
  - `AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"`、`AUTOSTART_VALUE = "StarHuanOCR"`
  - `SettingsWindow(QWidget)`：`changed = Signal(object)`、`open(settings: Config, device: str)`、信号 `hotkey_rejected = Signal(str)`、属性 `hotkey_edit`

- [ ] **Step 1: 写失败测试**

```python
def test_autostart_command_quotes_path():
    assert autostart_command(r"C:\Program Files\StarHuanOCR\StarHuanOCR.exe") == \
        '"C:\\Program Files\\StarHuanOCR\\StarHuanOCR.exe"'

def test_set_autostart_writes_and_removes(monkeypatch):
    calls = []
    monkeypatch.setattr(winapi, "_set_run_value", lambda path, name, val: calls.append((name, val)))
    monkeypatch.setattr(winapi, "_delete_run_value", lambda path, name: calls.append((name, None)))
    set_autostart(True, "C:/x.exe")
    set_autostart(False, "C:/x.exe")
    assert calls == [("StarHuanOCR", '"C:/x.exe"'), ("StarHuanOCR", None)]

def test_settings_rejects_bare_letter_hotkey(qtbot):
    w = SettingsWindow(); qtbot.addWidget(w)
    w._apply_hotkey_text("Q")
    assert w.hotkey_edit.text() == "F1"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_winapi.py tests/test_settings_window.py -v`
Expected: FAIL，`ImportError`

- [ ] **Step 3: 实现 `app/winapi.py`**

`_set_run_value` / `_delete_run_value` 用 `winreg` 操作 `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`；值为带引号的 exe 全路径。`OSError` 吞掉并静默返回。

- [ ] **Step 4: 实现设置窗口**

一页四组（快捷键 / 行为 / 识别 / 通用）+ 关于。热键 `LineEdit` 点入录制态，`keyPressEvent` 抓组合键，非法则回显旧值并发 `hotkey_rejected`。开关用 `SwitchButton`，精度用 `ComboBox`。任何修改即时 `save_config` 并 `changed.emit(cfg)`。

- [ ] **Step 5: 跑测试确认通过**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_winapi.py tests/test_settings_window.py -v`
Expected: 3 passed

- [ ] **Step 6: 提交**

```bash
git add app/winapi.py app/ui/settings_window.py tests/
git commit -m "feat: 设置窗口与开机自启"
```

---

### Task 10: 更新检查、图标与打包

**Files:**
- Create: `app/updater.py`, `tests/test_updater.py`, `assets/icon.ico`, `README.md`, `LICENSE`, `build/StarHuanOCR.spec`, `build/build.ps1`

**Interfaces:**
- Produces:
  - `parse_version(tag: str) -> tuple[int, int, int] | None`
  - `is_newer(remote: str, local: str) -> bool`
  - `check_update(current: str, owner: str, repo: str, timeout: float = 3.0) -> str | None`
  - `REPO_OWNER`、`REPO_NAME`（空串表示关闭该功能）

- [ ] **Step 1: 写失败测试**

```python
@pytest.mark.parametrize("remote,local,expected", [
    ("v1.2.0", "1.1.9", True),
    ("1.2.0", "1.2.0", False),
    ("v1.0.0", "1.2.0", False),
    ("v1.3.0-beta.1", "1.2.0", False),
])
def test_is_newer(remote, local, expected):
    assert is_newer(remote, local) is expected

def test_check_update_returns_none_on_network_error(monkeypatch):
    monkeypatch.setattr(updater, "_get_json", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    assert check_update("1.0.0", "o", "r") is None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `D:/444/.venv/Scripts/python.exe -m pytest tests/test_updater.py -v`
Expected: FAIL，`ImportError`

- [ ] **Step 3: 实现 `app/updater.py`**

用标准库 `urllib.request`（不引入 requests），`User-Agent: StarHuanOCR/<version>`，3 秒超时；任何异常返回 `None`。含 `-` 的预发布 tag 一律视为不提示。

- [ ] **Step 4: 生成图标与文档**

`assets/icon.ico` 用 Pillow 生成深色底 + 取景框形状的多尺寸 ico。`LICENSE` 取 GPL-3.0 全文。`README.md` 写功能、快捷键、已知限制（独占全屏黑屏、SmartScreen 提示）、隐私声明（识别全本地，唯一联网为更新检查，可关）。

- [ ] **Step 5: 写 PyInstaller 配置并打包**

`build/StarHuanOCR.spec`：onedir、`--collect-all onnxruntime --collect-all rapidocr`、`datas` 含 `models/` 与 `assets/`、`icon=assets/icon.ico`、`console=False`。`build/build.ps1` 接受 `-Gpu` 开关切换 onnxruntime / onnxruntime-directml。

- [ ] **Step 6: 打包并冒烟**

Run: `powershell -ExecutionPolicy Bypass -File build/build.ps1`
Expected: `dist/StarHuanOCR/StarHuanOCR.exe` 存在，双击后托盘出现、`F1` 可用。

- [ ] **Step 7: 提交**

```bash
git add app/updater.py tests/test_updater.py assets/ README.md LICENSE build/
git commit -m "feat: 更新检查、图标与打包"
```

---

## 验收（Task 11，手工执行，逐条记录到 `docs/acceptance.md`）

- [ ] 冷启动到托盘出现 < 3 s
- [ ] `F1` → 蒙层 < 120 ms（双 2560×1440 @100%）
- [ ] 框选 20–50 中文字：CPU < 1.5 s、GPU < 500 ms
- [ ] 识别成功时剪贴板 == 文本框内容
- [ ] 识别 > 150 ms 时出现等待胶囊且不抢焦点；< 150 ms 时不闪
- [ ] 关窗后仍在托盘，再按 `F1` 正常
- [ ] 改快捷键立即生效，旧键失效；被占用组合标红
- [ ] 自启开关正确增删注册表值
- [ ] 无 GPU 机器：自动 CPU，不崩溃；GPU 版同样能启动
- [ ] 双屏（副屏置左、负坐标）+ 单屏临时 150%：框选位置与裁剪一致
- [ ] 断网：全功能正常，更新检查静默
- [ ] 空选区 / 极小选区 / 全屏选区：分别为取消、取消、正常
- [ ] 删除 `models\` 后启动：托盘提示错误而非静默无响应
