import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

ROOT = Path(__file__).parents[1]


def _appimage_spec(binaries=()):
    captured = {}

    def analysis(*args, **kwargs):
        captured["analysis"] = kwargs
        return SimpleNamespace(
            scripts=[], binaries=list(binaries), datas=kwargs["datas"], pure=[]
        )

    def exe(*args, **kwargs):
        captured["binaries"] = args[2]

    namespace = {
        "Analysis": analysis,
        "PYZ": lambda *args, **kwargs: None,
        "EXE": exe,
    }
    spec = ROOT / "palworld-pal-editor.spec"
    exec(compile(spec.read_bytes(), spec, "exec"), namespace)  # noqa: S102
    return captured


def _pyinstaller_add_data(script: str, separator: str) -> set[tuple[str, str]]:
    if script == "build_appimage.sh":
        return {tuple(data) for data in _appimage_spec()["analysis"]["datas"]}

    lines = (ROOT / script).read_text("utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip().startswith("pyinstaller "))
    command_lines = [lines[start].strip()]
    while command_lines[-1].endswith("\\"):
        command_lines.append(lines[start + len(command_lines)].strip())
    command = " ".join(line.removesuffix("\\") for line in command_lines)
    values = (
        argument.removeprefix("--add-data=")
        for argument in shlex.split(command)
        if argument.startswith("--add-data=")
    )
    return {tuple(value.split(separator, 1)) for value in values}


def _required_runtime_members(prefix: str, package: Path) -> set[str]:
    data = {
        f"{prefix}/assets/data/{path.name}"
        for path in (package / "assets/data").glob("*.json")
    }
    icons = {
        f"{prefix}/assets/icons/{path.relative_to(package / 'assets/icons').as_posix()}"
        for path in (package / "assets/icons").rglob("*.png")
    }
    webui = {
        f"{prefix}/webui/{path.relative_to(package / 'webui').as_posix()}"
        for path in (package / "webui").rglob("*")
        if path.is_file()
    }
    return data | icons | webui


def _archive_members() -> tuple[set[str], set[str], set[str], set[str]]:
    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp) / "source"
        project.mkdir()
        for name in ("pyproject.toml", "MANIFEST.in", "README.md", "LICENSE"):
            shutil.copy2(ROOT / name, project / name)
        shutil.copytree(
            ROOT / "src",
            project / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"),
        )
        package = project / "src/palworld_pal_editor"
        webui = package / "webui"
        shutil.rmtree(webui, ignore_errors=True)
        subprocess.run(
            [
                shutil.which("npm") or "npm",
                "--prefix",
                str(ROOT / "frontend/palworld-pal-editor-webui"),
                "run",
                "build",
                "--",
                "--outDir",
                str(webui),
                "--emptyOutDir",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        assert (webui / "index.html").is_file()
        assert any((webui / "assets").glob("*.js"))
        assert any((webui / "assets").glob("*.css"))
        assert (webui / "docs/keep_this_project_alive.md").is_file()
        assert (webui / "icons/512.png").is_file()
        dist = Path(temp) / "dist"
        dist.mkdir()
        subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; from setuptools import build_meta; "
                    "output = sys.argv[1]; "
                    "build_meta.build_sdist(output); "
                    "build_meta.build_wheel(output)"
                ),
                str(dist),
            ],
            cwd=project,
            check=True,
            capture_output=True,
            text=True,
        )
        wheel = next(dist.glob("*.whl"))
        sdist = next(dist.glob("*.tar.gz"))
        with zipfile.ZipFile(wheel) as archive:
            wheel_members = set(archive.namelist())
        with tarfile.open(sdist, "r:gz") as archive:
            sdist_members = {
                "/".join(PurePosixPath(name).parts[1:]) for name in archive.getnames()
            }
        return (
            wheel_members,
            sdist_members,
            _required_runtime_members("palworld_pal_editor", package),
            _required_runtime_members("src/palworld_pal_editor", package),
        )


def _assert_archive_policy(members: set[str], required: set[str], prefix: str) -> None:
    assert required <= members, f"missing runtime members: {sorted(required - members)[:10]}"

    forbidden = []
    for name in members:
        path = PurePosixPath(name)
        lower = name.casefold()
        if (
            ".local-tools" in path.parts
            or "docs/superpowers" in lower
            or f"{prefix}/assets/tools/" in name
            or path.name in {"game_asset_provenance.json", "provenance.json", "pal_icon_map.json"}
            or (path.name.startswith("T_") and path.suffix.casefold() == ".png")
            or path.suffix.casefold() in {".uasset", ".ubulk", ".uexp", ".locres"}
        ):
            forbidden.append(name)
    assert not forbidden, f"forbidden package members: {sorted(forbidden)[:10]}"


