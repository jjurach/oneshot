Introduce new oneshot feature:

In addition to get_worker_prompt and get_auditor_prompt, add
get_reworker_prompt.

The prompt given to the initial worker agent invocation should contain these
clearly demarcated sections:
- header line (title)
- get_worker_prompt
- input prompt

The prompt given to both initial and subsequent auditor agent invocations
should contain these clearly demarcated sections:
- header line (title)
- get_auditor_prompt
- original input prompt 
- worker output -- final 2kb (or final message if message contains clear json)

The prompt given to subsequent worker agent invocations should contain these
clearly demarcated sections:
- header line (title)
- get_reworker_prompt
- original input prompt
- auditor_feedback

Notes:
- The auditor prompt should encourage the auditor to provide "feedback" to be
  passed to the subsequent worker flow(s)
- The reworker prompt should be careful that the worker MUST ONLY consider what
  is in the original prompt and in the auditor feedback, and not start
  wondering in random directions.

- The reworker prompt may contain text like this:
> Re-run your tests. If you think the requested change is complete and
> successful, then be very careful to output this expected JSON and nothing
> else.

create this project plan now.  do not implement yet.
