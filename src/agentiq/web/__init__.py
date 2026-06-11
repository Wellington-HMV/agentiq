"""AGENTIQ web surface — the animated factory view (browser, PixiJS).

A pure consumer of the event store, like the TUI: it renders runs, never
orchestrates (NFR17). Replay is fully client-side (the server hands the whole
event log to the browser; a JS reducer mirror folds it), so seeking is instant.
"""
