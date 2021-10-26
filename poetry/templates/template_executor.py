import zipfile
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Dict, Optional, ContextManager

from poetry.core.pyproject.project import Project
from poetry.core.vcs import Git
from poetry.core.utils.props_ext import cached_property
from poetry.core.vcs.git import GitConfig
# noinspection PyPackageRequirements
from protopy import doc_generator
# noinspection PyPackageRequirements
from protopy.engine import ProtopyEngine

from poetry.console import console
from poetry.managed_project import ManagedProject

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from poetry.app.relaxed_poetry import RelaxedPoetry


class TemplateExecutor:

    def __init__(self, rp: "RelaxedPoetry"):
        self._rp = rp
        self._pengine = ProtopyEngine(console.io)

    @cached_property
    def _git(self) -> Git:
        return Git()

    def document(self, descriptor: str) -> str:
        with self._locate_template(descriptor) as template:
            if not template or not template.exists():
                raise FileNotFoundError(f"could not locate template according to descriptor: {descriptor}")

            return doc_generator.generate(template / "proto.py", descriptor, "rp new")

    def execute(
            self,
            descriptor: str,
            out_path: Path,
            args: List[str],
            kwargs: Dict[str, str],
            allow_override: bool
    ):

        with self._locate_template(descriptor) as template:
            if not template or not template.exists():
                raise FileNotFoundError(f"could not locate template according to descriptor: {descriptor}")

            rp_ctx = _RelaxedPoetryTemplateContext(self._rp)
            self._pengine.render(
                template, out_path, args,
                kwargs, {"rp": rp_ctx}, allow_overwrite=allow_override)

    @contextmanager
    def _locate_template(self, descriptor: str) -> ContextManager[Path]:
        if descriptor.startswith("git+"):  # this is a git descriptor
            with _use_git_template(self._git, descriptor[len("git+"):]) as path:
                yield path
        else:
            descriptor_path = Path(descriptor)
            if descriptor_path.exists() or descriptor_path.with_suffix(".zip").exists():  # this is a path descriptor
                with _use_file_system(descriptor_path) as path:
                    yield path
            else:
                with _use_template_ref(descriptor, self._rp.active_project) as path:
                    yield path


@contextmanager
def _use_git_template(git: Git, repo: str):
    with TemporaryDirectory() as tmp:
        path = Path(tmp)
        git.clone(repo, path)
        yield path


@contextmanager
def _use_file_system(path: Path):
    if path.suffix == ".zip":
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            zipfile.ZipFile(path).extractall(tmp_path)
            yield tmp_path
    else:
        yield path


@contextmanager
def _use_builtin(name: str):
    try:
        import importlib.resources as pkg_resources
    except ImportError:
        import importlib_resources as pkg_resources

    with pkg_resources.path(__package__, name + ".zip") as resource_path:
        if not resource_path.exists():
            yield None
        else:
            with _use_file_system(resource_path) as path:
                yield path


@contextmanager
def _use_template_ref(name: str, prj: ManagedProject):

    if prj is not None:
        template_path = prj.path / "etc/rp/templates" / name
        if template_path.exists() or template_path.with_suffix(".zip").exists():
            with _use_file_system(template_path) as path:
                yield path
                return
        else:
            parent = prj.parent
            if parent:
                with _use_template_ref(name, parent) as path:
                    yield path
                    return

    with _use_builtin(name) as path:
        yield path


class _RelaxedPoetryProjectDefaults:

    @cached_property
    def _git_config(self):
        return GitConfig()

    @cached_property
    def author_name(self) -> str:
        """
        :return: the default author name
        """
        config = self._git_config
        author = None
        if config.get("user.name"):
            author = config["user.name"]
            author_email = config.get("user.email")
            if author_email:
                author += " <{}>".format(author_email)

        return author

    @cached_property
    def python_requirements(self) -> str:
        """
        :return: the default python version requirements (e.g., ^3.6)
        """
        import platform
        mj, mn, _ = platform.python_version_tuple()
        return f"^{mj}.{mn}"

    # noinspection PyCompatibility
    @cached_property
    def buildsys_requirements(self) -> str:
        """
        :return: the default build-sys (relaxed-poetry-core) requirements (e.g., >=0.1)
        """
        try:
            import importlib.metadata as mtd
        except ModuleNotFoundError:
            import importlib_metadata as mtd

        version = mtd.version("relaxed-poetry-core")
        return f">={version}"


class _RelaxedPoetryTemplateContext:
    def __init__(self, rp: "RelaxedPoetry"):
        self._rp = rp
        self.project_defaults = _RelaxedPoetryProjectDefaults()

    @property
    def active_project(self) -> Optional[Project]:
        if not self._rp.active_project:
            return None

        return self._rp.active_project.pyproject
