from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import requests


class NHLClient:
    def __init__(self, timeout: int = 45, retries: int = 4) -> None:
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "NHL-State-Lab/0.1 (public analytics project)"}
        )

    def get_json(
        self, url: str, cache_path: Path, refresh: bool = False
    ) -> dict[str, Any]:
        if cache_path.exists() and not refresh:
            return json.loads(cache_path.read_text(encoding="utf-8"))

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                payload = response.json()
                temp_path = cache_path.with_suffix(
                    cache_path.suffix + f".{os.getpid()}.{uuid.uuid4().hex}.tmp"
                )
                temp_path.write_text(
                    json.dumps(payload, ensure_ascii=False), encoding="utf-8"
                )
                for replace_attempt in range(6):
                    try:
                        os.replace(temp_path, cache_path)
                        break
                    except PermissionError:
                        if replace_attempt == 5:
                            raise
                        time.sleep(0.25 * (replace_attempt + 1))
                return payload
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                time.sleep(1.5 * (2**attempt))
        raise RuntimeError(f"Unable to download {url}: {last_error}")

    def download(self, url: str, cache_path: Path, refresh: bool = False) -> Path:
        if cache_path.exists() and not refresh:
            return cache_path
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.session.get(url, timeout=120, stream=True) as response:
            response.raise_for_status()
            temp_path = cache_path.with_suffix(
                cache_path.suffix + f".{os.getpid()}.{uuid.uuid4().hex}.tmp"
            )
            with temp_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
            for replace_attempt in range(6):
                try:
                    os.replace(temp_path, cache_path)
                    break
                except PermissionError:
                    if replace_attempt == 5:
                        raise
                    time.sleep(0.25 * (replace_attempt + 1))
        return cache_path
