#!/usr/bin/env python3
"""
Demonstration script to test AiderExecutor with a simple task.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from oneshot.providers.aider_executor import AiderExecutor

def main():
    """Test AiderExecutor with a simple query."""
    print("=" * 60)
    print("Testing AiderExecutor with: 'test prompt'")
    print("=" * 60)

    # Create an AiderExecutor instance
    executor = AiderExecutor(git_dir=os.getcwd())

    # Run the task
    task = "test prompt"
    print(f"\nRunning task: {task}")
    print("-" * 60)

    result = executor.run_task(task)

    # Display results
    print(f"\nExecution Result:")
    print(f"  Success: {result.success}")
    print(f"  Output:\n{result.output}")
    if result.error:
        print(f"  Error: {result.error}")
    if result.git_commit_hash:
        print(f"  Git Commit Hash: {result.git_commit_hash}")
    print(f"  Metadata: {result.metadata}")

    print("-" * 60)
    print("Test completed!")

    return 0 if result.success else 1

if __name__ == "__main__":
    sys.exit(main())