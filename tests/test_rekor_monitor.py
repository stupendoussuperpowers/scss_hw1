"""
Simple test cases for main.py
"""

import json
import os
import sys
import pytest
from jsonschema import validate
from io import StringIO
from unittest.mock import patch, MagicMock

import requests

import rekor_scss.main as main


checkpoint_schema = {
    "type": "object",
    "properties": {
        "inactiveShards": {"type": "array"},
        "rootHash": {"type": "string"},
        "signedTreeHead": {"type": "string"},
        "treeID": {"type": "string"},
        "treeSize": {"type": "integer"}
    },
    "required": ["inactiveShards", "rootHash", "signedTreeHead",
                 "treeID", "treeSize"]
}


def test_checkpoint():
    """Test that checkpoint retrieval works and returns valid JSON"""
    checkpoint = main.get_latest_checkpoint(debug=False)

    validate(instance=checkpoint, schema=checkpoint_schema)

    assert checkpoint["treeSize"] > 0, "Tree size should be positive"
    assert len(checkpoint["rootHash"]) > 0, "Root hash should not be empty"
    assert checkpoint["treeID"] != "", "Tree ID should not be empty"


def test_checkpoint_debug_mode():
    """Test checkpoint retrieval with debug flag"""
    checkpoint = main.get_latest_checkpoint(debug=True)

    validate(instance=checkpoint, schema=checkpoint_schema)
    assert checkpoint is not None
    assert "treeSize" in checkpoint


def test_get_log_entry_valid():
    """Test getting a valid log entry"""
    log_entry = main.get_log_entry(100000, debug=False)

    if log_entry is not None:
        assert "body" in log_entry
        assert "verification" in log_entry


def test_get_log_entry_negative():
    """Test that negative log index returns None"""
    result = main.get_log_entry(-1, debug=False)
    assert result is None


def test_get_log_entry_invalid_string():
    """Test that string log index returns None"""
    result = main.get_log_entry("invalid", debug=False)
    assert result is None


def test_inclusion_nonexistent_file():
    """Test inclusion with non-existent artifact file"""
    result = main.inclusion(
        123456, "/nonexistent/file.txt", debug=False)
    assert result is False


def test_inclusion_directory_not_file():
    """Test inclusion when artifact path is a directory"""
    result = main.inclusion(123456, ".", debug=False)
    assert result is False


def test_inclusion():
    """Test inclusion"""
    result = main.inclusion(540283374, "artifact.md", debug=False)

    assert result is True


def test_consistency_validation():
    """Test consistency check with previous checkpoint"""
    current = main.get_latest_checkpoint(debug=False)

    prev_checkpoint = {
        "treeID": current["treeID"],
        "treeSize": max(1, current["treeSize"] - 1000),  # Smaller tree
        "rootHash": current["rootHash"]
    }

    main.consistency(prev_checkpoint, debug=False)


def test_checkpoint_returns_valid_structure():
    """Test that checkpoint output has expected structure"""
    checkpoint = main.get_latest_checkpoint(debug=False)

    assert "treeID" in checkpoint
    assert "treeSize" in checkpoint
    assert "rootHash" in checkpoint
    assert "inactiveShards" in checkpoint


def test_checkpoint_tree_size_is_positive():
    """Test that checkpoint tree size is a positive integer"""
    checkpoint = main.get_latest_checkpoint(debug=False)

    tree_size = checkpoint["treeSize"]
    assert isinstance(tree_size, int), "Tree size should be an integer"
    assert tree_size > 0, "Tree size should be positive"


def test_rekor_request_timeout():
    """Test that rekor_request handles timeout errors"""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = TimeoutError("Request timed out")

        result = main.rekor_request("/api/v1/test")

        assert result is None


def test_rekor_request_http_error():
    """Test that rekor_request handles HTTP errors"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "404 Not Found")
        mock_get.return_value = mock_response

        result = main.rekor_request("/api/v1/invalid")

        assert result is None


def test_main_function():
    """Test main function with checkpoint flag"""
    test_args = ['main.py', '--checkpoint']

    with patch('sys.argv', test_args):
        main.main()


def test_consistency_missing_args(monkeypatch, capsys):
    """Tests that missing consistency args print helpful messages."""
    with patch("sys.argv", ["main.py", "--consistency"]):
        main.main()
        out = capsys.readouterr().out
        assert "please specify tree id for prev checkpoint" in out


def test_consistency_with_all_args(monkeypatch):
    """Tests full consistency path when all args are provided."""
    with patch.object(main, "consistency") as mock_consistency:
        args = [
            "--consistency",
            "--tree-id", "123",
            "--tree-size", "10",
            "--root-hash", "abc123"
        ]
        monkeypatch.setattr(sys, "argv", ["main.py"] + args)
        main.main()
        mock_consistency.assert_called_once()
        call_arg = mock_consistency.call_args[0][0]
        assert call_arg["treeID"] == "123"
        assert call_arg["treeSize"] == 10
        assert call_arg["rootHash"] == "abc123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
