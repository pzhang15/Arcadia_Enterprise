import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve()
while _REPO_ROOT != _REPO_ROOT.parent:
    if (_REPO_ROOT / "pyproject.toml").exists() and (_REPO_ROOT /
                                                     "docker").exists():
        break
    _REPO_ROOT = _REPO_ROOT.parent

_DOCKER_DIR = _REPO_ROOT / "docker"
_COMPOSE_FILE = _DOCKER_DIR / "docker-compose.yml"
_DOCKERFILE = _DOCKER_DIR / "Dockerfile"
_PLATFORM_DOCKERFILE = _REPO_ROOT / "frontends" / "platform" / "Dockerfile"


class TestDockerfileStructure:
    """Dockerfile contains required build steps."""

    def test_dockerfile_exists(self):
        assert _DOCKERFILE.exists(), (
            f"docker/Dockerfile not found at {_DOCKERFILE}")

    def test_dockerfile_seeds_northhill(self):
        content = _DOCKERFILE.read_text()
        assert "northhill_corp" in content, (
            "Dockerfile does not seed northhill_corp")

    def test_dockerfile_exposes_ports(self):
        content = _DOCKERFILE.read_text()
        assert "EXPOSE" in content
        assert "3000" in content
        assert "8080" in content
        assert "8081" in content

    def test_dockerfile_installs_uv(self):
        content = _DOCKERFILE.read_text()
        assert "uv" in content

    def test_dockerfile_copies_eval_package(self):
        content = _DOCKERFILE.read_text()
        assert "packages/eval" in content


class TestComposeStructure:
    """docker-compose.yml defines all required services."""

    def _load_compose(self):
        import yaml
        return yaml.safe_load(_COMPOSE_FILE.read_text())

    def test_compose_file_exists(self):
        assert _COMPOSE_FILE.exists()

    def test_compose_has_required_services(self):
        compose = self._load_compose()
        services = set(compose.get("services", {}).keys())
        for svc in ("arcadia-platform", "mock-services", "mirage"):
            assert svc in services, (f"Service '{svc}' missing from compose")

    def test_platform_mounts_fixture_volume(self):
        compose = self._load_compose()
        platform = compose["services"]["arcadia-platform"]
        volumes = platform.get("volumes", [])
        volume_strs = [str(v) for v in volumes]
        has_fixture = any("fixture" in v for v in volume_strs)
        assert has_fixture, ("arcadia-platform does not mount fixture volume")

    def test_platform_sets_disk_root(self):
        compose = self._load_compose()
        platform = compose["services"]["arcadia-platform"]
        env = platform.get("environment", [])
        env_strs = [str(e) for e in env]
        has_disk_root = any("DISK_ROOT" in e for e in env_strs)
        assert has_disk_root, ("arcadia-platform missing DISK_ROOT env var")

    def test_mock_services_has_healthcheck(self):
        compose = self._load_compose()
        mock = compose["services"]["mock-services"]
        assert "healthcheck" in mock

    def test_mirage_serves_northhill(self):
        compose = self._load_compose()
        mirage = compose["services"]["mirage"]
        cmd = str(mirage.get("command", ""))
        assert "northhill_corp" in cmd, (
            "mirage service does not serve northhill_corp")


class TestPlatformDockerfile:
    """Platform Dockerfile builds correctly."""

    def test_platform_dockerfile_exists(self):
        assert _PLATFORM_DOCKERFILE.exists(), (
            "frontends/platform/Dockerfile not found")

    def test_platform_dockerfile_has_server(self):
        content = _PLATFORM_DOCKERFILE.read_text()
        assert "server.py" in content, (
            "Platform Dockerfile should run server.py")


class TestSeededDataForDocker:
    """Verify seeded data matches what Docker expects."""

    def test_disk_subdirs_match_compose_volume(self, disk_root):
        """All mount subdirs exist in seeded data."""
        expected = {
            "compliance",
            "customers",
            "datadog",
            "finance",
            "gdocs",
            "github",
            "pagerduty",
            "sheets",
            "slack",
            "tickets",
            "database",
            "s3",
        }
        actual = {d.name for d in disk_root.iterdir() if d.is_dir()}
        missing = expected - actual
        assert not missing, (f"Seeded data missing subdirs: {missing}")

    def test_all_json_files_parseable(self, disk_root):
        """Docker services parse JSON; ensure no broken files."""
        broken = []
        for f in disk_root.rglob("*.json"):
            try:
                json.loads(f.read_text())
            except json.JSONDecodeError:
                broken.append(str(f.relative_to(disk_root)))
        assert not broken, f"Invalid JSON: {broken}"

    def test_all_jsonl_files_parseable(self, disk_root):
        """JSONL files must have valid JSON per line."""
        broken = []
        for f in disk_root.rglob("*.jsonl"):
            for i, line in enumerate(
                    f.read_text().strip().split("\n"),
                    1,
            ):
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    broken.append(f"{f.name}:{i}")
        assert not broken, f"Invalid JSONL lines: {broken}"

    def test_csv_files_have_headers(self, disk_root):
        """CSV exports should have header rows."""
        for f in disk_root.rglob("*.csv"):
            first_line = f.read_text().strip().split("\n")[0]
            assert "," in first_line, (f"{f.name} missing CSV header")

    def test_log_files_not_empty(self, disk_root):
        """App log files should have content."""
        for f in disk_root.rglob("*.log"):
            content = f.read_text().strip()
            assert len(content) > 0, f"{f.name} is empty"
