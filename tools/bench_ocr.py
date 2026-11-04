"""RapidOCR 基准：测量 PP-OCRv6 各档位/各 provider 的实际耗时。

用法：
    python tools/bench_ocr.py <image> [--model small|medium|tiny] [--provider cpu|dml|cuda] [--threads N]

注意：RapidOCR 默认 intra_op_num_threads=-1（交给 ORT 自动分配），在 24 核机器上
实测反而比 4 线程慢 3~10 倍，所以这里默认显式给 4。
Det 默认 limit_type=min / 736 会把小截图放大到近 2000px，也必须改成 max。
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

from rapidocr import EngineType, ModelType, OCRVersion, RapidOCR

MODELS = {"small": ModelType.SMALL, "medium": ModelType.MEDIUM, "tiny": ModelType.TINY}


def build(model: str, provider: str, threads: int) -> RapidOCR:
    params = {
        "Det.engine_type": EngineType.ONNXRUNTIME,
        "Det.model_type": MODELS[model],
        "Det.ocr_version": OCRVersion.PPOCRV6,
        "Det.limit_type": "max",
        "Det.limit_side_len": 960,
        "Rec.engine_type": EngineType.ONNXRUNTIME,
        "Rec.model_type": MODELS[model],
        "Rec.ocr_version": OCRVersion.PPOCRV6,
        "Global.log_level": "error",
        "EngineConfig.onnxruntime.intra_op_num_threads": threads,
    }
    if provider == "cuda":
        params["EngineConfig.onnxruntime.use_cuda"] = True
    elif provider == "dml":
        params["EngineConfig.onnxruntime.use_dml"] = True
    return RapidOCR(params=params)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--model", default="small", choices=sorted(MODELS))
    ap.add_argument("--provider", default="cpu", choices=["cpu", "dml", "cuda"])
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()

    path = Path(args.image)
    if not path.exists():
        print(f"图片不存在: {path}", file=sys.stderr)
        return 2

    engine = build(args.model, args.provider, args.threads)
    engine(str(path))  # 预热，避免把模型加载算进计时

    times: list[float] = []
    text = ""
    for _ in range(args.runs):
        start = time.perf_counter()
        result = engine(str(path))
        times.append((time.perf_counter() - start) * 1000)
        text = "".join(result.txts) if result and result.txts else ""

    print(f"model={args.model} provider={args.provider} threads={args.threads} "
          f"median={statistics.median(times):.1f}ms min={min(times):.1f}ms max={max(times):.1f}ms")
    print(f"text={text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
