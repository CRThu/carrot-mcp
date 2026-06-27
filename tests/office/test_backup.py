"""Tests for backup system."""

import os
import shutil
import tempfile

from carrot_mcp_office.server import backup_history, backup_restore
from carrot_mcp_office.excel import create_sheet, write_range, read_range
from carrot_mcp_office.backup import list_versions


def _cleanup(original_path):
    from carrot_mcp_office.backup import _mirror_path
    mirror = _mirror_path(original_path)
    if mirror.parent.exists():
        shutil.rmtree(mirror.parent, ignore_errors=True)


def _xlsx():
    return os.path.join(tempfile.gettempdir(), "test_office.xlsx")


def test_auto_backup_creates_version():
    path = _xlsx()
    try:
        create_sheet(path, "Data")
        result = write_range(path, "Data", "A1", [["Hello"]])
        assert result["version"] >= 1
        versions = list_versions(path)
        assert len(versions) >= 1
        assert versions[-1].tool == "write_range"
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_version_returned_from_mutation():
    path = _xlsx()
    try:
        create_sheet(path, "Data")
        result = write_range(path, "Data", "A1", [["V1"]])
        assert "version" in result
        assert isinstance(result["version"], int)
        assert result["version"] >= 1
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_backup_history():
    path = _xlsx()
    try:
        create_sheet(path, "Data")
        write_range(path, "Data", "A1", [["Hello"]])
        result = backup_history(path)
        assert result["status"] == "ok"
        assert result["count"] >= 1
        assert "versions" in result
        assert len(result["versions"]) >= 1
        v = result["versions"][0]
        assert "number" in v
        assert "file" in v
        assert "tool" in v
        assert "timestamp" in v
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_backup_history_nonexistent():
    result = backup_history("nonexistent.xlsx")
    assert result["status"] == "ok"
    assert result["count"] == 0


def test_backup_restore():
    path = _xlsx()
    try:
        create_sheet(path, "Data")
        write_range(path, "Data", "A1", [["Original"]])
        versions = list_versions(path)
        write_version = versions[-1].number
        write_range(path, "Data", "A1", [["Modified"]], overwrite=True)
        result = backup_restore(path, write_version)
        assert result["status"] == "ok"
        val = read_range(path, "Data", "A1")
        assert val["value"] == "Original"
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_backup_restore_nonexistent_version():
    path = _xlsx()
    try:
        create_sheet(path, "Data")
        result = backup_restore(path, 999)
        assert result["status"] == "error"
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_version_increments():
    path = _xlsx()
    try:
        create_sheet(path, "Data")
        write_range(path, "Data", "A1", [["V1"]])
        write_range(path, "Data", "A1", [["V2"]], overwrite=True)
        versions = list_versions(path)
        assert len(versions) == 3
        assert versions[0].number == 1
        assert versions[1].number == 2
        assert versions[2].number == 3
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)

