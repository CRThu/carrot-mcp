"""Tests for agent config modules."""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestClaudeConfig:
    @patch("carrot_mcp.claude.shutil")
    @patch("carrot_mcp.claude.CONFIG")
    @patch("carrot_mcp.claude.BACKUP_DIR")
    def test_add_new_server(self, mock_backup_dir, mock_config, mock_shutil):
        mock_config.exists.return_value = True
        mock_config.read_text.return_value = json.dumps({"mcpServers": {}})
        mock_backup_dir.__truediv__ = lambda self, x: Path("/tmp/test")

        from carrot_mcp.claude import add
        add("pdf")

        mock_config.write_text.assert_called_once()
        written = json.loads(mock_config.write_text.call_args[0][0])
        assert "carrot-pdf" in written["mcpServers"]
        assert written["mcpServers"]["carrot-pdf"]["command"] == "uvx"
        assert written["mcpServers"]["carrot-pdf"]["args"] == ["carrot-mcp-pdf@latest"]

    @patch("carrot_mcp.claude.shutil")
    @patch("carrot_mcp.claude.CONFIG")
    def test_add_preserves_env(self, mock_config, mock_shutil):
        mock_config.exists.return_value = True
        existing = {"mcpServers": {"carrot-pdf": {"env": {"API_KEY": "abc123"}}}}
        mock_config.read_text.return_value = json.dumps(existing)

        from carrot_mcp.claude import add
        add("pdf", env={"API_KEY": "abc123"})

        written = json.loads(mock_config.write_text.call_args[0][0])
        assert written["mcpServers"]["carrot-pdf"]["env"]["API_KEY"] == "abc123"

    @patch("carrot_mcp.claude.shutil")
    @patch("carrot_mcp.claude.CONFIG")
    def test_remove_server(self, mock_config, mock_shutil):
        mock_config.exists.return_value = True
        existing = {"mcpServers": {"carrot-pdf": {"command": "uvx"}}}
        mock_config.read_text.return_value = json.dumps(existing)

        from carrot_mcp.claude import remove
        remove("pdf")

        written = json.loads(mock_config.write_text.call_args[0][0])
        assert "carrot-pdf" not in written["mcpServers"]

    @patch("carrot_mcp.claude._load")
    def test_list_carrot(self, mock_load):
        mock_load.return_value = {
            "mcpServers": {
                "carrot-pdf": {"command": "uvx"},
                "other-server": {"command": "uvx"},
            }
        }

        from carrot_mcp.claude import list_carrot
        result = list_carrot()
        assert "carrot-pdf" in result
        assert "other-server" not in result

    def test_get_env(self):
        from carrot_mcp.claude import get_env
        assert get_env({"env": {"KEY": "val"}}) == {"KEY": "val"}
        assert get_env({}) is None


class TestMiMoCodeConfig:
    @patch("carrot_mcp.mimocode.shutil")
    @patch("carrot_mcp.mimocode.CONFIG")
    def test_add_new_server(self, mock_config, mock_shutil):
        mock_config.exists.return_value = True
        mock_config.parent.exists.return_value = True
        mock_config.read_text.return_value = json.dumps({"mcp": {}})

        from carrot_mcp.mimocode import add
        add("pdf")

        mock_config.write_text.assert_called_once()
        written = json.loads(mock_config.write_text.call_args[0][0])
        assert "carrot-pdf" in written["mcp"]
        assert written["mcp"]["carrot-pdf"]["command"] == ["uvx", "carrot-mcp-pdf@latest"]

    @patch("carrot_mcp.mimocode.shutil")
    @patch("carrot_mcp.mimocode.CONFIG")
    def test_add_preserves_env(self, mock_config, mock_shutil):
        mock_config.exists.return_value = True
        mock_config.parent.exists.return_value = True
        existing = {"mcp": {"carrot-pdf": {"environment": {"API_KEY": "abc123"}}}}
        mock_config.read_text.return_value = json.dumps(existing)

        from carrot_mcp.mimocode import add
        add("pdf", env={"API_KEY": "abc123"})

        written = json.loads(mock_config.write_text.call_args[0][0])
        assert written["mcp"]["carrot-pdf"]["environment"]["API_KEY"] == "abc123"

    @patch("carrot_mcp.mimocode.shutil")
    @patch("carrot_mcp.mimocode.CONFIG")
    def test_remove_server(self, mock_config, mock_shutil):
        mock_config.exists.return_value = True
        existing = {"mcp": {"carrot-pdf": {"command": ["uvx"]}}}
        mock_config.read_text.return_value = json.dumps(existing)

        from carrot_mcp.mimocode import remove
        remove("pdf")

        written = json.loads(mock_config.write_text.call_args[0][0])
        assert "carrot-pdf" not in written["mcp"]

    @patch("carrot_mcp.mimocode._load")
    def test_list_carrot(self, mock_load):
        mock_load.return_value = {
            "mcp": {
                "carrot-pdf": {"command": ["uvx"]},
                "other-server": {"command": ["uvx"]},
            }
        }

        from carrot_mcp.mimocode import list_carrot
        result = list_carrot()
        assert "carrot-pdf" in result
        assert "other-server" not in result

    def test_get_env(self):
        from carrot_mcp.mimocode import get_env
        assert get_env({"environment": {"KEY": "val"}}) == {"KEY": "val"}
        assert get_env({}) is None

    @patch("carrot_mcp.mimocode.CONFIG")
    def test_strip_comments(self, mock_config):
        mock_config.exists.return_value = True
        content = '{"mcp": {}}\n// this is a comment'
        mock_config.read_text.return_value = content

        from carrot_mcp.mimocode import _load
        result = _load()
        assert result == {"mcp": {}}


