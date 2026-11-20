# Browser testing on codex-dev

Use the `playwright` MCP tools for real browser checks. Chromium runs headlessly
on this VM; navigation, clicks, typing, screenshots, console and network inspection
are available. Each MCP session has an isolated profile; log in with the preview's
documented test account when needed.

For Branchline, load `/workspace/config/shell.env`, then use `branchline status`
to find the ready preview URL and source revision. `branchline preview <node-id>`
requests a build when needed; wait for ready before testing. Use the project's
verification instructions for user journeys and fixture credentials. Keep the
scoped Branchline token in its file.

Capture the tested URL/revision, observed behavior and browser errors. Screenshots
without an explicit filename go to a private session directory under
`/workspace/browser-artifacts`; explicit filenames are relative to the current
workspace. Close the browser when done. The server starts with each new Codex
session; an already open session may need restarting after installation.

Unattended `codex exec` needs `--approve-for-me` for authorized browser actions
that require review. This retains sandboxing and uses automatic approval review;
the default noninteractive policy rejects those calls.
