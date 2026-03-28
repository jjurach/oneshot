Several git versions ago, oneshot was streaming information as things were occurring, but that stopped, and now it's "batch" -- nothing then all at once.  I want it to stream. Running these agents with `--output-format json-stream` or similar seems to expose the JSON-formatted data in the underlying local storage representing the activity of the executor.

There are two files created during oneshot execution:

- <oneshot-id>-oneshot.json (aka "oneshot.json file") - this contains the executor, prompt text, updated at timestamp, and execution/result-summary/state-change history. It is intended to help the oneshot process maintain state across multiple executions to support features like `--resume`. 
- <oneshot-id>-oneshot-log.json (aka "oneshot-log.json") - this contains an append-only ndjson-formatted sequence of activity.

The "json packets" from agents like cline and claude tend to have a shape like "{\n "text":"thinking",...\n}\n". I believe agents are very strict about outputting only well-formed JSON, but badly formed "packets" should be written to stderr or and error log whenever their content would otherwise be lost. 

As each "packet" (of json representing agent activity) comes in, I want executor classes to have an opportunity to massage it into some internal representation before it gets written to the oneshot-log.json file, wrapped within a simple JSON expression to provide millisecond-since-epoch timestamp and origin: `{"ts":1768954851123,"executor":<executor>,"oneshot-id":<id-for-oneshot-invocation>,"activity":<orig-executor-output-json>}`  and formatted as a single line for ndjson.

This "ts"-containing JSON object is the standard internal representation of a "oneshot activity" (or sometimes just "activity" according to context), which will be commonly shared/translated to/from based on variations we see from various tools.  Generally speaking, once a "packet" has been parsed from the executor output, and has been processed through a pipeline of activities which includes json parsing, append oneshot activity line to oneshot-log.json, write a text summary to the user running the oneshot command -- once all that happens, oneshot shouldn't need to do anything with that information and can release it from memory. The oneshot-log.json file is the source of record. 

Introduce a "state" attribute to the oneshot.json file and "executionPid" and any other attributes required to inform `--resume` and other features. This state should reflect the internal one-shot state engine which drives iterations to completion.  For example, if the state engine reflects "worker-executing" (or similar), and then `oneshot --resume $oneshot_id` or `oneshot --resume $oneshot_filename` were called (or --view variants to summarize the current state of an execution), oneshot will read the oneshot.json file, see this "worker-executing" state but see the worker is no longer running at that pid, and will be able to transition the state to "worker-failed" or "worker-recovering" or similar.

If the oneshot process observes an executor process fail with a non-zero exit status, oneshot should write this "worker-failed" state to the oneshot.json file if aborting, or eventually to "worker-recovering" when those features are implemented.

Recovery is a concept defined by the executor subclass class so it will be implemented as one or more virtual methods on the executor class. Recovery may involve running different agent commands (e.g. `cline task view --output-format json`) to fetch agent activity information, or else to consult a directory like `~/.cline/data/tasks/$task_id/` to pull json data more directly.  Recovery will involve reconciling the history already written to the oneshot-log.json.  Some effort should be made within each executor class to correlate the activity in the agent to the activity already written to oneshot-log.json in order to ensure that the oneshot-log is a full accounting of what happened in that session, and that there is no duplication of information.

Use the information above to identify or create docs/ files which capture these design intentions.  We want the details spelled out clearly in our documentation before we engage in a long-term sequence of agentic tasks to produce all of these intended features.

Major themes to cover:

- oneshot needs to convey "streaming" with regular updates (every few seconds or so) to the user what the agent is doing. it needs to avoid waiting minutes and then outputting one big dump.
  - Such second-by-second interaction with the agent's output will drive "inactivity detection" features which may prompt oneshot to kill the agent and to transition to "worker-failed" or "auditor-failed" states.
  - The (ingest) millisecond timestamps on "oneshot activity" json dumps will clearly demonstrate whether the implementation is "streaming" this information.
- oneshot should do a better job parsing activity from agents, and feeding "oneshot activity" through a pipeline which involves writing to the oneshot-log.json file, text-formatting with the executor subclass, and possibly other "pipeline callbacks" within the executor base class or subclass related to usage analysis / cost measurement, etc.
- the oneshot.json file will represent the state of the internal oneshot state engine in order to be able to "resume" the processing for the same $oneshot_id oneshot execution across multiple command invocations.  It will contain a timestamped history of state transitions, possibly with a reason or error text or some other summary.

Create this documentation now.
