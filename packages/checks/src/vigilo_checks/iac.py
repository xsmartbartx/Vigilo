"""IAC category (container/infrastructure-as-code posture): static checks
over Dockerfiles, Docker Compose files, and Kubernetes manifests, read by
`vigilo_probes.iac_probe.collect_iac_evidence` from a local checkout — see
that probe's docstring for why this evidence source has no egress guard.

Deliberately **not** part of `vigilo_checks.REGISTRY` (the URL-scan
registry `apps/cli`'s `vigilo scan` runs): these checks need
`EvidenceBundle.iac`, which the network-scanning pipeline never populates,
and mixing them in would silently make every existing URL scan's finding
count depend on whether a caller happened to pass local files. `IAC_REGISTRY`
is its own list; `apps/cli`'s `vigilo scan-iac <path>` (or any other
caller) runs it explicitly via `run_registry(bundle, IAC_REGISTRY)`.

Same aggregation convention `vigilo_checks.cli` uses for
`bundle.fetched_scripts`: one verdict per check across every matching file
in the bundle, not one verdict per file — a scan of ten Dockerfiles is
still one `VG-IAC-001` finding, naming the first offending file.
"""

from __future__ import annotations

import re

from vigilo_checks.registry import Check, CheckResult, requires
from vigilo_core.evidence import EvidenceBundle, IacFile
from vigilo_core.models import CheckManifest, Confidence, Severity, Tier, Verdict

_ROOT_USER_PATTERN = re.compile(r"^\s*USER\s+(root|0)\s*$", re.IGNORECASE | re.MULTILINE)
_ANY_USER_PATTERN = re.compile(r"^\s*USER\s+\S+", re.IGNORECASE | re.MULTILINE)
_FROM_PATTERN = re.compile(r"^\s*FROM\s+([^\s]+)(?:\s+AS\s+\S+)?\s*$", re.IGNORECASE | re.MULTILINE)
_HARDCODED_SECRET_PATTERN = re.compile(
    r"(?:PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY)\s*[:=]\s*['\"]?(?!\s*\$|\{\{)[^\s'\"$]{4,}",
    re.IGNORECASE,
)
_PRIVILEGED_PATTERN = re.compile(r"privileged\s*:\s*true", re.IGNORECASE)
_DOCKER_SOCKET_PATTERN = re.compile(r"/var/run/docker\.sock")
_ALLOW_PRIVILEGE_ESCALATION_PATTERN = re.compile(
    r"allowPrivilegeEscalation\s*:\s*true", re.IGNORECASE
)
_RUN_AS_ROOT_PATTERN = re.compile(r"runAsUser\s*:\s*0\b")
_HOST_NETWORK_PATTERN = re.compile(r"network_mode\s*:\s*['\"]?host['\"]?", re.IGNORECASE)


def _files_of_kind(bundle: EvidenceBundle, kind: str) -> list[IacFile]:
    if bundle.iac is None:
        return []
    return [f for f in bundle.iac.files if f.kind == kind]


def _first_match_check(
    kind: str,
    pattern: re.Pattern[str],
    fail_detail: str,
    pass_detail: str,
    invert: bool = False,
):
    """`invert=True`: FAIL when the pattern is *absent* (e.g. "no USER
    instruction at all" — a Dockerfile with no USER instruction runs as
    root by Docker's own default, same as an explicit `USER root`)."""

    @requires("iac")
    def _check(bundle: EvidenceBundle) -> CheckResult:
        files = _files_of_kind(bundle, kind)
        if not files:
            return CheckResult(Verdict.NOT_APPLICABLE, f"no {kind} files found")
        for f in files:
            found = bool(pattern.search(f.content))
            if found != invert:
                return CheckResult(Verdict.FAILED, f"{fail_detail} ({f.path})", f.path)
        return CheckResult(Verdict.PASSED, pass_detail)

    return _check


# --- VG-IAC-001: Dockerfile does not default to root -------------------------


