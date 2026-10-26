from __future__ import annotations

from datetime import UTC, datetime

from vigilo_checks import IAC_REGISTRY, run_registry
from vigilo_core.evidence import EvidenceBundle, IacFile, IacObservation
from vigilo_core.models import Verdict


def _bundle(files: list[IacFile] | None = None) -> EvidenceBundle:
    iac = IacObservation(files=files or []) if files is not None else None
    return EvidenceBundle(
        bundle_id="b1",
        target_origin="local:/checkout",
        captured_at=datetime.now(UTC),
        iac=iac,
    )


def _findings_by_id(findings):
    return {f.check_id: f for f in findings}


def test_every_iac_check_runs_and_produces_one_finding_each():
    findings = run_registry(_bundle([]), IAC_REGISTRY)
    assert {c.manifest.check_id for c in IAC_REGISTRY} == {f.check_id for f in findings}


def test_checks_are_inconclusive_with_no_iac_evidence_at_all():
    findings = run_registry(_bundle(None), IAC_REGISTRY)
    assert all(f.verdict == Verdict.INCONCLUSIVE for f in findings)


def test_dockerfile_with_no_user_instruction_fails_default_root_check():
    files = [IacFile(path="Dockerfile", kind="dockerfile", content="FROM python:3.11-slim\n")]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-001"].verdict == Verdict.FAILED


def test_dockerfile_with_non_root_user_passes_default_root_check():
    files = [
        IacFile(path="Dockerfile", kind="dockerfile", content="FROM python:3.11-slim\nUSER app\n")
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-001"].verdict == Verdict.PASSED


def test_dockerfile_explicit_user_root_fails():
    files = [IacFile(path="Dockerfile", kind="dockerfile", content="FROM alpine\nUSER root\n")]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-001"].verdict == Verdict.FAILED


def test_unpinned_base_image_fails():
    files = [IacFile(path="Dockerfile", kind="dockerfile", content="FROM node\nUSER app\n")]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-002"].verdict == Verdict.FAILED


def test_pinned_base_image_passes():
    files = [
        IacFile(path="Dockerfile", kind="dockerfile", content="FROM node:20.11-slim\nUSER app\n")
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-002"].verdict == Verdict.PASSED


def test_dockerfile_hardcoded_secret_fails():
    files = [
        IacFile(
            path="Dockerfile",
            kind="dockerfile",
            content="FROM alpine\nUSER app\nENV API_KEY=sk_live_abcdef1234567890\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-003"].verdict == Verdict.FAILED


def test_dockerfile_secret_referencing_build_arg_does_not_fail():
    files = [
        IacFile(
            path="Dockerfile",
            kind="dockerfile",
            content="FROM alpine\nUSER app\nENV API_KEY=${API_KEY}\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-003"].verdict == Verdict.PASSED


def test_compose_privileged_service_fails():
    files = [
        IacFile(
            path="docker-compose.yml",
            kind="compose",
            content="services:\n  web:\n    privileged: true\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-004"].verdict == Verdict.FAILED


def test_compose_docker_socket_mount_fails():
    files = [
        IacFile(
            path="docker-compose.yml",
            kind="compose",
            content="services:\n  web:\n    volumes:\n      - /var/run/docker.sock:/var/run/docker.sock\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-005"].verdict == Verdict.FAILED


def test_compose_hardcoded_secret_fails():
    files = [
        IacFile(
            path="docker-compose.yml",
            kind="compose",
            content="services:\n  web:\n    environment:\n      DB_PASSWORD: hunter22\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-006"].verdict == Verdict.FAILED


def test_compose_host_network_fails():
    files = [
        IacFile(
            path="docker-compose.yml",
            kind="compose",
            content="services:\n  web:\n    network_mode: host\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-007"].verdict == Verdict.FAILED


def test_kubernetes_allow_privilege_escalation_fails():
    files = [
        IacFile(
            path="deploy.yaml",
            kind="kubernetes",
            content="apiVersion: apps/v1\nkind: Deployment\nsecurityContext:\n  allowPrivilegeEscalation: true\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-008"].verdict == Verdict.FAILED


def test_kubernetes_run_as_root_fails():
    files = [
        IacFile(
            path="deploy.yaml",
            kind="kubernetes",
            content="apiVersion: apps/v1\nkind: Deployment\nsecurityContext:\n  runAsUser: 0\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-009"].verdict == Verdict.FAILED


def test_kubernetes_manifest_with_no_security_context_is_not_flagged_for_run_as_root():
    files = [
        IacFile(
            path="deploy.yaml", kind="kubernetes", content="apiVersion: apps/v1\nkind: Deployment\n"
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-009"].verdict == Verdict.PASSED


def test_no_matching_files_is_not_applicable():
    findings = _findings_by_id(run_registry(_bundle([]), IAC_REGISTRY))
    assert findings["VG-IAC-001"].verdict == Verdict.NOT_APPLICABLE
    assert findings["VG-IAC-004"].verdict == Verdict.NOT_APPLICABLE
    assert findings["VG-IAC-008"].verdict == Verdict.NOT_APPLICABLE