class TestOpenCodeConfig:
    @patch("carrot_mcp.opencode.shutil")
    @patch("carrot_mcp.opencode.CONFIG")
    def test_add_new_server(self, mock_config, mock_shutil):
        mock_config.exists.return_value = True
        mock_config.parent.exists.return_value = True
        mock_config.read_text.return_value = json.dumps({"mcp": {}})

        from carrot_mcp.opencode import add
        add("pdf")

        mock_config.write_text.assert_called_once()
        written = json.loads(mock_config.write_text.call_args[0][0])
        assert "carrot-pdf" in written["mcp"]
        assert written["mcp"]["carrot-pdf"]["command"] == ["uvx", "carrot-mcp-pdf@latest"]

    @patch("carrot_mcp.opencode.shutil")
    @patch("carrot_mcp.opencode.CONFIG")
    def test_add_preserves_env(self, mock_config, mock_shutil):
        mock_config.exists.return_value = True
        mock_config.parent.exists.return_value = True
        existing = {"mcp": {"carrot-pdf": {"environment": {"API_KEY": "abc123"}}}}
        mock_config.read_text.return_value = json.dumps(existing)

        from carrot_mcp.opencode import add
        add("pdf", env={"API_KEY": "abc123"})

        written = json.loads(mock_config.write_text.call_args[0][0])
        assert written["mcp"]["carrot-pdf"]["environment"]["API_KEY"] == "abc123"

    @patch("carrot_mcp.opencode.shutil")
    @patch("carrot_mcp.opencode.CONFIG")
    def test_remove_server(self, mock_config, mock_shutil):
        mock_config.exists.return_value = True
        existing = {"mcp": {"carrot-pdf": {"command": ["uvx"]}}}
        mock_config.read_text.return_value = json.dumps(existing)

        from carrot_mcp.opencode import remove
        remove("pdf")

        written = json.loads(mock_config.write_text.call_args[0][0])
        assert "carrot-pdf" not in written["mcp"]

    @patch("carrot_mcp.opencode._load")
    def test_list_carrot(self, mock_load):
        mock_load.return_value = {
            "mcp": {
                "carrot-pdf": {"command": ["uvx"]},
                "other-server": {"command": ["uvx"]},
            }
        }

        from carrot_mcp.opencode import list_carrot
        result = list_carrot()
        assert "carrot-pdf" in result
        assert "other-server" not in result

    def test_get_env(self):
        from carrot_mcp.opencode import get_env
        assert get_env({"environment": {"KEY": "val"}}) == {"KEY": "val"}
        assert get_env({}) is None

    @patch("carrot_mcp.opencode.CONFIG")
    def test_strip_comments(self, mock_config):
        mock_config.exists.return_value = True
        content = '{"mcp": {}}\n// this is a comment'
        mock_config.read_text.return_value = content

        from carrot_mcp.opencode import _load
        result = _load()
        assert result == {"mcp": {}}

    @patch("carrot_mcp.opencode.CONFIG")
    def test_ensure_creates_with_schema(self, mock_config):
        mock_config.exists.return_value = False
        mock_config.parent.exists.return_value = True

        from carrot_mcp.opencode import _ensure
        _ensure()

        mock_config.write_text.assert_called_once()
        written = json.loads(mock_config.write_text.call_args[0][0])
        assert written["$schema"] == "https://opencode.ai/config.json"
