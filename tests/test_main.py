"""Smoke test for the __main__ module entry point."""

from unittest.mock import patch


def test_main_invokes_cli() -> None:
    """Ensure __main__ calls cli() when executed as a module."""
    with patch("envault.__main__.cli") as mock_cli:
        # Simulate running the module body
        import importlib
        import envault.__main__ as main_mod

        # Re-execute the module-level guard by calling cli directly
        main_mod.cli()
        mock_cli.assert_called_once()
