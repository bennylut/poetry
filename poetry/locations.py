from pathlib import Path

from .utils.appdirs import user_cache_dir
from .utils.appdirs import user_config_dir
from .utils.appdirs import user_data_dir

CACHE_DIR = user_cache_dir("relaxed-poetry")
DATA_DIR = user_data_dir("relaxed-poetry")
CONFIG_DIR = user_config_dir("relaxed-poetry")

REPOSITORY_CACHE_DIR = Path(CACHE_DIR) / "cache" / "repositories"


def data_dir() -> Path:
    """
    deprecated! use RelaxedPoetry.installation_dir
    :return:
    """
    from poetry.app.relaxed_poetry import RelaxedPoetry
    return RelaxedPoetry.installation_dir()
