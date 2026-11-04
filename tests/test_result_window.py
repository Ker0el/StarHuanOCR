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
