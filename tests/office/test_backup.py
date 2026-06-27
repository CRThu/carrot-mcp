"""Tests for backup system."""

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from carrot_mcp_office.server import backup_history, backup_restore
from carrot_mcp_office.excel import create_sheet, write_range, read_range
from carrot_mcp_office import backup as backup_mod
from carrot_mcp_office.backup import (
    list_versions,
    save_version,
    backup_root,
    _mirror_path,
    _versions_json_path,
    _load_versions,
    _save_versions,
    _prune_versions,
    VersionEntry,
    VersionsMeta,
)


def _cleanup(original_path):
    mirror = _mirror_path(original_path)
    if mirror.parent.exists():
        shutil.rmtree(mirror.parent, ignore_errors=True)
    d = os.path.dirname(original_path)
    if os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)


def _xlsx():
    d = tempfile.mkdtemp(prefix="test_office_")
    return os.path.join(d, "test.xlsx")


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


def test_backup_root_creates_directory():
    root = backup_root()
    assert root.exists()
    assert root.is_dir()
    assert root.name == "office"
    assert root.parent.name == "carrot-mcp"


def test_backup_root_override():
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"CARROT_MCP_BACKUP_ROOT": tmpdir}):
            root = backup_root()
            assert root == Path(tmpdir)
            assert root.exists()


def test_mirror_path_structure():
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"CARROT_MCP_BACKUP_ROOT": tmpdir}):
            mirror = _mirror_path("D:\\docs\\reports\\file.xlsx")
            assert mirror.parts[-1] == "file"
            assert "docs" in str(mirror)
            assert "reports" in str(mirror)


def test_mirror_path_single_part():
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"CARROT_MCP_BACKUP_ROOT": tmpdir}):
            mirror = _mirror_path("C:\\file.xlsx")
            assert mirror.parts[-1] == "file"


def test_mirror_path_unc_path():
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"CARROT_MCP_BACKUP_ROOT": tmpdir}):
            mirror = _mirror_path("\\\\server\\share\\file.xlsx")
            assert mirror.parts[-1] == "file"


def test_last_modified_timestamp():
    path = _xlsx()
    try:
        create_sheet(path, "Data")
        write_range(path, "Data", "A1", [["Test"]])
        root = backup_root()
        ts_file = root / "_last_modified.txt"
        assert ts_file.exists()
        ts_text = ts_file.read_text(encoding="utf-8").strip()
        dt = datetime.fromisoformat(ts_text)
        assert dt.tzinfo is not None
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_versions_json_created():
    path = _xlsx()
    try:
        create_sheet(path, "Data")
        write_range(path, "Data", "A1", [["Test"]])
        jp = _versions_json_path(path)
        assert jp.exists()
        data = json.loads(jp.read_text(encoding="utf-8"))
        assert "versions" in data
        assert "max_versions" in data
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_version_entry_fields():
    path = _xlsx()
    try:
        create_sheet(path, "Data")
        write_range(path, "Data", "A1", [["Test"]])
        versions = list_versions(path)
        assert len(versions) >= 1
        v = versions[-1]
        assert v.number >= 1
        assert v.file.endswith(".xlsx")
        assert v.tool == "write_range"
        assert v.timestamp is not None
        assert v.original_size > 0
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_backup_file_on_disk():
    path = _xlsx()
    try:
        create_sheet(path, "Data")
        write_range(path, "Data", "A1", [["Test"]])
        versions = list_versions(path)
        mirror = _mirror_path(path)
        backup_file = mirror / versions[-1].file
        assert backup_file.exists()
        assert backup_file.stat().st_size > 0
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_prune_by_max_versions():
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"CARROT_MCP_BACKUP_ROOT": tmpdir}):
            with patch.object(backup_mod, "MAX_VERSIONS", 3):
                path = os.path.join(tmpdir, "test.xlsx")
                create_sheet(path, "Data")
                for i in range(5):
                    write_range(path, "Data", "A1", [[f"V{i}"]], overwrite=True)
                versions = list_versions(path)
                assert len(versions) == 3
                assert versions[-1].number == 6
                mirror = _mirror_path(path)
                for v in versions:
                    assert (mirror / v.file).exists()


def test_prune_by_max_age_days():
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"CARROT_MCP_BACKUP_ROOT": tmpdir}):
            with patch.object(backup_mod, "MAX_AGE_DAYS", 1):
                path = os.path.join(tmpdir, "test.xlsx")
                create_sheet(path, "Data")
                write_range(path, "Data", "A1", [["V1"]])
                versions_before = list_versions(path)
                assert len(versions_before) == 2
                jp = _versions_json_path(path)
                data = json.loads(jp.read_text(encoding="utf-8"))
                for entry in data["versions"]:
                    entry["timestamp"] = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
                jp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                write_range(path, "Data", "A1", [["V2"]], overwrite=True)
                versions = list_versions(path)
                assert len(versions) == 1
                assert versions[0].number == 3


