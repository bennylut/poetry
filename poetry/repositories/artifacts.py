import hashlib
import threading
from pathlib import Path
from typing import Optional, Union

from poetry.console import Printer, NullPrinter
from poetry.core.packages.file_dependency import FileDependency
from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link
from poetry.utils.authenticator import Authenticator

_ARCHIVE_TYPES = {".whl", ".tar.gz", ".tar.bz2", ".bz2", ".zip"}


class Artifacts:
    def __init__(self, workspace: Union[Path, str]):
        self._workspace = Path(workspace)
        self._lock = threading.Lock()

    def _cache_dir_of(self, link: Link) -> Path:
        link_hash = hashlib.md5(link.url.encode('ascii')).hexdigest()
        parts = link.filename.split("-", maxsplit=1)
        pack_dir = parts[0]
        ver_dir = parts[1] if len(parts) > 0 else "unknown_versions"

        return self._workspace / pack_dir / ver_dir / link_hash

    def fetch(self, link: Union[Link, str], authenticator: Optional[Authenticator], io: Printer = NullPrinter,
              package: Optional[Package] = None) -> Path:

        if isinstance(link, str):
            link = Link(link)

        cached = self._lookup_cache(link)
        if cached is not None:
            return cached

        cached = self._download_archive(authenticator, link, io)
        if package is not None:
            self._validate_hash(cached, package, io)
        return cached

    def _download_archive(self, authenticator: Optional[Authenticator], link: Link, printer: Printer) -> Path:
        if not authenticator:
            from poetry.app.relaxed_poetry import rp
            authenticator = rp.authenticator

        response = authenticator.request("get", link.url, stream=True, io=printer.as_output())
        wheel_size = response.headers.get("content-length")

        message = f"<info>Downloading {link.filename}...</>"
        progress = None
        if printer.is_decorated():
            if wheel_size is None:
                printer.println(message)
            else:
                from cleo.ui.progress_bar import ProgressBar

                progress = ProgressBar(printer.dynamic_line().as_output(), max=int(wheel_size))
                progress.set_format(message + " <b>%percent%%</b>")

        if progress:
            progress.start()

        done = 0
        archive = self._cache_dir_of(link) / link.filename
        archive.parent.mkdir(parents=True, exist_ok=True)
        with archive.open("wb") as f:
            for chunk in response.iter_content(chunk_size=4096):
                if not chunk:
                    break

                done += len(chunk)

                if progress:
                    progress.set_progress(done)

                f.write(chunk)

        if progress:
            progress.finish()

        archive.with_suffix(".success").touch(exist_ok=True)

        return archive

    def _lookup_cache(self, link: Link) -> Optional[Path]:
        cache_dir = self._cache_dir_of(link)
        cached_file = cache_dir / link.filename

        if cached_file.with_suffix(".success").exists():
            return cached_file
        return None
        #
        # if cache_dir.exists():
        #     candidates = []
        #     for archive in cache_dir.iterdir():
        #         if archive.suffix in _ARCHIVE_TYPES and archive.with_suffix('.success').exists():
        #             if archive.suffix != '.whl':
        #                 candidates.append((float("inf"), archive))
        #             else:
        #                 try:
        #                     wheel = Wheel(archive.name)
        #                 except InvalidWheelName:
        #                     continue
        #
        #                 if not wheel.is_supported_by_environment(project.env):
        #                     continue
        #
        #                 candidates.append(
        #                     (wheel.get_minimum_supported_index(project.env.supported_tags), archive),
        #                 )
        #
        #     if len(candidates) > 0:
        #         return min(candidates)[1]
        #
        # return None

    def _validate_hash(self, artifact: Path, package: Package, io: Printer):
        if package.files:
            file_meta = next((meta for meta in package.files if meta.get('file') == artifact.name), None)
            if file_meta and file_meta['hash']:
                archive_hash = ("sha256:" + FileDependency(package.name, artifact, ).hash())
                if archive_hash != file_meta['hash']:
                    raise RuntimeError(f"Invalid hash for {package} using archive {artifact.name}")
            else:
                io.println(
                    f"<warning>Package {package.name}:{package.version} does not include hash for its archives, "
                    "including it can improve security, if you can, "
                    "please ask the maintainer of this package to do so.</warning>")
