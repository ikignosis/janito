"""
Tests for the --init-codesearch handler output, in particular the
"Indexing the current directory, this may take some time..." message.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from janito.cli.handlers.codesearch import handle_init_codesearch


def test_init_codesearch_prints_indexing_message(tmp_path, capsys):
    """--init-codesearch announces the indexing step before building."""
    with (
        patch(
            "janito.cli.handlers.codesearch.CodeSearch",
        ) as mock_cs_cls,
        patch(
            "janito.cli.handlers.codesearch.Path.cwd",
            return_value=tmp_path,
        ),
    ):
        mock_cs = MagicMock()
        mock_cs.stats.return_value = {"file_count": 1, "trigram_count": 3}
        mock_cs_cls.return_value.__enter__.return_value = mock_cs

        result = handle_init_codesearch(SimpleNamespace())

    assert result == 0
    captured = capsys.readouterr()
    assert "Indexing the current directory, this may take some time..." in captured.out
    assert "Code search index created at" in captured.out
