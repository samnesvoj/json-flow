import pytest

from json_flow.formats import FlowError
from json_flow.query import Condition, build_predicate, get_path, project, sort_records

PEOPLE = [
    {"name": "Ada", "age": 36, "city": "London", "address": {"zip": "007"}, "tags": ["math", "engines"]},
    {"name": "Linus", "age": 29, "city": "Helsinki", "address": {"zip": "00100"}, "tags": []},
    {"name": "Grace", "age": 45, "city": "New York", "tags": ["compilers"]},
]


def names(rows):
    return [r["name"] for r in rows]


def test_get_path_handles_nesting_and_indexes():
    assert get_path(PEOPLE[0], "address.zip") == "007"
    assert get_path(PEOPLE[0], "tags.1") == "engines"
    assert get_path(PEOPLE[0], "tags.-1") == "engines"


@pytest.mark.parametrize(
    "cond, expected",
    [("age>=36", ["Ada", "Grace"]), ("age<30", ["Linus"]), ("city==New York", ["Grace"]),
     ("city!=London", ["Linus", "Grace"]), ("name~=^[AG]", ["Ada", "Grace"]), ("tags~=compil", ["Grace"]),
     ("address.zip==007", ["Ada"]), ('address.zip=="00100"', ["Linus"]), ("address.zip!=007", ["Linus", "Grace"]),
     ("age>abc", [])],
)
def test_conditions(cond, expected):
    assert names(filter(Condition.parse(cond), PEOPLE)) == expected


def test_all_vs_any():
    assert names(filter(build_predicate(["age>30", "city==London"]), PEOPLE)) == ["Ada"]
    assert names(filter(build_predicate(["age<30", "city==London"], any_of=True), PEOPLE)) == ["Ada", "Linus"]


def test_bad_conditions_are_flow_errors():
    with pytest.raises(FlowError, match="cannot parse"):
        Condition.parse("just-a-field")
    with pytest.raises(FlowError, match="regular expression"):
        Condition.parse("name~=[")


def test_project_keeps_nesting_and_skips_missing():
    assert project(PEOPLE[0], ["name", "address.zip"]) == {"name": "Ada", "address": {"zip": "007"}}
    assert project(PEOPLE[2], ["name", "address.zip"]) == {"name": "Grace"}


def test_sort_with_missing_last():
    assert names(sort_records(PEOPLE, "age", descending=True)) == ["Grace", "Ada", "Linus"]
    # zips are strings: "00100" < "007"; Grace has no zip and goes last in both directions
    assert names(sort_records(PEOPLE, "address.zip")) == ["Linus", "Ada", "Grace"]
    assert names(sort_records(PEOPLE, "address.zip", descending=True)) == ["Ada", "Linus", "Grace"]


def test_sort_mixed_types_is_a_flow_error():
    with pytest.raises(FlowError, match="mixed types"):
        sort_records([{"v": 1}, {"v": "x"}], "v")
