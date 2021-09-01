try:
    import importlib.metadata as mtd
except ModuleNotFoundError:
    import importlib_metadata as mtd


__version__ = mtd.version("relaxed-poetry")