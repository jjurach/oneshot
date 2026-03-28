
Let's arrange for this to work:
```
oneshot --executor direct "what is the capital of sweden?"
```
Let's do whatever is necessary to treat "direct" as a regular executor which
can serve worker role.  We will be able to prove a concept with tasks like
"2+2?", and we will have a starting platform for our lang-graph
experimentation.

by "support direct", i mean:

- the worker prompt will still get transmitted to ollama, and until we invent
  tooling and other lang-graph features in our "direct" implementation there
  will not be much to expect here.

ollama is up and running for this:
```
$ ollama ps
NAME                ID              SIZE      PROCESSOR    CONTEXT    UNTIL               
llama-pro:latest    6f6be4b4781a    5.5 GB    100% GPU     8192       52 minutes from now    
```

- add and run pytests and demo scripts
- update any usage documentation with this new feature

Create a @AGENTS.md project plan now. do not implement.
