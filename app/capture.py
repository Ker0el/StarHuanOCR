"""虚拟桌面截屏与裁剪。"""
from __future__ import annotations

import ctypes

import numpy as np
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


def virtual_desktop_rect() -> QRect:
    u = ctypes.windll.user32
    return QRect(
        u.GetSystemMetrics(SM_XVIRTUALSCREEN),
        u.GetSystemMetrics(SM_YVIRTUALSCREEN),
        u.GetSystemMetrics(SM_CXVIRTUALSCREEN),
        u.GetSystemMetrics(SM_CYVIRTUALSCREEN),
    )


def grab_virtual_desktop() -> QImage:
    """逐屏抓取并合成到一张覆盖整个虚拟桌面的位图。"""
    rect = virtual_desktop_rect()
    canvas = QImage(rect.size(), QImage.Format.Format_RGB32)
    canvas.fill(Qt.GlobalColor.black)

    painter = QPainter(canvas)
    try:
        for screen in QGuiApplication.screens():
            geo = screen.geometry()
            shot = screen.grabWindow(0)
            if shot.isNull():
                continue
            painter.drawImage(geo.x() - rect.x(), geo.y() - rect.y(), shot.toImage())
    finally:
        painter.end()
    return canvas


def crop_to_numpy(image: QImage, rect_in_image: QRect) -> np.ndarray:
    """裁出 RGB888 连续数组，供 OCR 引擎使用。"""
    cropped = image.copy(rect_in_image).convertToFormat(QImage.Format.Format_RGB888)
    width, height = cropped.width(), cropped.height()
    if width <= 0 or height <= 0:
        return np.empty((0, 0, 3), dtype=np.uint8)
    buffer = np.frombuffer(cropped.constBits(), dtype=np.uint8, count=cropped.sizeInBytes())
    rows = buffer.reshape(height, cropped.bytesPerLine())
    # 必须显式 copy：cropped 是局部 QImage，函数返回后其缓冲区会被释放，
    # 直接返回视图会让调用方读到已释放内存（表现为 OCR 乱码或访问冲突）。
    return np.array(rows[:, : width * 3], dtype=np.uint8, copy=True).reshape(height, width, 3)