@requires("iac")
def _check_no_default_root(bundle: EvidenceBundle) -> CheckResult:
    files = _files_of_kind(bundle, "dockerfile")
    if not files:
        return CheckResult(Verdict.NOT_APPLICABLE, "no Dockerfile found")
    for f in files:
        if _ROOT_USER_PATTERN.search(f.content):
            return CheckResult(
                Verdict.FAILED, f"Dockerfile sets USER root explicitly ({f.path})", f.path
            )
        if not _ANY_USER_PATTERN.search(f.content):
            return CheckResult(
                Verdict.FAILED,
                f"Dockerfile has no USER instruction, so the container runs as root by default ({f.path})",
                f.path,
            )
    return CheckResult(Verdict.PASSED, "every Dockerfile sets a non-root USER")


CHECK_IAC_NO_DEFAULT_ROOT = Check(
    manifest=CheckManifest(
        check_id="VG-IAC-001",
        category="IAC",
        title="Container does not run as root by default",
        description="A Dockerfile with no USER instruction (or an explicit USER root) runs its process as root, giving a container-escape or dependency-compromise bug far more reach than it needs.",
        severity_default=Severity.HIGH,
        confidence=Confidence.CONFIRMED,
        weight=7,
        tier_required=Tier.PASSIVE,
        references=["https://docs.docker.com/engine/security/#linux-kernel-capabilities"],
        remediation_template="Add a dedicated `USER` instruction (e.g. `RUN adduser -D app && USER app`) before the container's entrypoint runs.",
        introduced_in="0.1",
    ),
    evaluate=_check_no_default_root,
)


# --- VG-IAC-002: base image is pinned, not :latest ---------------------------


@requires("iac")
def _check_base_image_pinned(bundle: EvidenceBundle) -> CheckResult:
    files = _files_of_kind(bundle, "dockerfile")
    if not files:
        return CheckResult(Verdict.NOT_APPLICABLE, "no Dockerfile found")
    for f in files:
        for match in _FROM_PATTERN.finditer(f.content):
            image = match.group(1)
            if image.lower() == "scratch":
                continue
            if "@sha256:" in image:
                continue
            if ":" not in image.split("/")[-1] or image.endswith(":latest"):
                return CheckResult(
                    Verdict.FAILED,
                    f"base image `{image}` is unpinned (no tag, or `:latest`) in {f.path}",
                    f.path,
                )
    return CheckResult(Verdict.PASSED, "every base image is pinned to a specific tag or digest")


CHECK_IAC_BASE_IMAGE_PINNED = Check(
    manifest=CheckManifest(
        check_id="VG-IAC-002",
        category="IAC",
        title="Base image is pinned, not :latest",
        description="An unpinned or `:latest` base image makes builds non-reproducible and can silently pull in a newer image with new vulnerabilities or behavior between builds.",
        severity_default=Severity.MEDIUM,
        confidence=Confidence.CONFIRMED,
        weight=3,
        tier_required=Tier.PASSIVE,
        references=[
            "https://docs.docker.com/build/building/best-practices/#pin-base-image-versions"
        ],
        remediation_template="Pin the base image to a specific version tag or, ideally, a `@sha256:` digest.",
        introduced_in="0.1",
    ),
    evaluate=_check_base_image_pinned,
)


# --- VG-IAC-003: no hardcoded secret in Dockerfile ENV/ARG -------------------

_check_no_dockerfile_secret = _first_match_check(
    "dockerfile",
    _HARDCODED_SECRET_PATTERN,
    "a hardcoded secret-shaped value was found in an ENV/ARG instruction",
    "no hardcoded secret-shaped value found in any Dockerfile",
)

CHECK_IAC_NO_DOCKERFILE_SECRET = Check(
    manifest=CheckManifest(
        check_id="VG-IAC-003",
        category="IAC",
        title="No hardcoded secret in a Dockerfile",
        description="A password/token/key literal baked into an ENV or ARG instruction is readable from the image's layer history by anyone who can pull the image, even after a later layer overwrites it.",
        severity_default=Severity.CRITICAL,
        confidence=Confidence.INDICATED,
        weight=8,
        tier_required=Tier.PASSIVE,
        references=[
            "https://docs.docker.com/build/building/best-practices/#dont-install-unnecessary-packages"
        ],
        remediation_template="Pass secrets at runtime (env vars, mounted files, or a secrets manager) instead of baking them into the image; use Docker BuildKit's `--mount=type=secret` for build-time-only secrets.",
        false_positive_notes="A value that is itself a build-arg reference (`${VAR}`) or template placeholder (`{{ .Secret }}`) is not flagged.",
        introduced_in="0.1",
    ),
    evaluate=_check_no_dockerfile_secret,
)


