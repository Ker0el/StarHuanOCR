# OCR 引擎选型与基准（2026-11-04）

机器：Windows 11 · 24 逻辑核 · RTX 4070 Ti (12 GB) · 驱动 617.42 · 未装 CUDA Toolkit
软件：Python 3.12.10 · rapidocr 3.10.0 · onnxruntime 1.31.1 / onnxruntime-directml 1.24.4
测试图：`ch_en_num.jpg`（323×430 中文促销图）的裁剪，分别 323×120 与 323×300

## 结论

| 组合 | 323×120 | 323×300 | 采用 |
|---|---|---|---|
| PP-OCRv6 small · CPU | 168 ms | 407 ms | ✅ CPU 版默认 |
| PP-OCRv6 medium · CPU | 4236 ms | 3094 ms | ❌ 太慢，仅作「高精度」可选 |
| PP-OCRv6 small · DirectML | 12.8 ms | 67 ms | — |
| **PP-OCRv6 medium · DirectML** | **15.2 ms** | **82 ms** | ✅ GPU 版默认 |

DirectML 可用，且比 CPU 快一个数量级；GPU 上 medium 与 small 耗时几乎相同（15 vs 13 ms），
所以 GPU 版直接用 medium（屏幕文字准确率 82.5% vs 79.7%）。

## 两个必须覆盖的默认值（否则慢 10~25 倍）

RapidOCR 3.10 的默认配置在本机上是病态的：

1. `EngineConfig.onnxruntime.intra_op_num_threads` 默认 `-1`，ORT 在 24 核上开满线程后严重抢占。
   实测 det（128×320）：24 线程 117 ms，8 线程 35 ms，4 线程 66 ms。**显式设 3~4 最优**（本机 3 线程最好）。
2. `Det.limit_type` 默认 `min` + `limit_side_len` 736，会把 323×120 的截图短边放大到 736 →
   实际推理尺寸接近 1981×736。改成 `limit_type=max` + `limit_side_len=960` 后总耗时从 2150 ms 降到 350 ms。

这两项都写进 `app/ocr/engine.py`，并配测试防回归。

## 备注

- 开发用 venv 当前装的是 `onnxruntime-directml`（含 Dml + CPU 两个 EP，是 CPU 版的超集）。
- 发布时 CPU 版装 `onnxruntime`，GPU 版装 `onnxruntime-directml`，代码不变，运行时按
  `ort.get_available_providers()` 自动选择。
- 模型文件位于 `site-packages/rapidocr/models/PP-OCRv6_{det,rec}_small.onnx`，打包时复制进 `models/`。
