from __future__ import annotations

from threading import Lock

in_flight_checksums: set[str] = set()
lock = Lock()


def try_claim(checksum: str) -> bool:
    with lock:
        if checksum in in_flight_checksums:
            return False
        in_flight_checksums.add(checksum)
        return True


def release(checksum: str) -> None:
    with lock:
        in_flight_checksums.discard(checksum)
