"""Validation at the boundary: a malformed program is refused with a reason."""

from __future__ import annotations

import json

import pytest

from cpr.model import Schedule, ScheduleError, Task


def test_a_valid_task_keeps_its_fields():
    t = Task(id="A", name="Alpha", workstream="WS", duration=5, deps=("B",))
    assert t.id == "A"
    assert t.duration == 5
    assert t.deps == ("B",)


def test_a_task_id_may_not_be_empty():
    with pytest.raises(ScheduleError, match="non-empty"):
        Task(id="   ", name="x", workstream="w", duration=1)


def test_a_task_duration_must_be_a_positive_integer():
    with pytest.raises(ScheduleError, match="positive"):
        Task(id="A", name="x", workstream="w", duration=0)


def test_a_negative_duration_is_refused():
    with pytest.raises(ScheduleError, match="positive"):
        Task(id="A", name="x", workstream="w", duration=-3)


def test_a_float_duration_is_refused_as_not_an_integer():
    with pytest.raises(ScheduleError, match="integer"):
        Task(id="A", name="x", workstream="w", duration=2.5)  # type: ignore[arg-type]


def test_a_boolean_is_not_accepted_as_a_duration():
    # bool is a subclass of int in Python; the model must still reject it.
    with pytest.raises(ScheduleError, match="integer"):
        Task(id="A", name="x", workstream="w", duration=True)  # type: ignore[arg-type]


def test_a_task_may_not_depend_on_itself():
    with pytest.raises(ScheduleError, match="depend on itself"):
        Task(id="A", name="x", workstream="w", duration=1, deps=("A",))


def test_a_program_needs_a_tasks_array():
    with pytest.raises(ScheduleError, match="tasks"):
        Schedule.from_dict({"nope": []})


def test_an_empty_tasks_array_is_refused():
    with pytest.raises(ScheduleError, match="non-empty"):
        Schedule.from_dict({"tasks": []})


def test_each_task_row_must_be_an_object():
    with pytest.raises(ScheduleError, match="must be an object"):
        Schedule.from_dict({"tasks": ["A"]})


def test_a_missing_field_names_the_field():
    with pytest.raises(ScheduleError, match="missing fields"):
        Schedule.from_dict({"tasks": [{"id": "A", "name": "x", "workstream": "w"}]})


def test_a_duplicate_id_is_refused():
    rows = [
        {"id": "A", "name": "x", "workstream": "w", "duration": 1},
        {"id": "A", "name": "y", "workstream": "w", "duration": 2},
    ]
    with pytest.raises(ScheduleError, match="duplicate"):
        Schedule.from_dict({"tasks": rows})


def test_a_dependency_on_an_unknown_task_is_refused():
    rows = [{"id": "A", "name": "x", "workstream": "w", "duration": 1, "deps": ["Z"]}]
    with pytest.raises(ScheduleError, match="not in the program"):
        Schedule.from_dict({"tasks": rows})


def test_missing_deps_key_defaults_to_no_dependencies():
    s = Schedule.from_dict({"tasks": [{"id": "A", "name": "x", "workstream": "w", "duration": 1}]})
    assert s["A"].deps == ()


def test_null_deps_is_treated_as_empty():
    rows = [{"id": "A", "name": "x", "workstream": "w", "duration": 1, "deps": None}]
    s = Schedule.from_dict({"tasks": rows})
    assert s["A"].deps == ()


def test_schedule_length_counts_tasks(program):
    assert len(program) == 16


def test_schedule_ids_preserve_insertion_order(program):
    assert program.ids[0] == "CM1"
    assert program.ids[-1] == "TD4"


def test_iterating_a_schedule_yields_tasks(program):
    ids = [t.id for t in program]
    assert ids == list(program.ids)


def test_successors_are_the_tasks_that_depend_on_a_task(program):
    assert set(program.successors("CM1")) == {"CM2", "AM1", "DM1"}


def test_a_leaf_task_has_no_successors(program):
    assert program.successors("TD4") == ()


def test_with_duration_returns_a_changed_copy_and_leaves_the_original(program):
    changed = program.with_duration("CM1", 100)
    assert changed["CM1"].duration == 100
    assert program["CM1"].duration == 8


def test_with_duration_on_an_unknown_task_is_refused(program):
    with pytest.raises(ScheduleError, match="unknown task"):
        program.with_duration("NOPE", 5)


def test_a_schedule_round_trips_through_dict(program):
    again = Schedule.from_dict(program.to_dict())
    assert again.ids == program.ids
    assert again["AM3"].duration == program["AM3"].duration


def test_from_json_reports_a_missing_file():
    with pytest.raises(ScheduleError, match="not found"):
        Schedule.from_json("/no/such/program.json")


def test_from_json_reports_bad_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ScheduleError, match="could not parse"):
        Schedule.from_json(p)


def test_from_json_loads_a_written_schedule(tmp_path, program):
    p = tmp_path / "prog.json"
    p.write_text(json.dumps(program.to_dict()), encoding="utf-8")
    loaded = Schedule.from_json(p)
    assert len(loaded) == len(program)
