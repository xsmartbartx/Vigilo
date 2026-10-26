"""The IaC probe reads local files only; these tests use a temp directory."""

from vigilo_probes.iac_probe import collect_iac_evidence

K8S = "apiVersion: apps/v1\nkind: Deployment\n"


def _kinds(root) -> dict[str, str]:
    return {f.path: f.kind for f in collect_iac_evidence(root).files}


def test_finds_dockerfiles_compose_files_and_kubernetes_manifests(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM scratch\n")
    (tmp_path / "Dockerfile.prod").write_text("FROM scratch\n")
    (tmp_path / "docker-compose.yml").write_text("services: {}\n")
    (tmp_path / "compose.yaml").write_text("services: {}\n")
    (tmp_path / "k8s").mkdir()
    (tmp_path / "k8s" / "deploy.yaml").write_text(K8S)

    assert _kinds(tmp_path) == {
        "Dockerfile": "dockerfile",
        "Dockerfile.prod": "dockerfile",
        "docker-compose.yml": "compose",
        "compose.yaml": "compose",
        "k8s/deploy.yaml": "kubernetes",
    }


def test_ignores_unrelated_yaml_and_other_files(tmp_path):
    (tmp_path / "config.yml").write_text("name: not-kubernetes\n")
    (tmp_path / "notes.txt").write_text("FROM scratch\n")

    assert _kinds(tmp_path) == {}


def test_skips_dependency_and_vcs_folders_inside_the_root(tmp_path):
    for skipped in (".git", "node_modules", "venv"):
        (tmp_path / skipped).mkdir()
        (tmp_path / skipped / "Dockerfile").write_text("FROM scratch\n")
    (tmp_path / "Dockerfile").write_text("FROM scratch\n")

    assert list(_kinds(tmp_path)) == ["Dockerfile"]


def test_a_checkout_that_lives_under_a_build_folder_is_still_scanned(tmp_path):
    root = tmp_path / "build" / "dist" / "myapp"
    root.mkdir(parents=True)
    (root / "Dockerfile").write_text("FROM scratch\n")

    assert _kinds(root) == {"Dockerfile": "dockerfile"}


def test_a_single_file_path_works_and_a_missing_path_is_empty(tmp_path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM scratch\n")

    assert [f.kind for f in collect_iac_evidence(dockerfile).files] == ["dockerfile"]
    assert collect_iac_evidence(tmp_path / "nope").files == []


def test_content_is_capped_and_marked_truncated(tmp_path):
    (tmp_path / "Dockerfile").write_text("# " + "x" * 200_000 + "\n")
    (tmp_path / "small").mkdir()
    (tmp_path / "small" / "Dockerfile").write_text("FROM scratch\n")

    files = {f.path: f for f in collect_iac_evidence(tmp_path).files}
    assert len(files["Dockerfile"].content) == 64 * 1024
    assert files["Dockerfile"].truncated is True
    assert files["small/Dockerfile"].truncated is False


def test_discovery_stops_at_the_file_limit(tmp_path):
    for i in range(250):
        (tmp_path / f"Dockerfile.{i:03d}").write_text("FROM scratch\n")

    assert len(collect_iac_evidence(tmp_path).files) == 200


def test_symlinks_are_never_read(tmp_path):
    secret = tmp_path / "outside.txt"
    secret.write_text("FROM scratch\n")
    project = tmp_path / "project"
    project.mkdir()
    (project / "Dockerfile").symlink_to(secret)

    assert collect_iac_evidence(project).files == []
