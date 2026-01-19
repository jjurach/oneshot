
When doing "claude --resume" or "cline task list", the sessions oneshot are creating are very ugly.

I want to optimize the worker and auditor prompt text in two ways:

- customizable from command-line or configuration file

- the prompt text given to the agent has a short summary on its first line followed by blank line, before the system prompt text is inserted.  i expect having the first words be something like "oneshot execution in chatterbox project" or similar.