def test_prune_keeps_recent_within_limit():
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"CARROT_MCP_BACKUP_ROOT": tmpdir}):
            with patch.object(backup_mod, "MAX_VERSIONS", 5):
                path = os.path.join(tmpdir, "test.xlsx")
                create_sheet(path, "Data")
                for i in range(3):
                    write_range(path, "Data", "A1", [[f"V{i}"]], overwrite=True)
                versions = list_versions(path)
                assert len(versions) == 4
                assert versions[0].number == 3
                assert versions[1].number == 4
                assert versions[2].number == 5
                mirror = _mirror_path(path)
                for v in versions:
                    assert (mirror / v.file).exists()


def test_prune_by_max_age_days():
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"CARROT_MCP_BACKUP_ROOT": tmpdir}):
            with patch.object(backup_mod, "MAX_AGE_DAYS", 1):
                path = os.path.join(tmpdir, "test.xlsx")
                create_sheet(path, "Data")
                write_range(path, "Data", "A1", [["V1"]])
                versions_before = list_versions(path)
                assert len(versions_before) == 2
                jp = _versions_json_path(path)
                data = json.loads(jp.read_text(encoding="utf-8"))
                for entry in data["versions"]:
                    entry["timestamp"] = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
                jp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                write_range(path, "Data", "A1", [["V2"]], overwrite=True)
                versions = list_versions(path)
                assert len(versions) == 1
                assert versions[0].number == 3


def test_prune_keeps_recent_within_limit():
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"CARROT_MCP_BACKUP_ROOT": tmpdir}):
            with patch.object(backup_mod, "MAX_VERSIONS", 5):
                path = os.path.join(tmpdir, "test.xlsx")
                create_sheet(path, "Data")
                for i in range(3):
                    write_range(path, "Data", "A1", [[f"V{i}"]], overwrite=True)
                versions = list_versions(path)
                assert len(versions) == 4


def test_prune_old_files_deleted_from_disk():
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"CARROT_MCP_BACKUP_ROOT": tmpdir}):
            with patch.object(backup_mod, "MAX_VERSIONS", 2):
                path = os.path.join(tmpdir, "test.xlsx")
                create_sheet(path, "Data")
                write_range(path, "Data", "A1", [["V1"]])
                write_range(path, "Data", "A1", [["V2"]], overwrite=True)
                write_range(path, "Data", "A1", [["V3"]], overwrite=True)
                versions = list_versions(path)
                mirror = _mirror_path(path)
                remaining_files = [v.file for v in versions]
                all_expected = [f"test_v{i:03d}.xlsx" for i in range(1, 4)]
                deleted = [f for f in all_expected if f not in remaining_files]
                for f in deleted:
                    assert not (mirror / f).exists(), f"Deleted file {f} should not exist on disk"
                for v in versions:
                    assert (mirror / v.file).exists()


def test_prune_age_and_count_combined():
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"CARROT_MCP_BACKUP_ROOT": tmpdir}):
            with patch.object(backup_mod, "MAX_VERSIONS", 2), \
                 patch.object(backup_mod, "MAX_AGE_DAYS", 1):
                path = os.path.join(tmpdir, "test.xlsx")
                create_sheet(path, "Data")
                write_range(path, "Data", "A1", [["V1"]])
                jp = _versions_json_path(path)
                data = json.loads(jp.read_text(encoding="utf-8"))
                for entry in data["versions"]:
                    entry["timestamp"] = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
                jp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                write_range(path, "Data", "A1", [["V2"]], overwrite=True)
                write_range(path, "Data", "A1", [["V3"]], overwrite=True)
                versions = list_versions(path)
                assert len(versions) == 2
                assert versions[0].number == 3
                assert versions[1].number == 4


def test_save_version_nonexistent_file():
    result = save_version("/nonexistent/path/file.xlsx", "test_tool")
    assert result is None


def test_load_versions_corrupt_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"CARROT_MCP_BACKUP_ROOT": tmpdir}):
            path = os.path.join(tmpdir, "test.xlsx")
            jp = _versions_json_path(path)
            jp.parent.mkdir(parents=True, exist_ok=True)
            jp.write_text("not valid json {{{", encoding="utf-8")
            meta = _load_versions(path)
            assert len(meta.versions) == 0


def test_prune_versions_empty():
    meta = VersionsMeta(versions=[])
    to_delete = _prune_versions(meta)
    assert len(to_delete) == 0

