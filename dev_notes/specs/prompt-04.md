
investigate why the claude cli isn't streaming its stream-json output yet.

Do we need to disable line-buffering on the file descriptor?

Do we need to allocate a pseudo-terminal?

Research with google search, and then generate an @AGENTS.md project plan


use this script for inspiration how to allocate pseudo-terminal.
```
import pty
import subprocess
import os

def run_claude_in_pty(prompt):
    # Create a master/slave PTY pair
    master, slave = pty.openpty()
    
    # Spawn Claude Code linked to the slave PTY
    process = subprocess.Popen(
        ["claude", "-p", prompt],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True
    )
    
    # Close the slave in the parent process
    os.close(slave)
    
    # Read from the master as Claude streams data
    try:
        while True:
            data = os.read(master, 1024)
            if not data:
                break
            print(data.decode(), end="", flush=True)
    except OSError:
        pass # End of stream

run_claude_in_pty("Refactor the login logic in main.py")
```

Success is seeing the claude code cli give me iterative reports on progress rather than waiting until the entire process is complete to output anything.

Do not implement. just create the plan.

