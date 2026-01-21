#!/usr/bin/env python3
"""
PTY Utilities for streaming subprocess execution.

Provides robust PTY-based command execution for real-time streaming output,
with intelligent chunk buffering and platform compatibility.

This module was extracted from oneshot.py to consolidate streaming infrastructure
and eliminate code duplication across executors.
"""

import json
import logging
import os
import platform
import pty
import select
import subprocess
import sys
import time
from typing import Optional, Tuple, List

# ============================================================================
# CONFIGURATION
# ============================================================================

DISABLE_STREAMING = os.environ.get('ONESHOT_DISABLE_STREAMING', '0') == '1'
SUPPORTS_PTY = platform.system() in ('Linux', 'Darwin')  # Unix/Linux and macOS

# Get logger for this module
logger = logging.getLogger(__name__)


# ============================================================================
# LOGGING UTILITIES
# ============================================================================

def _get_verbosity() -> int:
    """
    Get current verbosity level from environment or module globals.

    Returns:
        int: 0=default, 1=verbose, 2=debug
    """
    return int(os.environ.get('ONESHOT_VERBOSITY', '0'))


def _log_debug(msg: str):
    """Log debug message if verbosity >= 2."""
    if _get_verbosity() >= 2:
        print(f"[DEBUG] {msg}", file=sys.stderr)


def _log_verbose(msg: str):
    """Log verbose message if verbosity >= 1."""
    if _get_verbosity() >= 1:
        print(f"[VERBOSE] {msg}", file=sys.stderr)


# ============================================================================
# PTY STREAMING EXECUTION
# ============================================================================

