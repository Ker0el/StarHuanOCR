from app.single_instance import SingleInstance


def test_second_instance_is_rejected(qapp):
    first = SingleInstance()
    assert first.try_acquire("starhuan-test") is True
    second = SingleInstance()
    assert second.try_acquire("starhuan-test") is False
    first.release()
