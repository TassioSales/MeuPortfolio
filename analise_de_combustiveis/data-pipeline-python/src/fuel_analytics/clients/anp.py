from __future__ import annotations

import re
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import httpx

from fuel_analytics.logging import logger


ANP_SERIES_URL = (
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis"
)
ANP_SALES_URL = (
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/vendas-de-derivados-de-petroleo-e-biocombustiveis"
)
ANP_PROCESSING_URL = (
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/processamento-de-petroleo-e-producao-de-derivados"
)


@dataclass(slots=True)
class RemoteFile:
    label: str
    url: str
    published_order: int = 0


class ANPClient:
    def __init__(self, timeout: float = 60.0) -> None:
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)
        logger.debug("ANP client initialized with timeout={}s", timeout)

    def list_csv_files(self) -> list[RemoteFile]:
        logger.info("Fetching ANP series page: {}", ANP_SERIES_URL)
        result = self.list_files(ANP_SERIES_URL, extensions=("csv",))
        logger.info("Found {} ANP CSV files", len(result))
        return result

    def select_price_files(self, files: list[RemoteFile], per_series: int = 10) -> list[RemoteFile]:
        buckets: dict[str, list[RemoteFile]] = {}
        for item in files:
            buckets.setdefault(self._series_key(item.label), []).append(item)
        selected: list[RemoteFile] = []
        for series in sorted(buckets):
            selected.extend(buckets[series][:per_series])
        logger.info(
            "Selected {} price files across {} series (per_series={})",
            len(selected),
            len(buckets),
            per_series,
        )
        return selected

    def list_sales_files(self) -> list[RemoteFile]:
        logger.info("Fetching ANP sales page: {}", ANP_SALES_URL)
        return self.list_files(ANP_SALES_URL, extensions=("csv", "xls", "xlsx"))

    def list_processing_files(self) -> list[RemoteFile]:
        logger.info("Fetching ANP processing page: {}", ANP_PROCESSING_URL)
        return self.list_files(ANP_PROCESSING_URL, extensions=("csv", "xls", "xlsx"))

    def list_files(self, page_url: str, extensions: tuple[str, ...]) -> list[RemoteFile]:
        response = self._client.get(page_url)
        response.raise_for_status()
        ext_pattern = "|".join(map(re.escape, extensions))
        hrefs = re.findall(
            rf'href="([^"]+\.({ext_pattern})(?:/view)?)"',
            response.text,
            flags=re.IGNORECASE,
        )
        files: list[RemoteFile] = []
        for idx, (href, _) in enumerate(hrefs):
            url = href if href.startswith("http") else f"https://www.gov.br{href}"
            label = self._infer_label(url)
            files.append(RemoteFile(label=label, url=url, published_order=idx))
        deduped_by_url = {self._to_download_url(item.url): item for item in files}
        deduped_by_label: dict[str, RemoteFile] = {}
        for item in self._sort_recent_files(list(deduped_by_url.values())):
            deduped_by_label.setdefault(item.label.lower(), item)
        return list(deduped_by_label.values())

    def download_files(self, targets: Iterable[RemoteFile], raw_dir: Path) -> list[Path]:
        raw_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for target in targets:
            destination = raw_dir / target.label
            if destination.exists():
                logger.info("Using cached ANP file {}", destination)
                paths.append(destination)
                continue
            logger.info("Downloading ANP file {} to {}", target.url, destination)
            self._download_file(target.url, destination)
            paths.append(destination)
        logger.info("ANP download step finished with {} files", len(paths))
        return paths

    def redownload_file(self, target: RemoteFile, raw_dir: Path) -> Path:
        raw_dir.mkdir(parents=True, exist_ok=True)
        destination = raw_dir / target.label
        if destination.exists():
            destination.unlink()
        logger.info("Re-downloading corrupted ANP file {} to {}", target.url, destination)
        self._download_file(target.url, destination)
        return destination

    def _download_file(self, url: str, destination: Path) -> None:
        candidates = [self._to_download_url(url), url]
        last_error: Exception | None = None
        for candidate in candidates:
            try:
                tmp = destination.with_suffix(destination.suffix + ".part")
                with self._client.stream("GET", candidate) as response:
                    response.raise_for_status()
                    expected = int(response.headers.get("Content-Length", "0") or "0")
                    received = 0
                    with tmp.open("wb") as handle:
                        for chunk in response.iter_bytes():
                            handle.write(chunk)
                            received += len(chunk)
                if expected and received != expected:
                    raise RuntimeError(f"download truncated: received={received} expected={expected}")
                tmp.replace(destination)
                return
            except Exception as exc:
                last_error = exc
                logger.warning("Download attempt failed for {}: {}", candidate, exc)
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Falha ao baixar {url}") from last_error

    @staticmethod
    def _to_download_url(url: str) -> str:
        if url.endswith("/view"):
            return url.removesuffix("/view") + "/@@download/file"
        return url

    @staticmethod
    def _infer_label(url: str) -> str:
        clean = url.split("?")[0].rstrip("/")
        parts = clean.split("/")
        if parts[-1] == "view" and len(parts) >= 2:
            return parts[-2]
        return parts[-1]

    @staticmethod
    def _sort_recent_files(files: list[RemoteFile]) -> list[RemoteFile]:
        def score(item: RemoteFile) -> tuple[int, int, int]:
            match = re.search(r"(\d{4})[-_](\d{2})", item.label)
            if match:
                return (int(match.group(1)), int(match.group(2)), -item.published_order)
            year_only = re.search(r"(20\d{2})", item.label)
            if year_only:
                return (int(year_only.group(1)), 0, -item.published_order)
            return (0, 0, -item.published_order)

        return sorted(files, key=score, reverse=True)

    @staticmethod
    def _series_key(label: str) -> str:
        without_ext = re.sub(r"\.(csv|xls|xlsx)$", "", label, flags=re.IGNORECASE)
        normalized = without_ext.lower()
        normalized = re.sub(r"[-_](20\d{2})([-_]\d{2})?$", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"[-_](0[1-9]|1[0-2])$", "", normalized)
        normalized = re.sub(r"[-_](1|2)$", "", normalized)
        normalized = re.sub(r"[-_]+$", "", normalized)
        return normalized
