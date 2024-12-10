from pathlib import Path
from typing import Optional, Tuple
from rich.console import Console
from janito.common import progress_send_message
from janito.changehistory import save_changes_to_history
from janito.config import config

from . import (
    build_change_request_prompt,
    parse_response,
    setup_workdir_preview,
    ChangeApplier
)

from .analysis import analyze_request, AnalysisOption

if __name__ == "__main__":
    config.set_debug(True)
    config.set_workdir(Path("/tmp/main_test"))
    user_request = "create an hello.py with an hello world"
    answer = analyze_request([], user_request, pre_select="A")
    _process_change_request(answer.summary, user_request, "", auto_apply=True)