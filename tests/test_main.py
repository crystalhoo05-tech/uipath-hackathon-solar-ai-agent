"""CLI tests."""

from unittest.mock import patch

from hackathon_ai_uipath.main import build_parser, main


def test_parser_accepts_host_and_port():
    parser = build_parser()
    args = parser.parse_args(["--host", "127.0.0.1", "--port", "9000"])
    assert args.host == "127.0.0.1"
    assert args.port == 9000


@patch("hackathon_ai_uipath.api.app.run")
def test_main_starts_server(mock_run):
    assert main([]) == 0
    mock_run.assert_called_once()
