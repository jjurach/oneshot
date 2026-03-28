
I ran this command.  See test.out. This output is still quite ugly and uninformative.
```
oneshot --verbose --debug "what is the capital of russia?" 2>&1 | tee test.out
```

look at docs/cline-activity-json.md for how to interpret this streaming json information.

I don't see any oneshot log or session json files at all.  what's up with that?
```
$ ls -ltr | tail -3
drwxr-xr-x 2 phaedrus phaedrus  4096 Jan 19 12:10 tmp
drwxr-xr-x 3 phaedrus phaedrus  4096 Jan 19 12:12 tests
-rw-r--r-- 1 phaedrus phaedrus 61373 Jan 19 12:20 test.out
```

Recover session file and new logging file feature which was supposed to be introduced with dev_notes/project_plans$ 2026-01-19_11-29-00_raw_ndjson_activity_logging.md.

Continue implementing and testing the feature until it is working.
