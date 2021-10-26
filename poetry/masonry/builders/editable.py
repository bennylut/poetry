from __future__ import unicode_literals

import hashlib
import os
import shutil

from base64 import urlsafe_b64encode
from pathlib import Path
from typing import TYPE_CHECKING, Union
from typing import List

from cleo.io.outputs.output import Verbosity
from poetry.core.masonry.builders.builder import Builder
from poetry.core.masonry.builders.sdist import SdistBuilder
from poetry.core.masonry.utils.package_include import PackageInclude
from poetry.core.semver.version import Version

from poetry.console import console
from poetry.utils._compat import WINDOWS
from poetry.utils._compat import decode
from poetry.utils.helpers import is_dir_writable
from poetry.utils.pip import pip_editable_install

if TYPE_CHECKING:
    from cleo.io.io import IO  # noqa

    from poetry.core.poetry import Poetry
    from poetry.utils.env import Env

SCRIPT_TEMPLATE = """\
#!{python}
from {module} import {callable_holder}

if __name__ == '__main__':
    {callable_}()
"""

WINDOWS_CMD_TEMPLATE = """\
@echo off\r\n"{python}" "%~dp0\\{script}" %*\r\n
"""


class EditableBuilder(Builder):
    def __init__(self, poetry: "Poetry", env: "Env", io: "IO") -> None:
        super(EditableBuilder, self).__init__(poetry)

        self._env = env
        self._io = io

    def build(self, include_symlinks: bool = False) -> None:
        console.println(f"  - Building package <c1>{self._package.name}</c1> in <info>editable</info> mode",
                        verbosity=Verbosity.DEBUG)

        if self._package.build_script:
            if self._package.build_should_generate_setup():
                console.println("  - <warning>Falling back on using a <b>setup.py</b></warning>", Verbosity.DEBUG)
                return self._setup_build()

            self._run_build_script(self._package.build_script)

        for removed in self._env.site_packages.remove_distribution_files(
                distribution_name=self._package.name
        ):
            console.println(f"  - Removed <c2>{removed.name}</c2> directory from <b>{removed.parent}</b>",
                            Verbosity.DEBUG)

        added_files = []
        added_files += self._add_pth(include_symlinks)
        added_files += self._add_scripts()
        self._add_dist_info(added_files)

    def _run_build_script(self, build_script: Union[Path, str]) -> None:
        build_script = Path(build_script)
        console.println(f"  - Executing build script: <b>{build_script}</b>", Verbosity.DEBUG)
        self._env.run("python", str(self._path.joinpath(build_script)), call=True)

    def _setup_build(self) -> None:
        builder = SdistBuilder(self._poetry)
        setup = self._path / "setup.py"
        has_setup = setup.exists()

        if has_setup:
            console.println("<warning>A setup.py file already exists. Using it.</warning>")
        else:
            with setup.open("w", encoding="utf-8") as f:
                f.write(decode(builder.build_setup()))

        try:
            if self._env.pip_version < Version.from_parts(19, 0):
                pip_editable_install(self._path, self._env)
            else:
                # Temporarily rename pyproject.toml
                shutil.move(
                    str(self._poetry.file), str(self._poetry.file.with_suffix(".tmp"))
                )
                try:
                    pip_editable_install(self._path, self._env)
                finally:
                    shutil.move(
                        str(self._poetry.file.with_suffix(".tmp")),
                        str(self._poetry.file),
                    )
        finally:
            if not has_setup:
                os.remove(str(setup))

    def _add_pth(self, include_symlinks: bool = False) -> List[Path]:
        paths = set()
        link_targets = []
        for include in self._module.includes:
            if isinstance(include, PackageInclude) and (
                    include.is_module() or include.is_package()
            ):
                paths.add(include.base.resolve().as_posix())
                link_targets.append(include)

        content = ""
        for path in paths:
            content += decode(path + os.linesep)

        pth_file = Path(self._module.name).with_suffix(".pth")

        # remove any pre-existing pth files for this package
        for file in self._env.site_packages.find(path=pth_file, writable_only=True):
            console.println(
                f"  - Removing existing <c2>{file.name}</c2> from <b>{file.parent}</b> for {self._poetry.file.parent}",
                Verbosity.DEBUG)
            # We can't use unlink(missing_ok=True) because it's not always available
            if file.exists():
                file.unlink()

        try:
            pth_file = self._env.site_packages.write_text(
                pth_file, content, encoding="utf-8"
            )
            console.println(
                f"  - Adding <c2>{pth_file.name}</c2> to <b>{pth_file.parent}</b> for {self._poetry.file.parent}",
                Verbosity.DEBUG)

            if include_symlinks:
                console.print("  - Including symlinks to: ")
                for link_target in link_targets:
                    console.print(link_target.package + " ")
                    dst = self._env.site_packages.path.joinpath(link_target.package)
                    src = link_target.base.joinpath(link_target.package)
                    if dst.exists():
                        dst.unlink()
                    os.symlink(src, dst, src.is_dir())
                console.println()

            return [pth_file]
        except OSError:
            # TODO: Replace with PermissionError
            self._io.write_error_line(
                "  - Failed to create <c2>{}</c2> for {}".format(
                    pth_file.name, self._poetry.file.parent
                )
            )
            return []

    def _add_scripts(self) -> List[Path]:
        added = []
        entry_points = self.convert_entry_points()

        for scripts_path in self._env.script_dirs:
            if is_dir_writable(path=scripts_path, create=True):
                break
        else:
            self._io.write_error_line(
                "  - Failed to find a suitable script installation directory for {}".format(
                    self._poetry.file.parent
                )
            )
            return []

        scripts = entry_points.get("console_scripts", [])
        for script in scripts:
            name, script = script.split(" = ")
            module, callable_ = script.split(":")
            callable_holder = callable_.split(".", 1)[0]

            script_file = scripts_path.joinpath(name)
            self._debug(
                "  - Adding the <c2>{}</c2> script to <b>{}</b>".format(
                    name, scripts_path
                )
            )
            with script_file.open("w", encoding="utf-8") as f:
                f.write(
                    decode(
                        SCRIPT_TEMPLATE.format(
                            python=self._env.python,
                            module=module,
                            callable_holder=callable_holder,
                            callable_=callable_,
                        )
                    )
                )

            script_file.chmod(0o755)

            added.append(script_file)

            if WINDOWS:
                cmd_script = script_file.with_suffix(".cmd")
                cmd = WINDOWS_CMD_TEMPLATE.format(python=self._env.python, script=name)
                self._debug(
                    "  - Adding the <c2>{}</c2> script wrapper to <b>{}</b>".format(
                        cmd_script.name, scripts_path
                    )
                )

                with cmd_script.open("w", encoding="utf-8") as f:
                    f.write(decode(cmd))

                added.append(cmd_script)

        return added

    def _add_dist_info(self, added_files: List[Path]) -> None:
        from poetry.core.masonry.builders.wheel import WheelBuilder

        added_files = added_files[:]

        builder = WheelBuilder(self._poetry)
        dist_info = self._env.site_packages.mkdir(Path(builder.dist_info))

        self._debug(
            "  - Adding the <c2>{}</c2> directory to <b>{}</b>".format(
                dist_info.name, dist_info.parent
            )
        )

        with dist_info.joinpath("METADATA").open("w", encoding="utf-8") as f:
            builder._write_metadata_file(f)

        added_files.append(dist_info.joinpath("METADATA"))

        with dist_info.joinpath("INSTALLER").open("w", encoding="utf-8") as f:
            f.write("poetry")

        added_files.append(dist_info.joinpath("INSTALLER"))

        if self.convert_entry_points():
            with dist_info.joinpath("entry_points.txt").open(
                    "w", encoding="utf-8"
            ) as f:
                builder._write_entry_points(f)

            added_files.append(dist_info.joinpath("entry_points.txt"))

        with dist_info.joinpath("RECORD").open("w", encoding="utf-8") as f:
            for path in added_files:
                hash = self._get_file_hash(path)
                size = path.stat().st_size
                f.write("{},sha256={},{}\n".format(str(path), hash, size))

            # RECORD itself is recorded with no hash or size
            f.write("{},,\n".format(dist_info.joinpath("RECORD")))

    def _get_file_hash(self, filepath: Path) -> str:
        hashsum = hashlib.sha256()
        with filepath.open("rb") as src:
            while True:
                buf = src.read(1024 * 8)
                if not buf:
                    break
                hashsum.update(buf)

            src.seek(0)

        return urlsafe_b64encode(hashsum.digest()).decode("ascii").rstrip("=")

    def _debug(self, msg: str) -> None:
        if self._io.is_debug():
            self._io.write_line(msg)
