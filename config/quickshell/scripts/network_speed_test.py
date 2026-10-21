#!/usr/bin/env python3
"""Run one bounded, user-requested internet throughput test.

This script is launched only by the Network Manager Test button. Results are
estimates of the path to Cloudflare, not passive interface traffic or the
contracted ISP speed. Output is one JSON event per line for QuickShell.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor


BASE_URL = "https://speed.cloudflare.com"
DOWNLOAD_BYTES = 8_000_000
UPLOAD_BYTES = 4_000_000
PARALLEL_REQUESTS = 4
REQUEST_TIMEOUT = 15


def emit(event: str, **fields: object) -> None:
    print(json.dumps({"event": event, **fields}), flush=True)


def make_opener() -> urllib.request.OpenerDirector:
    # Respect the desktop's configured proxy, if any: the test should follow
    # the route the user's normal internet traffic takes.
    return urllib.request.build_opener()


def download_once(size: int, base_url: str = BASE_URL) -> int:
    request = urllib.request.Request(
        f"{base_url}/__down?bytes={size}",
        headers={"Cache-Control": "no-store", "User-Agent": "danshell-speed-test/1.0"},
    )
    received = 0
    with make_opener().open(request, timeout=REQUEST_TIMEOUT) as response:
        while chunk := response.read(65536):
            received += len(chunk)
            if received > size:
                raise ValueError("The test server returned more data than requested")
    if received != size:
        raise ValueError("The download ended before the test sample was complete")
    return received


def upload_once(payload: bytes, base_url: str = BASE_URL) -> int:
    request = urllib.request.Request(
        f"{base_url}/__up",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/octet-stream",
            "User-Agent": "danshell-speed-test/1.0",
        },
    )
    with make_opener().open(request, timeout=REQUEST_TIMEOUT) as response:
        response.read(65536)
    return len(payload)


def measure(task, count: int = PARALLEL_REQUESTS) -> float:
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=count) as pool:
        transferred = sum(pool.map(lambda _: task(), range(count)))
    elapsed = max(time.monotonic() - started, 0.001)
    return round(transferred * 8 / elapsed / 1_000_000, 1)


def run() -> None:
    emit("phase", name="download")
    download_mbps = measure(lambda: download_once(DOWNLOAD_BYTES))
    emit("partial", name="download", mbps=download_mbps)

    emit("phase", name="upload")
    payload = b"x" * UPLOAD_BYTES
    upload_mbps = measure(lambda: upload_once(payload))
    emit("result", download_mbps=download_mbps, upload_mbps=upload_mbps)


if __name__ == "__main__":
    try:
        run()
    except urllib.error.HTTPError as error:
        emit("error", message=f"Test server returned HTTP {error.code}. Try again later.")
        sys.exit(1)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        emit("error", message=f"Could not reach the test server: {error.reason if isinstance(error, urllib.error.URLError) else error}")
        sys.exit(1)
    except ValueError as error:
        emit("error", message=str(error))
        sys.exit(1)
