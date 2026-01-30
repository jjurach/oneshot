
Fix this problem:
```
$ oneshot "implement dev_notes/project_plans/2026-01-19_22-10-30_gemini_executor_implementation.md" --verbose --debug
Warning: Configuration file error: Invalid configuration in .oneshot.json: Invalid type for 'worker_prompt_header': expected <class 'str'>, got <class 'NoneType'>
Using default settings.
```


Also, this attempt failed with a timeout as describ
```
$ Warning: Configuration file error: Invalid configuration in .oneshot.json: Invalid type for 'worker_prompt_header': expected <class 'str'>, got <class 'NoneType'>
Using default settings.
[INFO] Starting oneshot with worker provider: executor, auditor provider: executor
[INFO] Creating new session: 2026-01-19_16-46-01_oneshot.json

--- 🤖 Worker: Iteration 1 ---
[INFO] Iteration 1/5
[INFO] Initial timeout (300s) exceeded, checking for activity...
^C^CTraceback (most recent call last):
  File "/home/phaedrus/AiSpace/oneshot/src/oneshot/oneshot.py", line 949, in call_executor
    result = subprocess.run(
             ^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/subprocess.py", line 550, in run
    stdout, stderr = process.communicate(input, timeout=timeout)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/subprocess.py", line 1209, in communicate
    stdout, stderr = self._communicate(input, endtime, timeout)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/subprocess.py", line 2116, in _communicate
    self._check_timeout(endtime, orig_timeout, stdout, stderr)
  File "/usr/lib/python3.12/subprocess.py", line 1253, in _check_timeout
    raise TimeoutExpired(
^C
```

check these files:
- 2026-01-19_16-56-45_oneshot.json
- session_20260119_165647.md
- ~/.cline/data/tasks/1768862765092/api_conversation_history.json

This last file contains "The task is complete! Let me provide a final summary of what was implemented." here:
```
jq .[] -c ~/.cline/data/tasks/1768862765092/api_conversation_history.json | tail -1 | jq . | head -c3000
```

In this case, it looks like the cline executor itself continued executing and completed the task to some extent, but the streaming events or something else made something stuck in the system, and oneshot did not reliably see this task to completion.

Focusing on the cline executor alone, please create a checklist of tasks to test and implement solutions around "recovering" a stuck process including possibly any of these in certain circumstances:
- killing all cline processes with `-9` signal
- running `cline task list` to determine which task (aka session) is most recently associated with a stuck oneshot process.
  - to this end, we should adjust the worker_prompt header line to include the same timestamp pattern as the oneshot .json filename.
  - this will serve as a correlation id, to make it easier to identify the correct session from an agent's list of sessions.
  - for example, `$project_name worker 2026-01-19_16-46-01_oneshot\n\n` so that its easier to reason about catching up or resuming activity.
  - running onelist will generate and display "2026-01-19_16-46-01_oneshot" as its oneshot id, and then the oneshot id can be used to `oneshot --resume $oneshot_id`
  - as a function of the resuming concept here, oneshot should pull all api conversation history (or at least, the part of conversation history which is now missing from the log), into the oneshot log.  then, the last "2kb" or last message or whatever portion is shared with the auditor should be sent to the auditor in that --resume workflow.  from that moment on, "reworker/auditor" iteration will occur. 
  - this --resume feature is an opportunity to continue executing after max iterations was exhausted.

  - if resume is given both a oneshot id and a prompt, prepare to overwrite any original prompt with the new prompt.
  - make sure the original prompt exists in the oneshot session file.
  - fix any files called session_*.md.  All files should have consistent timestamp beginning but different -suffixes.ext

Create a project plan with detailed checklist instructions.  Do not execute this project plan yet.



