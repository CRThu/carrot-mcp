"""Tests for CLI entry point."""

from unittest.mock import patch, MagicMock

from carrot_mcp.cli import get_servers, main


def test_get_servers():
    servers = get_servers()
    assert isinstance(servers, dict)


@patch("carrot_mcp.cli.entry_points")
def test_get_servers_returns_dict(mock_ep):
    mock_ep.return_value = []
    result = get_servers()
    assert result == {}


@patch("carrot_mcp.cli.entry_points")
def test_get_servers_maps_names(mock_ep):
    ep1 = MagicMock()
    ep1.name = "serial"
    ep2 = MagicMock()
    ep2.name = "ds"
    mock_ep.return_value = [ep1, ep2]
    result = get_servers()
    assert "serial" in result
    assert "ds" in result
    assert result["serial"] is ep1


@patch("carrot_mcp.cli.get_servers")
@patch("builtins.print")
def test_main_list(mock_print, mock_get_servers):
    mock_get_servers.return_value = {"serial": MagicMock(), "ds": MagicMock()}
    with patch("sys.argv", ["carrot-mcp", "list"]):
        main()
    mock_print.assert_any_call("Available servers:")
    calls = [str(c) for c in mock_print.call_args_list]
    assert any("serial" in c for c in calls)
    assert any("ds" in c for c in calls)


@patch("carrot_mcp.cli.get_servers")
@patch("builtins.print")
def test_main_no_args(mock_print, mock_get_servers):
    mock_get_servers.return_value = {"serial": MagicMock()}
    with patch("sys.argv", ["carrot-mcp"]):
        main()
    calls = [str(c) for c in mock_print.call_args_list]
    assert any("Usage" in c for c in calls)
    assert any("serial" in c for c in calls)


@patch("carrot_mcp.cli.get_servers")
@patch("builtins.print")
def test_main_unknown_server(mock_print, mock_get_servers):
    mock_get_servers.return_value = {"serial": MagicMock()}
    with patch("sys.argv", ["carrot-mcp", "unknown"]):
        try:
            main()
        except SystemExit as e:
            assert e.code == 1
    calls = [str(c) for c in mock_print.call_args_list]
    assert any("Unknown" in c for c in calls)


@patch("carrot_mcp.cli.get_servers")
def test_main_runs_server(mock_get_servers):
    mock_server = MagicMock()
    mock_get_servers.return_value = {"serial": mock_server}
    with patch("sys.argv", ["carrot-mcp", "serial"]):
        main()
    mock_server.load.return_value.run.assert_called_once()
