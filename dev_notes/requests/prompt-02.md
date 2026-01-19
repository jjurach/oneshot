
Note:
this command works:
```
aider --message "What is the capital of france?" --chat-mode ask --yes-always --no-stream --no-pretty
```
with this .env file (which is NOT all what chatterbox needs)
```
AIDER2_MODEL=ollama_chat/qwen2.5-coder:7b
AIDER_EDITOR2_MODEL=ollama_chat/qwen2.5-coder:7b
AIDER_MODEL=ollama_chat/llama-pro
AIDER_EDITOR_MODEL=ollama_chat/llama-pro
AIDER_ARCHITECT=true
OLLAMA_API_BASE=http://localhost:11434
AIDER_EDIT_FORMAT=whole
```

the .env we need is at .env.orig.   iterate on each configuration and remove them from the "working" .env until we have a command which doesn't require any change to .env.  then, recover the CHATTERBOX_ .env.orig when we control all aider behavior through its commandline arguments
