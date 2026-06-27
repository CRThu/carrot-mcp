"""Shared fixtures for Office MCP tests."""

import os
import shutil
import tempfile

import pytest


@pytest.fixture
def xlsx_path():
    path = os.path.join(tempfile.gettempdir(), "test_office.xlsx")
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def docx_path():
    path = os.path.join(tempfile.gettempdir(), "test_office.docx")
    yield path
    if os.path.exists(path):
        os.unlink(path)


def cleanup_backup(original_path):
    """Remove backup directory for a test file."""
    from carrot_mcp_office.backup import _mirror_path
    mirror = _mirror_path(original_path)
    if mirror.parent.exists():
        shutil.rmtree(mirror.parent, ignore_errors=True)
