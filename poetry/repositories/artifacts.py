import hashlib
import threading
from pathlib import Path
from typing import Optional, Union

from poetry.core.packages.file_dependency import FileDependency
from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link

from poetry.console import Printer, NullPrinter
from poetry.installation.chooser import Wheel, InvalidWheelName
from poetry.managed_project import ManagedProject

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

    def fetch(self, project: ManagedProject, link: Link, io: Printer = NullPrinter,
              package: Optional[Package] = None) -> Path:

        cached = self._lookup_cache(project, link)
        if cached is not None:
            return cached

        cached = self._download_archive(project, link, io)
        if package is not None:
            self._validate_hash(cached, package, io)
        return cached

    def _download_archive(self, project: ManagedProject, link: Link, io: Printer) -> Path:
        response = project.authenticator.request("get", link.url, stream=True, io=io)
        wheel_size = response.headers.get("content-length")

        message = f"<info>Downloading {link.filename}...</>"
        progress = None
        if io.is_decorated():
            if wheel_size is None:
                io.println(message)
            else:
                from cleo.ui.progress_bar import ProgressBar

                progress = ProgressBar(io.dynamic_line().as_output(), max=int(wheel_size))
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

    def _lookup_cache(self, project: ManagedProject, link: Link) -> Optional[Path]:
        cache_dir = self._cache_dir_of(link)

        if cache_dir.exists():
            candidates = []
            for archive in cache_dir.iterdir():
                if archive.suffix in _ARCHIVE_TYPES and archive.with_suffix('.success').exists():
                    if archive.suffix != '.whl':
                        candidates.append((float("inf"), archive))
                    else:
                        try:
                            wheel = Wheel(archive.name)
                        except InvalidWheelName:
                            continue

                        if not wheel.is_supported_by_environment(project.env):
                            continue

                        candidates.append(
                            (wheel.get_minimum_supported_index(project.env.supported_tags), archive),
                        )

            if len(candidates) > 0:
                return min(candidates)[1]

        return None

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
