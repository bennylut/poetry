from pathlib import Path
from typing import Any

from poetry.core.utils import toml
from poetry.core.utils.collections import nested_dict_set, nested_dict_del

from .config_source import ConfigSource


class FileConfigSource(ConfigSource):
    def __init__(self, file: Path, auth_config: bool = False) -> None:
        self._file = file
        self._auth_config = auth_config

    @property
    def name(self) -> str:
        return str(self._file)

    @property
    def file(self) -> Path:
        return self._file

    def add_property(self, key: str, value: Any) -> None:
        data, dumps = toml.load(self._file)
        nested_dict_set(data, toml.key2path(key), value)
        self._file.write_text(dumps(data))

    def remove_property(self, key: str) -> None:
        data, dumps = toml.load(self._file)
        nested_dict_del(data, toml.key2path(key))
        self._file.write_text(dumps(data))
