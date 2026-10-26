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


def collect_iac_evidence(root: str | Path) -> IacObservation:
    root_path = Path(root)
    if not root_path.exists():
        return IacObservation()

    candidates = [root_path] if root_path.is_file() else sorted(root_path.rglob("*"))
    files: list[IacFile] = []

    for candidate in candidates:
        if len(files) >= _MAX_FILES:
            break
        if not candidate.is_file():
            continue
        # Only directories *inside* the scanned root are skipped: a checkout that itself lives
        # under a folder called "build" or "dist" must still be scanned.
        try:
            inside_root = candidate.relative_to(root_path).parts[:-1]
        except ValueError:
            inside_root = ()
        if any(part in _SKIP_DIRS for part in inside_root):
            continue

        kind = _kind_for(candidate)
        if kind is None:
            continue

        try:
            content = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if kind == "kubernetes_candidate":
            if "apiVersion:" not in content or "kind:" not in content:
                continue
            kind = "kubernetes"

        try:
            rel_path = str(candidate.relative_to(root_path))
        except ValueError:
            rel_path = str(candidate)

        files.append(IacFile(path=rel_path, kind=kind, content=content[:_MAX_FILE_BYTES]))

    return IacObservation(files=files)
