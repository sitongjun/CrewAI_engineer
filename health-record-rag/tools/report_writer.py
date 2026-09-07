"""Configuration for CrewAI's official FileWriterTool.

The official tool owns all path validation, directory creation and UTF-8 file
writing. This module only limits writes to the current project directory.
"""

from pathlib import Path

from crewai_tools import FileWriterTool


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_report_writer_tool() -> FileWriterTool:
    """Return a sandboxed official FileWriterTool instance."""
    return FileWriterTool(
        base_dir=str(PROJECT_ROOT),
        encoding="utf-8",
    )
