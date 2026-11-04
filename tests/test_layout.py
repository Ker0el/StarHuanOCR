from app.ocr.layout import boxes_to_text


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
