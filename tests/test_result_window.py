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
