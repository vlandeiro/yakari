import pytest
from collections import deque
from yakari.types import MenuArguments, History, SuggestionsList, SuggestionsCommand
from unittest.mock import patch


def test_history_init():
    """Test History initialization with default values."""
    history = History()
    assert isinstance(history.values, deque)
    assert len(history.values) == 0
    assert history._cur_pos is None


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
    assert history._cur_pos is None


def test_restart_with_values():
    """Test restart with existing values."""
    history = History(values=deque(["test"]))
    history.restart()
    assert history._cur_pos == -1


def test_current_no_position():
    """Test current value when no position is set."""
    history = History(values=deque(["test"]))
    assert history.current is None


def test_current_with_position():
    """Test current value with valid position."""
    history = History(values=deque(["test"]))
    history._cur_pos = 0
    assert history.current == "test"


def test_prev_no_position():
    """Test prev value when no position is set."""
    history = History(values=deque(["test"]))
    assert history.prev == "test"


def test_prev_wrap_around():
    """Test prev value wraps to start when at end."""
    history = History(values=deque(["test1", "test2"]))
    history._cur_pos = 1
    assert history.prev == "test1"
    assert history._cur_pos == 0


def test_prev_normal_case():
    """Test prev value in normal case."""
    history = History(values=deque(["test1", "test2"]))
    history._cur_pos = 0
    assert history.prev == "test2"
    assert history._cur_pos == 1


def test_next_no_position():
    """Test next value when no position is set."""
    history = History(values=deque(["test"]))
    assert history.next == "test"


def test_next_wrap_around():
    """Test next value wraps to end when at start."""
    history = History(values=deque(["test1", "test2"]))
    history._cur_pos = 0
    assert history.next == "test2"
    assert history._cur_pos == 1


def test_next_normal_case():
    """Test next value in normal case."""
    history = History(values=deque(["test1", "test2"]))
    history._cur_pos = 1
    assert history.next == "test1"
    assert history._cur_pos == 0


def test_suggestion_list():
    sl = SuggestionsList(values=["item1", "item2"])
    assert sl.values == ["item1", "item2"]


class TestSuggestionsCommand:
    @pytest.fixture
    def command_instance(self):
        return SuggestionsCommand(command="echo test")

    @patch("subprocess.run")
    def test_suggestions_with_caching(self, mock_run, command_instance):
        command_instance.cache = True
        mock_run.return_value.stdout = b"line1\nline2\n"
        mock_run.return_value.stderr = b""

        # First call should trigger subprocess
        assert command_instance.values == ["line1", "line2"]
        mock_run.assert_called_once()

        # Second call should use cached value
        assert command_instance.values == ["line1", "line2"]
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_suggestions_without_caching(self, mock_run, command_instance):
        mock_run.return_value.stdout = b"line1\nline2\n"
        mock_run.return_value.stderr = b""
        command_instance.cache = False

        # Each call should trigger subprocess
        assert command_instance.values == ["line1", "line2"]
        assert command_instance.values == ["line1", "line2"]
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_suggestions_with_error(self, mock_run, command_instance):
        mock_run.return_value.stderr = b"error message"

        with pytest.raises(RuntimeError) as exc_info:
            _ = command_instance.values
        assert "failed with the following message" in str(exc_info.value)