# --- VG-IAC-004: Compose service is not privileged ---------------------------

_check_compose_not_privileged = _first_match_check(
    "compose",
    _PRIVILEGED_PATTERN,
    "a service runs in privileged mode",
    "no service runs in privileged mode",
)

CHECK_IAC_COMPOSE_NOT_PRIVILEGED = Check(
    manifest=CheckManifest(
        check_id="VG-IAC-004",
        category="IAC",
        title="Compose service does not run privileged",
        description="`privileged: true` gives a container almost all host-kernel capabilities — a compromise inside it is effectively a host compromise.",
        severity_default=Severity.CRITICAL,
        confidence=Confidence.CONFIRMED,
        weight=9,
        tier_required=Tier.PASSIVE,
        references=["https://docs.docker.com/reference/compose-file/services/#privileged"],
        remediation_template="Remove `privileged: true`; grant only the specific Linux capabilities the service needs via `cap_add`.",
        introduced_in="0.1",
    ),
    evaluate=_check_compose_not_privileged,
)


# --- VG-IAC-005: Compose does not mount the Docker socket --------------------

_check_no_docker_socket_mount = _first_match_check(
    "compose",
    _DOCKER_SOCKET_PATTERN,
    "a service mounts the host Docker socket",
    "no service mounts the host Docker socket",
)

CHECK_IAC_NO_DOCKER_SOCKET_MOUNT = Check(
    manifest=CheckManifest(
        check_id="VG-IAC-005",
        category="IAC",
        title="Docker socket is not mounted into a container",
        description="Mounting `/var/run/docker.sock` into a container gives that container root-equivalent control of the host — any code-execution bug inside it becomes a host takeover.",
        severity_default=Severity.CRITICAL,
        confidence=Confidence.CONFIRMED,
        weight=9,
        tier_required=Tier.PASSIVE,
        references=["https://docs.docker.com/engine/security/#docker-daemon-attack-surface"],
        remediation_template="Avoid mounting the Docker socket; if a service genuinely needs to manage containers, use a scoped proxy (e.g. Tecnativa's docker-socket-proxy) instead of direct access.",
        introduced_in="0.1",
    ),
    evaluate=_check_no_docker_socket_mount,
)


# --- VG-IAC-006: no hardcoded secret in Compose environment ------------------

_check_no_compose_secret = _first_match_check(
    "compose",
    _HARDCODED_SECRET_PATTERN,
    "a hardcoded secret-shaped value was found in a service's environment",
    "no hardcoded secret-shaped value found in any Compose file",
)

CHECK_IAC_NO_COMPOSE_SECRET = Check(
    manifest=CheckManifest(
        check_id="VG-IAC-006",
        category="IAC",
        title="No hardcoded secret in a Compose file",
        description="A password/token/key literal committed directly into a Compose file's `environment:` block ends up in source control history even after it's rotated out of the running config.",
        severity_default=Severity.HIGH,
        confidence=Confidence.INDICATED,
        weight=6,
        tier_required=Tier.PASSIVE,
        references=["https://docs.docker.com/compose/how-tos/environment-variables/"],
        remediation_template="Reference an `.env` file (excluded from version control) or `env_file:`/Compose `secrets:` instead of a literal value.",
        false_positive_notes="A value that is itself a variable reference (`${VAR}`) or template placeholder is not flagged.",
        introduced_in="0.1",
    ),
    evaluate=_check_no_compose_secret,
)


# --- VG-IAC-007: Compose service does not use host networking ---------------

