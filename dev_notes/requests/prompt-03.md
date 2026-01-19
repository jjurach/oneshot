
- rename the "session log" to start with "oneshot", e.g. 2026-01-17_21-55-00_oneshot.json

- store more information in this log, including the original prompt text, executor model, working directory
  - either identify/copy or incorporate all the information from the agent
    session log -- all of the agent's reasoning and tool interactions, etc.
    - try to keep it all in the same single file, but feel free to organize some of that information into a parallel markdown file, e.g. 2026-01-17_21-55-00_oneshot-data.md or whatever representation
    - for examples:
      - from cline, `cline task list; cline task open $task_id; cline task view --output-format json`
      - alternatively from cline, `$HOME/.cline/data/tasks/$task_id/api_conversation_history.json`
      - claude, aider etc. must each have state files or cli features to dump session history, etc.  research with google search how to do this with our individual executors
  
- add support for the "gemini" executor to allow worker execution to occur through gemini-cli with appropriate permission-bypass and non-interactive arguments.

- consider all documentation in README.md and docs/.  For any documentation which describes features of oneshot, and lists capabilities etc. Ensure that all of the supported executors are listed, including "direct".

- add demo script to execute oneshot using command-line arguments to trigger "direct" executor usage with the ollama model described in /.env of this project.  Demonstrate with "What is the capital of Norway?" that the direct executor running with the llama-pro model can participate in this one-shot flow.

  - there are aspirations to use lang-chain/lang-graph in the direct executor
    implementation in order to provide basic context augmentation and tooling.

    - if that is in place, now is a good time to include checklist tasks to work
      through testing that logic.

    - if none of that is in place, create docs/direct-executor.md with a
      detailed design of how these technologies will work together to form an
      extensible platform for tooling and context management.  a user will review
      this design and use it in future project planning.

- create a docs/overview.md which describes all other documentation committed to this project.
  - add description of the kinds of documentation accumulating in `dev_notes/`


- allow the logs directory to be specified in command-line or configuration
  file. For example, i want it to be easy for oneshot logs to accumulate in `dev_notes/oneshot/oneshot-*`
  -  add oneshot logs to .gitignore just in case they are massive.

- before considering this change complete, execute pytest and demo scripts, and consult server log. if there are any crashes, diagnose and fix. keep iterating on pytest and demo scripts until all is working.

- when all tests and scripts are working commit your work
