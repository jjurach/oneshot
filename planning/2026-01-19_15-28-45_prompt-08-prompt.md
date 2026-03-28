create @AGENTS.md project plan introduce `--executor gemini` to execute oneshot tasks within Gemini CLI.

This is set up and working right now:
```
$ echo "what is the capital of columbia?" | gemini --output-format stream-json --approval-mode yolo
YOLO mode is enabled. All tool calls will be automatically approved.
Loaded cached credentials.
Server 'context7' supports tool updates. Listening for changes...
{"type":"init","timestamp":"2026-01-19T21:26:44.030Z","session_id":"b35ecd66-4ed8-43cd-b73b-9dd2eb9b2f4e","model":"auto-gemini-2.5"}
{"type":"message","timestamp":"2026-01-19T21:26:44.031Z","role":"user","content":"what is the capital of columbia?\n"}
{"type":"tool_use","timestamp":"2026-01-19T21:26:48.072Z","tool_name":"google_web_search","tool_id":"google_web_search-1768858008072-7d88fcce98a3b","parameters":{"query":"capital of columbia"}}
{"type":"tool_result","timestamp":"2026-01-19T21:26:49.890Z","tool_id":"google_web_search-1768858008072-7d88fcce98a3b","status":"success","output":"Search results for \"capital of columbia\" returned."}
{"type":"message","timestamp":"2026-01-19T21:26:50.796Z","role":"assistant","content":"Bogotá is the capital and","delta":true}
{"type":"message","timestamp":"2026-01-19T21:26:50.825Z","role":"assistant","content":" largest city of Colombia.","delta":true}
{"type":"result","timestamp":"2026-01-19T21:26:50.854Z","status":"success","stats":{"total_tokens":32735,"input_tokens":32282,"output_tokens":76,"cached":13673,"input":18609,"duration_ms":6824,"tool_calls":1}}
```

Create a project plan which includes pytests and copying or extending a demo script.

Create the plan now. do not implement
