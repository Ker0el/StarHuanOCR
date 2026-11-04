"""单实例：第二个进程把激活消息转给第一个后退出。"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstance(QObject):
    activated = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_new_connection)

    def try_acquire(self, name: str) -> bool:
        probe = QLocalSocket()
        probe.connectToServer(name)
        if probe.waitForConnected(200):
            probe.write(b"activate")
            probe.flush()
            probe.waitForBytesWritten(200)
            probe.disconnectFromServer()
            return False

        QLocalServer.removeServer(name)
        return self._server.listen(name)

    def release(self) -> None:
        self._server.close()

    def _on_new_connection(self) -> None:
        while self._server.hasPendingConnections():
            conn = self._server.nextPendingConnection()
            conn.readyRead.connect(lambda c=conn: self._drain(c))
            conn.disconnected.connect(conn.deleteLater)
        self.activated.emit()

    @staticmethod
    def _drain(conn) -> None:
        conn.readAll()
