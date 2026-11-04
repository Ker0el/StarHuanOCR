from PySide6.QtCore import QRect, Qt

from app.ui.result_window import ResultWindow


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


def test_copied_hint_shown_when_auto_copied(qtbot):
    w = ResultWindow()
    qtbot.addWidget(w)
    w.show_result("你好", QRect(0, 0, 10, 10), copied=True)
    assert w.copied_label.isHidden() is False
    assert w.copied_label.text() == "√ 已复制到剪贴板"


def test_copied_hint_hidden_for_new_result_without_copy(qtbot):
    w = ResultWindow()
    qtbot.addWidget(w)
    w.show_result("你好", QRect(0, 0, 10, 10), copied=True)
    w.show_result("再来", QRect(0, 0, 10, 10), copied=False)
    assert w.copied_label.isHidden() is True


def test_copy_button_shows_hint(qtbot):
    w = ResultWindow()
    qtbot.addWidget(w)
    w.show_result("你好", QRect(0, 0, 10, 10), copied=False)
    w.copy_text()
    assert w.copied_label.isHidden() is False


def test_click_outside_closes_window(qtbot):
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QMouseEvent

    w = ResultWindow()
    qtbot.addWidget(w)
    w.show_result("你好", QRect(200, 200, 120, 40))
    inside = w.geometry()
    outside = QPointF(inside.right() + 200, inside.bottom() + 200)
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(5, 5),
        outside,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    w.eventFilter(w, event)
    assert w.isVisible() is False


def test_click_inside_keeps_window(qtbot):
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QMouseEvent

    w = ResultWindow()
    qtbot.addWidget(w)
    w.show_result("你好", QRect(200, 200, 120, 40))
    local = QPointF(10, 10)
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        local,
        QPointF(w.geometry().topLeft()) + local,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    w.eventFilter(w, event)
    assert w.isVisible() is True


def test_result_text_uses_larger_font(qtbot):
    from app.ui.fonts import RESULT_TEXT_SIZE

    w = ResultWindow()
    qtbot.addWidget(w)
    assert w.text_edit.font().pointSize() == RESULT_TEXT_SIZE


def test_window_can_be_dragged(qtbot):
    from PySide6.QtCore import QEvent, QPoint, QPointF
    from PySide6.QtGui import QMouseEvent

    w = ResultWindow()
    qtbot.addWidget(w)
    w.show_result("你好", QRect(200, 200, 120, 40))
    before = w.pos()
    press_global = QPointF(w.mapToGlobal(QPoint(10, 10)))
    w.mousePressEvent(
        QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(10, 10), press_global,
                    Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier)
    )
    move_global = QPointF(press_global.x() + 60, press_global.y() + 40)
    w.mouseMoveEvent(
        QMouseEvent(QEvent.Type.MouseMove, QPointF(70, 50), move_global,
                    Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier)
    )
    assert w.pos() != before


def test_window_closes_when_deactivated(qtbot):
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    w = ResultWindow()
    qtbot.addWidget(w)
    w.show_result("你好", QRect(200, 200, 120, 40))
    assert w.isVisible() is True
    QApplication.sendEvent(w, QEvent(QEvent.Type.WindowDeactivate))
    assert w.isVisible() is False
