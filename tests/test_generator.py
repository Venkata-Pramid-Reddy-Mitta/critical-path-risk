"""The seeded generator: deterministic, always a DAG, always a real merge."""

from __future__ import annotations

import pytest

from cpr.cpm import compute_cpm, topological_order
from cpr.generator import generate_program


def test_the_same_seed_yields_an_identical_program():
    a = generate_program(seed=7)
    b = generate_program(seed=7)
    assert a.to_dict() == b.to_dict()


def test_different_seeds_yield_different_programs():
    a = generate_program(seed=1)
    b = generate_program(seed=2)
    assert a.to_dict() != b.to_dict()


def test_a_generated_program_is_always_a_dag():
    for seed in range(25):
        s = generate_program(seed=seed)
        # topological_order raises CycleError if it is not a DAG.
        order = topological_order(s)
        assert len(order) == len(s)


def test_a_generated_program_has_the_expected_task_count():
    s = generate_program(seed=3, workstreams=4, tasks_per_stream=4)
    # Four streams of four tasks, plus the integration task.
    assert len(s) == 4 * 4 + 1


def test_the_integration_task_depends_on_every_stream_tail():
    s = generate_program(seed=5, workstreams=3, tasks_per_stream=3)
    deps = set(s["INT"].deps)
    assert len(deps) == 3


def test_too_few_workstreams_is_refused():
    with pytest.raises(ValueError, match="two workstreams"):
        generate_program(seed=1, workstreams=1)


def test_too_short_a_stream_is_refused():
    with pytest.raises(ValueError, match="two tasks"):
        generate_program(seed=1, tasks_per_stream=1)


def test_bad_duration_bounds_are_refused():
    with pytest.raises(ValueError, match="duration bounds"):
        generate_program(seed=1, min_duration=10, max_duration=5)


def test_generated_programs_usually_have_a_critical_path():
    s = generate_program(seed=11)
    cpm = compute_cpm(s)
    assert cpm.project_duration > 0
    assert len(cpm.critical_path) >= 1
