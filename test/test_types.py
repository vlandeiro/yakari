import pytest
from collections import deque
from yakari.types import Deferred, History


def test_deferred_init():
    """Test Deferred initialization with varname."""
    deferred = Deferred(varname="test_var")
    assert deferred.varname == "test_var"


def test_evaluate_custom_context():
    """Test evaluating with context dictionary."""
    context = {"test_var": "context_value"}
    deferred = Deferred(varname="test_var")
    assert deferred.evaluate(context) == "context_value"


def test_evaluate_missing_var():
    """Test evaluating a non-existent variable raises KeyError."""
    deferred = Deferred(varname="nonexistent_var")
    with pytest.raises(KeyError):
        deferred.evaluate({"foo": "bar"})


def test_evaluate_empty_context():
    """Test evaluating with empty context dictionary raises KeyError."""
    deferred = Deferred(varname="test_var")
    with pytest.raises(KeyError):
        deferred.evaluate({})


def test_evaluate_nested_context():
    """Test evaluating with nested context dictionaries."""
    outer_context = {"inner": {"test_var": "nested_value"}}
    deferred = Deferred(varname="inner")
    assert deferred.evaluate(outer_context) == {"test_var": "nested_value"}


def test_history_init():
    """Test History initialization with default values."""
    history = History()
    assert isinstance(history.values, deque)
    assert len(history.values) == 0
    assert history.cur_pos is None


def test_add_empty_value():
    """Test adding empty string does not modify history."""
    history = History()
    history.add("")
    assert len(history.values) == 0


def test_add_first_value():
    """Test adding first value to empty history."""
    history = History()
    history.add("test")
    assert len(history.values) == 1
    assert history.values[0] == "test"


def test_add_duplicate_value():
    """Test adding duplicate value is ignored."""
    history = History()
    history.add("test")
    history.add("test")
    assert len(history.values) == 1


def test_add_multiple_values():
    """Test adding multiple unique values."""
    history = History()
    history.add("test1")
    history.add("test2")
    assert len(history.values) == 2
    assert list(history.values) == ["test2", "test1"]


def test_restart_empty():
    """Test restart with empty history."""
    history = History()
    history.restart()
    assert history.cur_pos is None


def test_restart_with_values():
    """Test restart with existing values."""
    history = History(values=deque(["test"]))
    history.restart()
    assert history.cur_pos == -1


def test_current_no_position():
    """Test current value when no position is set."""
    history = History(values=deque(["test"]))
    assert history.current is None


def test_current_with_position():
    """Test current value with valid position."""
    history = History(values=deque(["test"]))
    history.cur_pos = 0
    assert history.current == "test"


def test_prev_no_position():
    """Test prev value when no position is set."""
    history = History(values=deque(["test"]))
    assert history.prev is None


def test_prev_wrap_around():
    """Test prev value wraps to start when at end."""
    history = History(values=deque(["test1", "test2"]))
    history.cur_pos = 1
    assert history.prev == "test1"
    assert history.cur_pos == 0


def test_prev_normal_case():
    """Test prev value in normal case."""
    history = History(values=deque(["test1", "test2"]))
    history.cur_pos = 0
    assert history.prev == "test2"
    assert history.cur_pos == 1


def test_next_no_position():
    """Test next value when no position is set."""
    history = History(values=deque(["test"]))
    assert history.next is None


def test_next_wrap_around():
    """Test next value wraps to end when at start."""
    history = History(values=deque(["test1", "test2"]))
    history.cur_pos = 0
    assert history.next == "test2"
    assert history.cur_pos == 1


def test_next_normal_case():
    """Test next value in normal case."""
    history = History(values=deque(["test1", "test2"]))
    history.cur_pos = 1
    assert history.next == "test1"
    assert history.cur_pos == 0