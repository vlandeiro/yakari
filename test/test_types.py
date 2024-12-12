import pytest
from yakari.types import SuggestionsList, SuggestionsCommand
from unittest.mock import patch


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
