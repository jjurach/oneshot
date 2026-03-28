To build on docs/streaming-and-state-management.md, consider more details:

Within the context of "state machine" transitions, one can say that the purpose
of the worker-executing phase is to calculate a resultSummary to pass to the
auditor for assessment.

The perfect resultSummary will be a final message from the agent which is
JSON and which follows the SYSTEM prompt's instructions. But agents can be a
little unpredictable how they behave, therefore...

The oneshot auditing system will be set up to allow for a fuzzier assessment of
completion by a follow-up call to an ai agent:

- a "full text" representation of each individual activity item from the tail of all activity is considered
- an algorithm is applied to find the most likely result message:
  - a score is calculated based on words or patterns containing: status, done, success, human, intervention, json delimiters
  - the latest activity with the best score is chosen, and then
    - choose "full text" from up two useful leading and trailing activity items -- 5 items total.

  - this same algorithm can be generalized and applied to auditorFeedback calculation:
    - the score can be based on the total number of words

- the algorithm can be tested/improved on real world oneshot-log.json files, as
  this project obtains more and more confidence about this interaction.

To summarize:
- state system transitions to worker-executing after starting the agent process
- 'run_oneshot()` calls the worker prompt generator with the input prompt
- the worker prompt generator sends the following information in <xml>-delimited sections: 
```
<oneshot>$oneshot_id worker #$iteration_n</oneshot>

$worker_system_prompt

<instruction>
$original_input_prompt
</instruction>
```
- the executor command is called with this worker prompt to produce a subprocess
  - the agent subprocess (e.g. gemini-cli, aider) writes json activity events to its stdout
  - our oneshot process accumulates string from this file descriptor into a buffer
  - well-balanced, well-formed JSON are detected, extracted from buffer then fed into the event pipeline
- the event pipeline considers each piece of activity from the agent:
  - wraps in "oneshot activity" with millisecond timestamp to append to oneshot-log.json
  - displays text format to the user
  - etc. this is described elsewhere

- if the subprocess exits with failed status,
  - state transitions to worker-failed
  - the oneshot.json file is updated to reflect the latest state
  - oneshot dies with error message

- a successful exit status will lead to the execution of an algorithm on the oneshot-log.json file.

- the algorithm will behave as described above, and return a resultSummary structure with:
  - result: string - the text format of the activity event which is most likely to have the best result
  - leadingContext: string[] - a small number of text format of leading activity events
  - trailingContext: string[] - a small number of text format of trailing activity events
- this resultSummary is fed into the auditor prompt generator
- the prompt generator conditionally adds leading and trailing context based
  the `max_prompt_length()` value of the executor.
  - especially to supporting "direct" ollama local llm models which are limited to 8192 tokens.
  - most executors should have 100000 to allow virtually unlimited prompt size.
- the prompt generator will avoid leaving empty (e.g. <empty></empty>) labels.

- the audit prompt generator sends the following information in <xml>-delimited sections: 
```
<oneshot>$oneshot_id audit #$iteration_n</oneshot>

<what-was-requested>
$original_input_prompt
</what-was-requested>

<worker-result>
 <leading-context>
$activity_n_minus_2
$activity_n_minus_1
 </leading-context>
$result
 <trailing-context>
$activity_n_plus_1
$activity_n_plus_2
 </trailing-context>
</worker-result>

$auditor_system_prompt
```
- the executor command is called with this auditor prompt to produce a subprocess
  - the agent subprocess (e.g. gemini-cli, aider) writes json activity events to its stdout
  - our oneshot process accumulates string from this file descriptor into a buffer
  - etc.
  - this follows the same mechanism as described for worker, to feed into the same event pipeline.
- oneshot processes the auditor result according to its existing algorithm

- if the auditor result is to re-iterate, then auditorFeedback is extracted
  from some undecided amount of trailing activity "full text" format.
  - auditorFeedback is fed back into the worker prompt flow above, like this:
```
<oneshot>$oneshot_id worker #$iteration_n</oneshot>

<auditor-feedback>
$auditor_advice
<auditor-feedback>

<instruction>
$original_input_prompt
</instruction>

$reworker_system_prompt
```
