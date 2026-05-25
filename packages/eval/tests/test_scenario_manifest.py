from mirage_eval.scenario import ScenarioManifest


def test_onboarding_it_manifest_loads():
    m = ScenarioManifest.load("onboarding_it")
    assert m.id == "onboarding_it"
    assert m.mounts.l1.builder.endswith(":build_l1_workspace")
    assert m.mounts.l2 is not None
    assert m.absolute_tasks_dir.exists()


def test_onboarding_it_lists_8_tasks():
    m = ScenarioManifest.load("onboarding_it")
    primary = [p.stem for p in m.list_tasks()]
    all_t = [p.stem for p in m.list_tasks(include_adversarial=True)]
    assert len(primary) == 4
    assert len(all_t) == 8
    expected_primary = {
        "onboarding_status",
        "provision_new_hire",
        "ticket_triage",
        "incident_followup",
    }
    assert set(primary) == expected_primary


def test_load_each_task_validates():
    m = ScenarioManifest.load("onboarding_it")
    for p in m.list_tasks(include_adversarial=True):
        task = m.load_task(p.stem)
        assert task.id
        assert task.prompt
        assert task.judge.rubric
        weights = sum(item.weight for item in task.judge.rubric.values())
        assert 0.99 <= weights <= 1.01, (
            f"{p.stem} weights sum to {weights}, expected ~1.0")
