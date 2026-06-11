"""``agentiq web`` — serve the browser factory view over the run store.

Read-only over the store (phase W0): browse runs, replay any of them in the
browser. ``agentiq replay <id> --web`` deep-links straight into a run. Heavy
imports (fastapi/uvicorn) stay inside the command so the CLI starts fast.
"""

from __future__ import annotations

import argparse
import webbrowser

from agentiq.core.exit_codes import ExitCode

DEFAULT_PORT = 8642


def serve_web(
    *,
    port: int = DEFAULT_PORT,
    open_browser: bool = True,
    run_id: str | None = None,
) -> int:
    """Start the web server (blocking) and optionally open the browser."""
    import uvicorn

    from agentiq.web.server import create_app

    url = f"http://127.0.0.1:{port}/"
    if run_id is not None:
        url += f"?run={run_id}"
    if open_browser:
        webbrowser.open(url)
    print(f"AGENTIQ factory at {url}  (Ctrl+C to stop)")
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="warning")
    return ExitCode.SUCCESS


def web_command(args: argparse.Namespace) -> int:
    """``agentiq web [--port] [--no-browser]``."""
    return serve_web(port=args.port, open_browser=not args.no_browser)
