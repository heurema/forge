"""Registry I/O adapters for 4 target registries.

Each adapter reads/writes a specific JSON format. All writes are atomic (tmp + rename).
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class RegistryIOError(Exception):
    pass


def atomic_write_json(path: Path, data: object) -> None:
    """Write JSON atomically via tmp + os.rename."""
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    closed = False
    try:
        os.write(fd, content.encode())
        os.close(fd)
        closed = True
        os.rename(tmp, path)
    except BaseException:
        if not closed:
            os.close(fd)
        Path(tmp).unlink(missing_ok=True)
        raise


class Skill7Registry:
    """Adapter for skill7 registry.json (dict with category keys)."""

    def __init__(self, path: Path) -> None:
        self.file_path = path
        self.target_name = "skill7_registry"

    def _load(self) -> dict:
        return json.loads(self.file_path.read_text())

    def read_entry(self, name: str) -> dict | None:
        data = self._load()
        for cat_entries in data.values():
            matches = [e for e in cat_entries if e.get("name") == name]
            if matches:
                if len(matches) > 1:
                    raise RegistryIOError(f"Data corruption: duplicate '{name}' in {self.file_path}")
                return matches[0]
        return None

    def _find_category(self, name: str) -> str | None:
        data = self._load()
        for cat, entries in data.items():
            if any(e.get("name") == name for e in entries):
                return cat
        return None

    def write_entry(self, name: str, entry: dict, *, category: str) -> str:
        data = self._load()
        existing_cat = self._find_category(name)
        if existing_cat and existing_cat != category:
            raise RegistryIOError(
                f"Name collision: '{name}' exists in {existing_cat}, cannot write to {category}"
            )
        if category not in data:
            data[category] = []
        entries = data[category]
        for i, e in enumerate(entries):
            if e.get("name") == name:
                entries[i] = entry
                entries.sort(key=lambda x: x.get("name", ""))
                atomic_write_json(self.file_path, data)
                return "updated"
        entries.append(entry)
        entries.sort(key=lambda x: x.get("name", ""))
        atomic_write_json(self.file_path, data)
        return "added"

    def remove_entry(self, name: str) -> bool:
        data = self._load()
        for cat, entries in data.items():
            for i, e in enumerate(entries):
                if e.get("name") == name:
                    entries.pop(i)
                    atomic_write_json(self.file_path, data)
                    return True
        return False


class EmporiumMarketplace:
    """Adapter for emporium marketplace.json (top-level object with plugins array)."""

    def __init__(self, path: Path) -> None:
        self.file_path = path
        self.target_name = "emporium_marketplace"

    def _load(self) -> dict:
        return json.loads(self.file_path.read_text())

    def read_entry(self, name: str) -> dict | None:
        data = self._load()
        matches = [p for p in data["plugins"] if p.get("name") == name]
        if matches:
            if len(matches) > 1:
                raise RegistryIOError(f"Data corruption: duplicate '{name}' in {self.file_path}")
            return matches[0]
        return None

    def write_entry(self, name: str, entry: dict, **kwargs) -> str:
        data = self._load()
        plugins = data["plugins"]
        for i, p in enumerate(plugins):
            if p.get("name") == name:
                plugins[i] = entry
                plugins.sort(key=lambda x: x.get("name", ""))
                atomic_write_json(self.file_path, data)
                return "updated"
        plugins.append(entry)
        plugins.sort(key=lambda x: x.get("name", ""))
        atomic_write_json(self.file_path, data)
        return "added"

    def remove_entry(self, name: str) -> bool:
        data = self._load()
        plugins = data["plugins"]
        for i, p in enumerate(plugins):
            if p.get("name") == name:
                plugins.pop(i)
                atomic_write_json(self.file_path, data)
                return True
        return False


class WebsiteMarketplace:
    """Adapter for website marketplace.json (object with plugins array)."""

    def __init__(self, path: Path) -> None:
        self.file_path = path
        self.target_name = "website_marketplace"

    def _load(self) -> dict:
        return json.loads(self.file_path.read_text())

    def read_entry(self, name: str) -> dict | None:
        data = self._load()
        plugins = data["plugins"]
        matches = [e for e in plugins if e.get("name") == name]
        if matches:
            if len(matches) > 1:
                raise RegistryIOError(f"Data corruption: duplicate '{name}' in {self.file_path}")
            return matches[0]
        return None

    def write_entry(self, name: str, entry: dict, **kwargs) -> str:
        data = self._load()
        plugins = data["plugins"]
        for i, e in enumerate(plugins):
            if e.get("name") == name:
                plugins[i] = entry
                plugins.sort(key=lambda x: x.get("name", ""))
                atomic_write_json(self.file_path, data)
                return "updated"
        plugins.append(entry)
        plugins.sort(key=lambda x: x.get("name", ""))
        atomic_write_json(self.file_path, data)
        return "added"

    def remove_entry(self, name: str) -> bool:
        data = self._load()
        plugins = data["plugins"]
        for i, e in enumerate(plugins):
            if e.get("name") == name:
                plugins.pop(i)
                atomic_write_json(self.file_path, data)
                return True
        return False


class WebsitePluginMeta:
    """Adapter for website plugin-meta.json (dict keyed by plugin name)."""

    def __init__(self, path: Path) -> None:
        self.file_path = path
        self.target_name = "website_plugin_meta"

    def _load(self) -> dict:
        return json.loads(self.file_path.read_text())

    def read_entry(self, name: str) -> dict | None:
        data = self._load()
        return data["plugins"].get(name)

    def write_entry(self, name: str, entry: dict, **kwargs) -> str:
        data = self._load()
        action = "updated" if name in data["plugins"] else "added"
        data["plugins"][name] = entry
        atomic_write_json(self.file_path, data)
        return action

    def remove_entry(self, name: str) -> bool:
        data = self._load()
        if name in data["plugins"]:
            del data["plugins"][name]
            atomic_write_json(self.file_path, data)
            return True
        return False


def read_all_versions(
    targets: dict[str, Skill7Registry | EmporiumMarketplace | WebsiteMarketplace | WebsitePluginMeta],
    name: str,
) -> dict[str, str]:
    """Return {target_name: version} for targets that store version.

    Emporium entries have no version field -- excluded from result.
    """
    versions: dict[str, str] = {}
    for target_name, adapter in targets.items():
        entry = adapter.read_entry(name)
        if entry is not None and "version" in entry:
            versions[target_name] = entry["version"]
    return versions
