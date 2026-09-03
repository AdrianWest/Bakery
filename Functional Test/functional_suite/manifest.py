"""!
@file manifest.py

@brief Recursive file manifest and hash-comparison utilities.

@section description_manifest Detailed Description
Implements the manifest/hash primitives required throughout
`Functional Test/test_spec.md`: SETUP-07 (fixture copy verification),
INST-06 (installed-plugin verification), BASE-01/BASE-02 (pre-run project
baseline), FIX-01 (source fixture integrity), and IDM-06 (idempotence
comparison). Every caller builds a `Manifest` from a directory and compares
two manifests with `diff_manifests`, so the comparison semantics (relative
path, size, SHA-256) stay identical everywhere they are required.

@section notes_manifest Notes
- Hashing streams files in fixed-size chunks so large 3D models do not need
  to be loaded fully into memory.
- `is_volatile` centralizes the documented volatile-file exclusion list from
  `config.VOLATILE_FILE_SUFFIXES` (Section 11) instead of an unrestricted
  glob pattern.
"""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List

from . import config

_HASH_CHUNK_SIZE = 1024 * 1024


def is_volatile(relative_path: str) -> bool:
    """
    @brief Determine whether a relative path is a documented volatile file

    @param relative_path: Path relative to a project or install root, using
        forward slashes
    @return True when the path matches a documented volatile suffix from
        `config.VOLATILE_FILE_SUFFIXES`
    """
    lowered = relative_path.lower()
    return any(lowered.endswith(suffix.lower()) for suffix in config.VOLATILE_FILE_SUFFIXES)


def hash_file(path: Path) -> str:
    """
    @brief Compute the SHA-256 hash of a file's contents

    @param path: File to hash
    @return Lowercase hex-encoded SHA-256 digest

    @throws OSError if the file cannot be read
    """
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class ManifestEntry:
    """!
    @brief One file entry within a `Manifest`.

    @section attributes Attributes
    - relative_path (str): Path relative to the manifest root, forward
      slashes only.
    - size (int): File size in bytes.
    - sha256 (str): Lowercase hex-encoded SHA-256 digest.
    """

    relative_path: str
    size: int
    sha256: str


@dataclass
class Manifest:
    """!
    @brief A recursive, hashed snapshot of every file below a root directory.

    @section attributes Attributes
    - root (Path): Directory the manifest was built from.
    - entries (Dict[str, ManifestEntry]): Entries keyed by relative path.
    """

    root: Path
    entries: Dict[str, ManifestEntry] = field(default_factory=dict)

    def to_json(self) -> dict:
        """
        @brief Serialize this manifest to a JSON-compatible dictionary

        @return Dictionary with "root" and "entries" keys
        """
        return {
            "root": str(self.root),
            "entries": {
                relative_path: {
                    "size": entry.size,
                    "sha256": entry.sha256,
                }
                for relative_path, entry in sorted(self.entries.items())
            },
        }

    def write(self, path: Path) -> None:
        """
        @brief Write this manifest to disk as JSON

        @param path: Destination file path
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_json(), indent=2), encoding="utf-8")


def build_manifest(
    root: Path,
    exclude_dirs: Iterable[str] = (),
    include_hidden: bool = True,
) -> Manifest:
    """
    @brief Recursively build a hashed manifest of every file below root

    @param root: Directory to scan
    @param exclude_dirs: Directory names to skip entirely (matched by name,
        anywhere in the tree)
    @param include_hidden: When False, skip files/directories whose name
        starts with a dot
    @return Populated Manifest

    @throws FileNotFoundError if root does not exist
    """
    if not root.is_dir():
        raise FileNotFoundError(f"Manifest root does not exist: {root}")

    exclude = set(exclude_dirs)
    entries: Dict[str, ManifestEntry] = {}
    for candidate in root.rglob("*"):
        if candidate.is_dir():
            continue
        if any(part in exclude for part in candidate.relative_to(root).parts):
            continue
        if not include_hidden and any(
            part.startswith(".") for part in candidate.relative_to(root).parts
        ):
            continue
        relative_path = candidate.relative_to(root).as_posix()
        entries[relative_path] = ManifestEntry(
            relative_path=relative_path,
            size=candidate.stat().st_size,
            sha256=hash_file(candidate),
        )
    return Manifest(root=root, entries=entries)


@dataclass
class ManifestDiff:
    """!
    @brief Result of comparing two manifests.

    @section attributes Attributes
    - added (List[str]): Relative paths present only in the "after" manifest.
    - removed (List[str]): Relative paths present only in the "before"
      manifest.
    - changed (List[str]): Relative paths present in both manifests with a
      different size or hash.
    """

    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    changed: List[str] = field(default_factory=list)

    @property
    def is_identical(self) -> bool:
        """
        @brief Whether the two compared manifests were identical

        @return True when there are no added, removed, or changed entries
        """
        return not (self.added or self.removed or self.changed)

    def to_json(self) -> dict:
        """
        @brief Serialize this diff to a JSON-compatible dictionary

        @return Dictionary with "added", "removed", and "changed" keys
        """
        return {
            "added": sorted(self.added),
            "removed": sorted(self.removed),
            "changed": sorted(self.changed),
        }


def diff_manifests(
    before: Manifest,
    after: Manifest,
    ignore_volatile: bool = False,
) -> ManifestDiff:
    """
    @brief Compare two manifests by relative path, size, and SHA-256

    @param before: Manifest captured earlier
    @param after: Manifest captured later
    @param ignore_volatile: When True, exclude documented volatile files
        (config.VOLATILE_FILE_SUFFIXES) from the comparison, as required for
        the idempotence check (test_spec.md IDM-06)
    @return ManifestDiff describing every difference
    """
    before_keys = set(before.entries)
    after_keys = set(after.entries)
    if ignore_volatile:
        before_keys = {key for key in before_keys if not is_volatile(key)}
        after_keys = {key for key in after_keys if not is_volatile(key)}

    diff = ManifestDiff(
        added=sorted(after_keys - before_keys),
        removed=sorted(before_keys - after_keys),
    )
    for key in sorted(before_keys & after_keys):
        before_entry = before.entries[key]
        after_entry = after.entries[key]
        if before_entry.size != after_entry.size or before_entry.sha256 != after_entry.sha256:
            diff.changed.append(key)
    return diff
