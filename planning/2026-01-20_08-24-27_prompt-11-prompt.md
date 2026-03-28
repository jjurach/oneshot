
Implement an Executor virtual class, and migrate all existing functionality for
cline, claude, and gemini into respective base classes of this subclass which
represent what agent is executing for a given step.

Provide detailed checklist of instructions for each individual executor.
Instruct the agent to update each checklist item when completed so as not to
lose track of where they are in this process.

In other words, consider cline for example:
- The ClineExecutor class (or similar) should:

  - have a method which chooses the command to execute
    - different executors have different commands

  - have a method which interprets each parsed activity chunk into a summary to
    output to stdout, and details to append to what is passed to the auditor
    - different executors emit different streaming activity

  - all reference to cline should be isolated to this executor class.
    - whenever some behavior of cline is exposed within oneshot, we need to figure out how to represent that in this executor class.

- Repeat all this work for "claude" executor (claude code)

- Repeat all this work for "gemini" executor (gemini-cli)

- Repeat all this work for "aider" executor (Aider)

- Repeat all this work for "direct" executor (openai)

- Write pytests which test:
  - the streaming activity parser
  - command construction
  - across all executor subclasses

- Write a demo script which applies a simple demonstration to an individual working executor.
  - include checklist items
  - include feature to demo script which executes demo script across all executors.

- Add instruction at the end to repeat all tests for all executors to ensure no regressions.

Create this project plan now.  do not implement.
