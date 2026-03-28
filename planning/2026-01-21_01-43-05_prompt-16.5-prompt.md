
take a look at tmp/test-cases/gemini2/notes.md.  That directory has the actual
gemini internal files which should mirror the streaming content we're getting
from the gemini-cli process.

Using this, we should be able to validate/correct our json stream formatting
for gemini-cli, and provide accurate resultSummary to the auditor, etc.

Run these two commands:

- `oneshot --executor gemini "what is the capital of india?" --debug --verbose`
- `gemini --yolo --output-format stream-json "what is the capital of spain?"`

Adjust the oneshot gemini_executor to function.

Add additional debugging if it helps understand what is happening internally.

Please create a @AGENTS.md project plan to test diagnose fix.
