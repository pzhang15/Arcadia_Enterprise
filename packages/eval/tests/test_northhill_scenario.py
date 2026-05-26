import pytest
from mirage_eval.scenario import ScenarioManifest


class TestNorthhillManifest:

    def test_manifest_loads(self):
        m = ScenarioManifest.load("northhill_corp")
        assert m.id == "northhill_corp"
        assert "NorthHill" in m.name

    def test_builder_spec(self):
        m = ScenarioManifest.load("northhill_corp")
        assert m.mounts.l1.builder.endswith(":build_l1_workspace")

    def test_absolute_tasks_dir_exists(self):
        m = ScenarioManifest.load("northhill_corp")
        assert m.absolute_tasks_dir.exists()
        assert m.absolute_tasks_dir.is_dir()

    def test_lists_3_tasks(self):
        m = ScenarioManifest.load("northhill_corp")
        tasks = [p.stem for p in m.list_tasks()]
        assert len(tasks) == 3
        expected = {
            "enterprise_review",
            "incident_forensics",
            "customer_revenue_analysis",
        }
        assert set(tasks) == expected

    def test_load_each_task_validates_rubric_weights(self):
        m = ScenarioManifest.load("northhill_corp")
        for p in m.list_tasks(include_adversarial=True):
            task = m.load_task(p.stem)
            assert task.id
            assert task.prompt
            assert task.judge.rubric
            weights = sum(item.weight for item in task.judge.rubric.values())
            assert 0.99 <= weights <= 1.01, (
                f"{p.stem} weights sum to {weights}, expected ~1.0")

    def test_each_task_has_oracles(self):
        m = ScenarioManifest.load("northhill_corp")
        for p in m.list_tasks():
            task = m.load_task(p.stem)
            assert task.oracles.files_must_exist, (
                f"{p.stem} missing files_must_exist")
            assert task.oracles.ops_must_touch_prefix, (
                f"{p.stem} missing ops_must_touch_prefix")

    def test_enterprise_review_task_covers_all_departments(self):
        m = ScenarioManifest.load("northhill_corp")
        task = m.load_task("enterprise_review")
        prefixes = task.oracles.ops_must_touch_prefix
        assert any("/tickets/" in p for p in prefixes)
        assert any("/sheets/" in p for p in prefixes)
        assert any("/finance/" in p for p in prefixes)
        assert any("/pagerduty/" in p for p in prefixes)
        assert any("/customers/" in p for p in prefixes)
        assert any("/compliance/" in p for p in prefixes)

    def test_incident_forensics_touches_new_data_sources(self):
        m = ScenarioManifest.load("northhill_corp")
        task = m.load_task("incident_forensics")
        prefixes = task.oracles.ops_must_touch_prefix
        assert any("/s3/" in p for p in prefixes)
        assert any("/github/" in p for p in prefixes)
        assert any("/datadog/" in p for p in prefixes)

    def test_customer_revenue_analysis_touches_database(self):
        m = ScenarioManifest.load("northhill_corp")
        task = m.load_task("customer_revenue_analysis")
        prefixes = task.oracles.ops_must_touch_prefix
        assert any("/database/" in p for p in prefixes)
        assert any("/customers/" in p for p in prefixes)

    def test_builder_is_importable(self):
        m = ScenarioManifest.load("northhill_corp")
        builder = m.get_builder("l1")
        assert callable(builder)

    def test_seeder_is_importable(self):
        m = ScenarioManifest.load("northhill_corp")
        seeder = m.get_seeder()
        assert callable(seeder)
