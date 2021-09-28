try:
    import importlib.metadata as mtd
except ModuleNotFoundError:
    import importlib_metadata as mtd


try:
    __version__ = mtd.version("relaxed-poetry")
except mtd.PackageNotFoundError as e:
    from pathlib import Path
    from poetry.core.pyproject.toml import PyProject

    __version__ = PyProject.read(Path(__file__).parent / "../pyproject.toml").version


