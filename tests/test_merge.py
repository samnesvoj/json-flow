import pytest

from json_flow.formats import FlowError
from json_flow.merge import deep_merge, merge_by_key, merge_documents


def test_deep_merge_nested_objects_without_mutating_inputs():
    base = {"db": {"host": "localhost", "port": 5432}, "tags": ["a"]}
    update = {"db": {"port": 6543, "user": "app"}, "tags": ["b"]}
    assert deep_merge(base, update) == {"db": {"host": "localhost", "port": 6543, "user": "app"}, "tags": ["a", "b"]}
    assert deep_merge(base, update, list_mode="replace")["tags"] == ["b"]
    assert base == {"db": {"host": "localhost", "port": 5432}, "tags": ["a"]}


def test_scalar_and_type_conflicts_take_the_newer_value():
    assert deep_merge({"a": {"x": 1}}, {"a": 5}) == {"a": 5}


def test_lists_are_concatenated_in_order():
    assert merge_documents([[1, 2], [3], []]) == [1, 2, 3]


def test_merge_by_key_upserts_and_keeps_first_seen_order():
    a = [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Linus", "tags": ["x"]}, {"note": "no id"}]
    b = [{"id": 2, "city": "Portland", "tags": ["kernel"]}, {"id": 3, "name": "Grace"}]
    assert merge_by_key([a, b], "id") == [
        {"id": 1, "name": "Ada"},
        {"id": 2, "name": "Linus", "tags": ["kernel"], "city": "Portland"},
        {"note": "no id"},
        {"id": 3, "name": "Grace"},
    ]


def test_merge_by_nested_key():
    out = merge_by_key([[{"u": {"id": 1}, "a": 1}], [{"u": {"id": 1}, "b": 2}]], "u.id")
    assert out == [{"u": {"id": 1}, "a": 1, "b": 2}]


@pytest.mark.parametrize(
    "docs, kwargs, message",
    [([[1], {"a": 1}], {}, "different kinds"), ([{"a": 1}], {"key": "id"}, "only applies"),
     ([[1, 2]], {"key": "id"}, "every list item"), ([[{"id": [1]}]], {"key": "id"}, "scalar"), ([], {}, "nothing")],
)
def test_merge_errors(docs, kwargs, message):
    with pytest.raises(FlowError, match=message):
        merge_documents(docs, **kwargs)
