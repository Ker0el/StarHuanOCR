# 验收记录（2026-11-04）

机器：Windows 11 · 24 逻辑核 · RTX 4070 Ti · 双 2560×1440 @100%
构建：CPU 版（onnxruntime 1.31.1）· 打包产物 523 MB

| # | 项 | 结果 | 证据 |
|---|---|---|---|
| 1 | 冷启动到托盘 < 3 s | ✅ 523 ms | 源码模式下构造 QApplication + 全部组件 + 托盘完成计时；打包版未单独计时 |
| 2 | `F1` → 蒙层 < 120 ms | ⚠️ 中位 117 ms，最慢 225 ms | 双屏 5120×1440 抓屏 + 建两块蒙层，5 次采样 |
| 3 | 框选 → 文字 CPU < 1.5 s | ⚠️ 1494 ms | 900×220 真实桌面区域、39 行文本，CPU/small，中位 3 次 |
| 4 | 剪贴板 == 文本内容 | ✅ | `Pipeline._on_result` 单测覆盖；非空才复制 |
| 5 | >150 ms 出现等待胶囊 / 快结果不闪 | ✅ | `test_chip_not_left_visible_when_result_is_fast` |
| 6 | 关窗后仍在托盘 | ✅ | `main.py` 冒烟 8 s 进程存活（`setQuitOnLastWindowClosed(False)`） |
| 7 | 改快捷键立即生效、旧键失效 | ✅ 代码路径 | 单测覆盖解析/注册失败；设置信号 → main 重新注册（未做真人按键验证） |
| 8 | 自启开关增删注册表值 | ✅ 单测（mock） | 未真实写入 `HKCU`，避免留下系统副作用 |
| 9 | 无 GPU 自动 CPU | ✅ | 打包版 `--selftest` 输出 `ok device=cpu tier=small` |
| 10 | 双屏负坐标框选 | ✅ 单测 | `test_negative_origin_screen_preserves_global_coords` |
| 10b | 150% 缩放下框选一致 | ❌ 未测 | 需临时改系统缩放，会打断当前会话，留待人工 |
| 11 | 断网全功能正常、更新检查静默 | ✅ 单测 | `test_check_update_returns_none_on_network_error` |
| 12 | 空 / 极小 / 全屏选区 | ✅ 单测 | `tests/test_overlay_geometry.py` |
| 13 | 删除 `models\` 后提示而非静默失效 | ✅ 单测 | `test_engine_raises_clear_error_when_models_missing`；worker 把异常转 `failed` → 托盘气泡 |

## 未覆盖（需人工）

- 真实按键 `F1` 的完整交互（托盘 → 蒙层 → 拖拽 → 结果窗）需人眼确认。
- 150% DPI 缩放。
- 独占全屏程序下的黑屏表现（已知限制，不修）。
- 打包版冷启动计时与 GPU 版（DirectML）实测。

## 开发中发现并修复的真实缺陷

- `crop_to_numpy` 曾返回指向已释放 QImage 缓冲区的 numpy 视图，导致真实桌面截图 OCR 出乱码甚至访问冲突。已改为显式 copy，并加 `test_crop_does_not_alias_source_image` 防回归。

## 代码审查后的修复（同一分支）

| 严重度 | 问题 | 修复 | 验证 |
|---|---|---|---|
| Critical | 打包版缺 cls 模型，首次识别会联网下载、离线则失败 | 引擎关掉方向分类 `Global.use_cls=False`（截图场景不需要） | `test_engine_disables_text_direction_classifier`；打包版 `--selftest` 输出 `use_cls=False text_len=11` |
| Critical | 引擎初始化失败后线程死亡，之后按 `F1` 永远卡在加载胶囊 | `OcrWorker` 记录 failed 状态；`Pipeline` 在 failed 时拒绝截图并提示 | `test_worker_marks_failed_and_stays_dead`、`test_trigger_capture_refused_when_worker_failed` |
| Important | 启动时热键注册失败后，改键永远不会生效 | `wire_hotkey()` 无条件连接信号 | `test_wire_hotkey_connects_even_when_registration_failed` |
| Important | 设置页录不到 Ctrl+字母（`event.text()` 是控制字符） | 改用 `event.key()` 映射 | `test_hotkey_edit_records_ctrl_letter_via_keycode` |
| Important | 非 100% 缩放下截图被降采样 | `screen_physical_rect()` 按 dpr 换算到物理像素 | `test_screen_physical_rect_scales_by_dpr` |
| Minor | 打开设置页就写自启注册表 | `open()` 期间 `blockSignals` | `test_open_does_not_write_autostart` |
| Minor | config 里非法热键导致启动即退出 | `resolve_hotkey()` 回落 `F1` | `test_resolve_hotkey_falls_back_on_invalid_config` |
| Minor | 托盘缺「检查更新」 | 已加菜单项 | 手工 |
| Minor | README 误称右键关闭结果窗 | 已改正 | — |

仍未处理（记录在案）：热键冲突时设置页不标红；识别中切换引擎会让 UI 最多等 3 s；设置页缺「关于」分组与手动检查更新按钮。
