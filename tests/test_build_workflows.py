from pathlib import Path


WORKFLOWS = Path(__file__).parents[1] / ".github/workflows"


def workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text("utf-8")


def test_release_workflow_only_accepts_three_part_v_tags():
    source = workflow("release-build.yml")

    assert "'v[0-9]+.[0-9]+.[0-9]+'" in source
    assert '- "*"' not in source


def test_nightly_workflow_updates_only_the_existing_automatic_release():
    source = workflow("dev-build.yml")

    assert "auto-nightly-buiilds" in source
    assert "gh release edit" in source
    assert "github.com/${GITHUB_REPOSITORY}/commit/${GITHUB_SHA}" in source
    assert "cancel-in-progress: true" in source
    assert "gh release create" not in source
    assert "git push" not in source
    assert "prerelease" not in source


def test_all_platforms_build_once_and_publish_once():
    for name in ("dev-build.yml", "release-build.yml"):
        source = workflow(name)

        assert "ubuntu-22.04" in source
        assert source.count("actions/upload-artifact@v7") == 1
        assert source.count("actions/download-artifact@v8") == 1


def test_linux_build_must_start_the_backend_and_qt_window():
    for name in ("dev-build.yml", "release-build.yml"):
        source = workflow(name)

        assert "/api/ready" in source
        assert "xdotool search" in source
        assert "Failed Launching pywebview" in source