def test_release_build_collects_only_runtime_assets_and_webui():
    expected = {
        ("src/palworld_pal_editor/assets/data", "assets/data"),
        ("src/palworld_pal_editor/assets/icons", "assets/icons"),
        ("src/palworld_pal_editor/webui", "webui"),
    }
    assert _pyinstaller_add_data("build_executable.ps1", ";") == expected
    assert _pyinstaller_add_data("build_executable.sh", ":") == expected
    assert _pyinstaller_add_data("build_appimage.sh", ":") == expected

    ignored = (ROOT / ".gitignore").read_text("utf-8").splitlines()
    assert "src/palworld_pal_editor/webui/" in ignored
    git_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if git_root.returncode == 0 and Path(git_root.stdout.strip()) == ROOT:
        tracked_webui = subprocess.run(
            ["git", "ls-files", "--", "src/palworld_pal_editor/webui"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert not tracked_webui.strip()

    release_commands = {
        "build_executable.ps1": (
            "& $NPM_CMD run build",
            (
                'Move-Item -Path ".\\frontend\\palworld-pal-editor-webui\\dist\\*" '
                '-Destination ".\\src\\palworld_pal_editor\\webui" -Force'
            ),
        ),
        "build_executable.sh": (
            "${NPM_CMD} run build",
            (
                'mv "./frontend/palworld-pal-editor-webui/dist" '
                '"./src/palworld_pal_editor/webui"'
            ),
        ),
        "build_appimage.sh": (
            "$NPM_CMD run build",
            (
                'mv "./frontend/palworld-pal-editor-webui/dist" '
                '"./src/palworld_pal_editor/webui"'
            ),
        ),
    }
    for script, (build, publish) in release_commands.items():
        source = (ROOT / script).read_text("utf-8")
        pyinstaller = re.search(r"(?m)^pyinstaller (?:--onefile|--clean)(?:\s|$)", source)
        assert pyinstaller is not None
        assert source.index(build) < source.index(publish) < pyinstaller.start()


def test_appimage_uses_gpu_by_default_and_ci_smoke_tests_use_software_rendering():
    source = (ROOT / "build_appimage.sh").read_text("utf-8")
    spec = _appimage_spec()["analysis"]

    assert 'pywebview[pyside6]==4.4.1' in source
    assert "webview.platforms.qt" in spec["hiddenimports"]
    assert 'export PYWEBVIEW_GUI="qt"' in source
    assert 'QT_OPENGL="software"' not in source
    assert 'QT_QUICK_BACKEND="software"' not in source
    assert "--disable-gpu" not in source
    assert "ldd " not in source
    assert "LD_LIBRARY_PATH" not in source
    assert "--appimage-extract-and-run" in source

    for workflow in ("dev-build.yml", "release-build.yml"):
        workflow_source = (ROOT / ".github" / "workflows" / workflow).read_text("utf-8")
        assert 'QT_OPENGL=software QT_QUICK_BACKEND=software QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu"' in workflow_source


def test_appimage_uses_host_gbm_library():
    captured = _appimage_spec(
        [
            ("libgbm.so.1", "/build/libgbm.so.1", "BINARY"),
            ("libstdc++.so.6", "/build/libstdc++.so.6", "BINARY"),
        ]
    )

    assert [binary[0] for binary in captured["binaries"]] == ["libstdc++.so.6"]


def test_pages_workflow_deploys_release_tags_and_manual_refs():
    workflow = ROOT / ".github/workflows/pages.yml"
    assert workflow.is_file(), "missing dedicated GitHub Pages workflow"

    source = workflow.read_text("utf-8")
    triggers = source.split("concurrency:", 1)[0]
    expected = (
        "v[0-9]+.[0-9]+.[0-9]+",
        "workflow_dispatch:",
        "required: false",
        "ref: ${{ inputs.ref || github.sha }}",
        "group: github-pages",
        "cancel-in-progress: true",
        "contents: read",
        "pages: write",
        "id-token: write",
        "actions/configure-pages@v5",
        "BASE_PATH: ${{ steps.pages.outputs.base_path }}",
        "run: npm ci",
        'npm run build -- --base "${BASE_PATH:-}/"',
        "actions/upload-pages-artifact@v4",
        "frontend/palworld-pal-editor-webui/dist",
        "actions/deploy-pages@v4",
        "name: github-pages",
    )
    assert all(value in source for value in expected)
    assert "branches:" not in triggers


def test_built_archives_include_runtime_assets_and_exclude_maintainer_files():
    wheel, sdist, wheel_required, sdist_required = _archive_members()
    _assert_archive_policy(wheel, wheel_required, "palworld_pal_editor")
    _assert_archive_policy(sdist, sdist_required, "src/palworld_pal_editor")
