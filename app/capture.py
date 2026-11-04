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


def screen_physical_rect(geometry: QRect, dpr: float, virtual: QRect) -> QRect:
    """把 Qt 的逻辑几何换算到画布的物理像素坐标。

    进程是 per-monitor DPI aware 的，GetSystemMetrics 给的是物理像素，
    而 QScreen.geometry() 给的是逻辑坐标（150% 缩放下是物理尺寸的 2/3）。
    不做这个换算，drawImage 会按源图 DPR 把内容缩到逻辑尺寸，
    等于把截图降采样后再送去 OCR。
    """
    return QRect(
        round((geometry.x() - virtual.x()) * dpr),
        round((geometry.y() - virtual.y()) * dpr),
        round(geometry.width() * dpr),
        round(geometry.height() * dpr),
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
            image = shot.toImage()
            target = screen_physical_rect(geo, screen.devicePixelRatio(), rect)
            painter.drawImage(target, image, image.rect())
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
