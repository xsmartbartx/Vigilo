"""The IaC probe: reads Dockerfiles, Compose files, and Kubernetes
manifests from a local path for `vigilo_checks.iac`'s static checks.

Deliberately **not** like every other probe in this package: it never makes
a network request and never goes through `vigilo_security.egress_guard` —
there is nothing to guard against here, since the input is a local
checkout the caller already has read access to (a CI job's own repository
checkout, typically), not a remote target reachable only via an
attacker-influenced network path. `docs/modules.md` §3's "Probes: the only
module permitted to make outbound requests to a target" describes the
URL-scanning path; this is a second, local-file evidence source with a
different — and much simpler — trust model.
"""

from __future__ import annotations

import os
from pathlib import Path

from vigilo_core.evidence import IacFile, IacObservation

_MAX_FILE_BYTES = 64 * 1024
_MAX_FILES = 200

# Directories a local-file walk should never descend into — dependency
# trees and VCS metadata are enormous and never contain a Dockerfile a
# human actually wrote.
_SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}


def _kind_for(path: Path) -> str | None:
    name = path.name.lower()
    if name == "dockerfile" or name.startswith("dockerfile."):
        return "dockerfile"
    if name.startswith("docker-compose") and name.endswith((".yml", ".yaml")):
        return "compose"
    if name.startswith("compose") and name.endswith((".yml", ".yaml")):
        return "compose"
    if name.endswith((".yml", ".yaml")):
        # Cheap, deliberately imprecise Kubernetes-manifest detection: a
        # real YAML parse per candidate file would be needlessly heavy for
        # a probe whose only job is "is this worth handing to the checks
        # layer" — cli.py's generic-secret check makes the same
        # cheap-signal-over-full-parse tradeoff for JS bundles.
        return "kubernetes_candidate"
    return None


def _read_capped(path: Path) -> tuple[str, bool] | None:
    """The first `_MAX_FILE_BYTES` of a file (decoded leniently) and whether more followed.
    Never reads more than the cap plus one byte, whatever the file's size."""
    try:
        with path.open("rb") as handle:
            raw = handle.read(_MAX_FILE_BYTES + 1)
    except OSError:
        return None
    return raw[:_MAX_FILE_BYTES].decode("utf-8", errors="replace"), len(raw) > _MAX_FILE_BYTES


def _candidates(root: Path):
    """Files under `root` in a stable order. Skipped folders are pruned before descending, so a
    huge `node_modules` is never walked; symlinks are never followed or read."""
    if root.is_file():
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if not path.is_symlink():
                yield path


def collect_iac_evidence(root: str | Path) -> IacObservation:
    root_path = Path(root)
    if not root_path.exists():
        return IacObservation()

    files: list[IacFile] = []
    for candidate in _candidates(root_path):
        if len(files) >= _MAX_FILES:
            break

        kind = _kind_for(candidate)
        if kind is None:
            continue

        read = _read_capped(candidate)
        if read is None:
            continue
        content, truncated = read

        if kind == "kubernetes_candidate":
            if "apiVersion:" not in content or "kind:" not in content:
                continue
            kind = "kubernetes"

        try:
            rel_path = str(candidate.relative_to(root_path))
        except ValueError:
            rel_path = str(candidate)

        files.append(IacFile(path=rel_path, kind=kind, content=content, truncated=truncated))

    return IacObservation(files=files)
