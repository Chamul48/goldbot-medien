"""Verhindert, dass der Dauerbetrieb zweimal gleichzeitig läuft.

Die Sperre ist eine echte Datei-Sperre des Betriebssystems: Sie verschwindet
automatisch, wenn der Prozess endet (auch nach Absturz oder Strg+C).
"""

from __future__ import annotations

import os
from pathlib import Path


class AlreadyRunning(RuntimeError):
    pass


class single_instance:  # noqa: N801 - wird wie ein Kontextmanager benutzt
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._fh = None

    def __enter__(self) -> "single_instance":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(self.path, "a+")
        try:
            if os.name == "nt":
                import msvcrt

                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            fh.close()
            raise AlreadyRunning(str(self.path)) from exc
        self._fh = fh
        return self

    def __exit__(self, *exc: object) -> None:
        if self._fh:
            try:
                if os.name == "nt":
                    import msvcrt

                    self._fh.seek(0)
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
                self._fh = None