def call_executor_pty(cmd: List[str], input_data: Optional[str] = None,
                      timeout: Optional[float] = None,
                      buffer_size: int = 1024,
                      accumulation_buffer_size: int = 4096) -> Tuple[str, str, int]:
    """
    Execute command using PTY allocation for real-time streaming output.

    PTY allocation forces CLI tools to detect a terminal and use line-buffering
    instead of full buffering, enabling real-time output streaming.

    Args:
        cmd: Command and arguments as list
        input_data: Optional stdin data for the process
        timeout: Subprocess timeout in seconds
        buffer_size: Size of read buffer (1024 bytes typical for line-buffered output)
        accumulation_buffer_size: Size of accumulation buffer before activity processing (4096 bytes)

    Returns:
        Tuple of (stdout, stderr, exit_code)

    Raises:
        OSError: If PTY allocation fails
        subprocess.TimeoutExpired: If timeout is exceeded
    """
    if not SUPPORTS_PTY:
        _log_debug("PTY not supported on this platform, falling back to buffered execution")
        raise OSError("PTY not supported on Windows")

    if DISABLE_STREAMING:
        _log_debug("Streaming disabled via ONESHOT_DISABLE_STREAMING environment variable")
        raise OSError("Streaming disabled")

    try:
        # Allocate master and slave PTY file descriptors
        master_fd, slave_fd = pty.openpty()
        _log_debug(f"PTY allocated: master={master_fd}, slave={slave_fd}")
        _log_debug(f"[PTY CONFIG] buffer_size={buffer_size} bytes, accumulation_buffer_size={accumulation_buffer_size} bytes")

        stdout_data = []
        stderr_data = []
        accumulation_buffer = []  # Buffer for accumulating chunks before processing
        buffer_total_bytes = 0
        chunk_count = 0
        exit_code = 1  # Default exit code
        start_time = time.time()

        try:
            # Fork and execute process
            pid = os.fork()

            if pid == 0:
                # Child process
                os.setsid()  # Create new session
                os.dup2(slave_fd, 0)  # stdin
                os.dup2(slave_fd, 1)  # stdout
                os.dup2(slave_fd, 2)  # stderr

                # Close PTY file descriptors in child
                os.close(master_fd)
                os.close(slave_fd)

                try:
                    os.execvp(cmd[0], cmd)
                except Exception as e:
                    print(f"[INFO] Failed to execute {cmd[0]}: {e}", file=sys.stderr)
                    sys.exit(1)
            else:
                # Parent process
                os.close(slave_fd)
                _log_debug(f"Child process spawned with PID {pid}")

                # Read output from master PTY with chunk accumulation
                process_exited = False
                while True:
                    # Check timeout
                    if timeout is not None:
                        elapsed = time.time() - start_time
                        if elapsed > timeout:
                            import signal
                            os.killpg(os.getpgid(pid), signal.SIGTERM)
                            raise subprocess.TimeoutExpired(cmd[0], timeout)

                    # Check if process is done
                    if not process_exited:
                        try:
                            wpid, status = os.waitpid(pid, os.WNOHANG)
                            if wpid == pid:
                                exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else 1
                                _log_debug(f"Process exited with code {exit_code}")
                                process_exited = True

                                # Flush any remaining accumulated data
                                if accumulation_buffer:
                                    accumulated_text = ''.join(accumulation_buffer)
                                    stdout_data.append(accumulated_text)
                                    if _get_verbosity() >= 1:
                                        _log_verbose(f"[Accumulate] Flushed {len(accumulated_text)} chars ({len(accumulation_buffer)} chunks) on process exit")
                                    accumulation_buffer = []
                                    buffer_total_bytes = 0
                        except OSError:
                            break

                    # Read available data with select for non-blocking I/O
                    try:
                        ready, _, _ = select.select([master_fd], [], [], 0.1)
                        if ready:
                            try:
                                data = os.read(master_fd, buffer_size)
                                if data:
                                    chunk_count += 1
                                    chunk_text = data.decode('utf-8', errors='replace')
                                    accumulation_buffer.append(chunk_text)
                                    buffer_total_bytes += len(chunk_text)

                                    # Minimal logging for streaming chunks (only in debug mode)
                                    if _get_verbosity() >= 2:
                                        preview = chunk_text[:100].replace('\n', '\\n')
                                        _log_debug(f"[PTY CHUNK] #{chunk_count}: {len(data)} bytes, accumulated: {buffer_total_bytes}/{accumulation_buffer_size} bytes")
                                        _log_debug(f"[PTY CHUNK] Preview: {preview}{'...' if len(chunk_text) > 100 else ''}")

                                    # Check if we should flush the accumulation buffer
                                    should_flush = False

                                    # Flush on accumulation buffer size limit
                                    if buffer_total_bytes >= accumulation_buffer_size:
                                        should_flush = True
                                        flush_reason = f"size limit reached ({buffer_total_bytes} >= {accumulation_buffer_size} bytes)"
                                        _log_debug(f"[PTY FLUSH TRIGGER] {flush_reason}")
                                    # Flush on complete lines (good boundary for text output)
                                    elif '\n' in chunk_text and buffer_total_bytes > 0:
                                        should_flush = True
                                        flush_reason = "line boundary detected"
                                        _log_debug(f"[PTY FLUSH TRIGGER] {flush_reason} (buffer: {buffer_total_bytes} bytes)")
                                    # Flush on JSON object boundaries (for structured output)
                                    elif ('}' in chunk_text or '{' in chunk_text) and buffer_total_bytes > 50:
                                        # Check if we have a complete JSON object
                                        accumulated_text = ''.join(accumulation_buffer)
                                        try:
                                            json.loads(accumulated_text.strip())
                                            should_flush = True
                                            flush_reason = "complete JSON object detected"
                                            _log_debug(f"[PTY FLUSH TRIGGER] {flush_reason}")
                                        except json.JSONDecodeError:
                                            # Check for multiple JSON objects
                                            lines = accumulated_text.split('\n')
                                            complete_objects = 0
                                            for line in lines:
                                                line = line.strip()
                                                if line and (line.startswith('{') and line.endswith('}')):
                                                    try:
                                                        json.loads(line)
                                                        complete_objects += 1
                                                    except json.JSONDecodeError:
                                                        pass
                                            if complete_objects > 0:
                                                should_flush = True
                                                flush_reason = f"{complete_objects} complete JSON line(s) detected"
                                                _log_debug(f"[PTY FLUSH TRIGGER] {flush_reason}")

                                    if should_flush:
                                        accumulated_text = ''.join(accumulation_buffer)
                                        preview = accumulated_text[:200].replace('\n', '\\n')
                                        _log_debug(f"[PTY FLUSH] Reason: {flush_reason}")
                                        _log_debug(f"[PTY FLUSH] Content: {len(accumulated_text)} bytes → {preview}{'...' if len(accumulated_text) > 200 else ''}")
                                        stdout_data.append(accumulated_text)
                                        _log_debug(f"[PTY STDOUT] Total accumulated so far: {sum(len(s) for s in stdout_data)} bytes")
                                        # Remove verbose accumulation logging that was causing noise
                                        accumulation_buffer = []
                                        buffer_total_bytes = 0
                                else:
                                    # No more data, flush any remaining accumulated data
                                    if accumulation_buffer:
                                        accumulated_text = ''.join(accumulation_buffer)
                                        stdout_data.append(accumulated_text)
                                        if _get_verbosity() >= 1:
                                            _log_verbose(f"[Accumulate] Final flush: {len(accumulated_text)} chars ({len(accumulation_buffer)} chunks)")
                                        accumulation_buffer = []
                                        buffer_total_bytes = 0
                                    break
                            except OSError:
                                break
                    except Exception as e:
                        _log_debug(f"Error in select/read: {e}")
                        break

                    # If process has exited and we've read all available data, break
                    if process_exited:
                        break

                # Handle stdin input if provided
                if input_data and False:  # We handle stdin via shell redirection for now
                    pass

        finally:
            # Cleanup PTY
            try:
                os.close(master_fd)
            except OSError:
                pass

        return ''.join(stdout_data), ''.join(stderr_data), exit_code

    except Exception as e:
        _log_debug(f"PTY execution failed: {e}")
        raise
