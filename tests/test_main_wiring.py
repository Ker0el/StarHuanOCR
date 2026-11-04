from app.hotkey import HotkeyManager
from main import wire_hotkey


def test_wire_hotkey_connects_even_when_registration_failed(qapp):
    manager = HotkeyManager()
    assert manager.is_registered is False  # 模拟启动时注册失败

    calls = []

    class Stub:
        def trigger_capture(self):
            calls.append(1)

    stub = Stub()  # 必须持有引用，否则临时对象被回收后信号连接即失效
    wire_hotkey(manager, stub)
    manager.activated.emit()
    assert calls == [1]