_check_no_host_network = _first_match_check(
    "compose",
    _HOST_NETWORK_PATTERN,
    "a service uses host networking",
    "no service uses host networking",
)

CHECK_IAC_NO_HOST_NETWORK = Check(
    manifest=CheckManifest(
        check_id="VG-IAC-007",
        category="IAC",
        title="Compose service does not use host networking",
        description="`network_mode: host` removes network isolation between the container and the host, exposing every host port the container binds and vice versa.",
        severity_default=Severity.MEDIUM,
        confidence=Confidence.CONFIRMED,
        weight=4,
        tier_required=Tier.PASSIVE,
        references=["https://docs.docker.com/engine/network/drivers/host/"],
        remediation_template="Use the default bridge network and explicit `ports:` mappings instead of `network_mode: host`.",
        introduced_in="0.1",
    ),
    evaluate=_check_no_host_network,
)


# --- VG-IAC-008: Kubernetes pod spec does not allow privilege escalation ----

_check_k8s_no_privilege_escalation = _first_match_check(
    "kubernetes",
    _ALLOW_PRIVILEGE_ESCALATION_PATTERN,
    "a container sets allowPrivilegeEscalation: true",
    "no container allows privilege escalation",
)

CHECK_IAC_K8S_NO_PRIVILEGE_ESCALATION = Check(
    manifest=CheckManifest(
        check_id="VG-IAC-008",
        category="IAC",
        title="Kubernetes pod does not allow privilege escalation",
        description="`allowPrivilegeEscalation: true` lets a process gain more privileges than its parent (e.g. via a setuid binary), undermining a securityContext that is otherwise locked down.",
        severity_default=Severity.HIGH,
        confidence=Confidence.CONFIRMED,
        weight=6,
        tier_required=Tier.PASSIVE,
        references=["https://kubernetes.io/docs/tasks/configure-pod-container/security-context/"],
        remediation_template="Set `securityContext.allowPrivilegeEscalation: false` on every container.",
        introduced_in="0.1",
    ),
    evaluate=_check_k8s_no_privilege_escalation,
)


# --- VG-IAC-009: Kubernetes pod does not explicitly run as root --------------

_check_k8s_no_run_as_root = _first_match_check(
    "kubernetes",
    _RUN_AS_ROOT_PATTERN,
    "a container sets runAsUser: 0",
    "no container explicitly runs as root (uid 0)",
)

CHECK_IAC_K8S_NO_RUN_AS_ROOT = Check(
    manifest=CheckManifest(
        check_id="VG-IAC-009",
        category="IAC",
        title="Kubernetes pod does not explicitly run as root",
        description="`runAsUser: 0` explicitly runs a container's process as root inside the pod, the same widened blast radius VG-IAC-001 flags for a bare Dockerfile.",
        severity_default=Severity.HIGH,
        confidence=Confidence.CONFIRMED,
        weight=6,
        tier_required=Tier.PASSIVE,
        references=["https://kubernetes.io/docs/tasks/configure-pod-container/security-context/"],
        remediation_template="Set `securityContext.runAsNonRoot: true` and a non-zero `runAsUser` on the pod or container spec.",
        false_positive_notes="A manifest with no explicit `runAsUser` at all is not flagged here — the image's own Dockerfile USER is what determines the effective user in that case (see VG-IAC-001).",
        introduced_in="0.1",
    ),
    evaluate=_check_k8s_no_run_as_root,
)


CHECKS: list[Check] = [
    CHECK_IAC_NO_DEFAULT_ROOT,
    CHECK_IAC_BASE_IMAGE_PINNED,
    CHECK_IAC_NO_DOCKERFILE_SECRET,
    CHECK_IAC_COMPOSE_NOT_PRIVILEGED,
    CHECK_IAC_NO_DOCKER_SOCKET_MOUNT,
    CHECK_IAC_NO_COMPOSE_SECRET,
    CHECK_IAC_NO_HOST_NETWORK,
    CHECK_IAC_K8S_NO_PRIVILEGE_ESCALATION,
    CHECK_IAC_K8S_NO_RUN_AS_ROOT,
]
