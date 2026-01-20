#!/usr/bin/env python3
"""
Demo script for Gemini executor with various output formats and approval modes.

This script demonstrates how to use the oneshot CLI with the --executor gemini option,
showcasing different combinations of output formats and approval modes.

Prerequisites:
- Gemini CLI installed and configured
- oneshot package installed

Usage:
  python demo_gemini_executor.py
  python demo_gemini_executor.py "Your custom task here"
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


class GeminiExecutorDemo:
    """Demo class for showcasing Gemini executor functionality."""

    def __init__(self, custom_task: str = None):
        self.custom_task = custom_task or "Create a simple Python function that calculates the factorial of a number"
        self.demos = [
            {
                "name": "Basic Gemini Executor (default settings)",
                "description": "Basic usage with default JSON output and yolo approval mode",
                "command": ["oneshot", "--executor", "gemini", self.custom_task],
                "expected_output": "Should show basic execution with JSON output format"
            },
            {
                "name": "Gemini with Stream-JSON Output",
                "description": "Using streaming JSON output format for real-time updates",
                "command": ["oneshot", "--executor", "gemini", "--output-format", "stream-json", self.custom_task],
                "expected_output": "Should show streaming JSON events as they occur"
            },
            {
                "name": "Gemini with Normal Approval Mode",
                "description": "Using normal approval mode (requires manual approval for actions)",
                "command": ["oneshot", "--executor", "gemini", "--approval-mode", "normal", self.custom_task],
                "expected_output": "Should prompt for approval before executing actions"
            },
            {
                "name": "Gemini with Stream-JSON and Normal Approval",
                "description": "Combining streaming output with manual approval mode",
                "command": ["oneshot", "--executor", "gemini", "--output-format", "stream-json", "--approval-mode", "normal", self.custom_task],
                "expected_output": "Should show streaming events and require manual approval"
            },
            {
                "name": "Gemini with JSON Output and YOLO Mode",
                "description": "Explicitly setting JSON output and yolo approval (same as default)",
                "command": ["oneshot", "--executor", "gemini", "--output-format", "json", "--approval-mode", "yolo", self.custom_task],
                "expected_output": "Should behave identically to basic demo"
            },
            {
                "name": "Gemini with Custom Session Logging",
                "description": "Using custom session logging with stream-json output",
                "command": ["oneshot", "--executor", "gemini", "--output-format", "stream-json", "--session-log", "demo_gemini_session.md", "--keep-log", self.custom_task],
                "expected_output": "Should create a session log file with execution details"
            }
        ]

    def run_command(self, cmd: List[str]) -> Tuple[int, str, str]:
        """Run a command and return exit code, stdout, and stderr."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out after 300 seconds"
        except FileNotFoundError:
            return -1, "", "Command not found. Make sure 'oneshot' is installed and in PATH."

    def print_header(self):
        """Print the demo header."""
        print("=" * 80)
        print("🤖 ONESHOT GEMINI EXECUTOR DEMO")
        print("=" * 80)
        print()
        print("This demo showcases the --executor gemini feature with various options:")
        print("• --output-format: json (structured) or stream-json (streaming)")
        print("• --approval-mode: normal (requires approval) or yolo (auto-approve)")
        print()
        print(f"Task: {self.custom_task}")
        print()
        print("Note: These demos will actually execute the Gemini CLI.")
        print("Make sure Gemini CLI is installed and configured before running.")
        print()

    def run_demo(self, demo_config: dict) -> bool:
        """Run a single demo configuration."""
        print(f"📋 Demo: {demo_config['name']}")
        print(f"   Description: {demo_config['description']}")
        print(f"   Command: {' '.join(demo_config['command'])}")
        print(f"   Expected: {demo_config['expected_output']}")
        print()

        # Ask user if they want to run this demo
        try:
            response = input("Run this demo? (y/n): ").strip().lower()
            if response not in ['y', 'yes']:
                print("⏭️  Skipping demo...")
                print("-" * 60)
                return True
        except KeyboardInterrupt:
            print("\n⏹️  Demo interrupted by user")
            return False

        print("🚀 Running demo...")
        print("-" * 60)

        # Run the command
        exit_code, stdout, stderr = self.run_command(demo_config['command'])

        # Print results
        if exit_code == 0:
            print("✅ Demo completed successfully!")
            if stdout.strip():
                print("📄 Output:")
                # Truncate very long output for readability
                output_lines = stdout.split('\n')
                if len(output_lines) > 50:
                    print('\n'.join(output_lines[:25]))
                    print(f"... ({len(output_lines) - 50} more lines) ...")
                    print('\n'.join(output_lines[-25:]))
                else:
                    print(stdout)
        else:
            print(f"❌ Demo failed with exit code {exit_code}")
            if stderr.strip():
                print("❗ Error output:")
                print(stderr[:1000])  # Limit error output
                if len(stderr) > 1000:
                    print("... (truncated)")
            if stdout.strip():
                print("📄 Standard output:")
                print(stdout[:1000])
                if len(stdout) > 1000:
                    print("... (truncated)")

        print("-" * 60)
        return True

    def run_all_demos(self):
        """Run all demo configurations."""
        self.print_header()

        for i, demo in enumerate(self.demos, 1):
            print(f"\n[{i}/{len(self.demos)}]")
            if not self.run_demo(demo):
                break

        print("\n" + "=" * 80)
        print("🎉 DEMO COMPLETE!")
        print("=" * 80)
        print()
        print("Summary of Gemini executor features demonstrated:")
        print("• Basic execution with default settings")
        print("• Stream-JSON output format for real-time updates")
        print("• Normal approval mode requiring manual confirmation")
        print("• Combination of output formats and approval modes")
        print("• Custom session logging")
        print()
        print("The --executor gemini feature is now ready for use!")
        print()


def main():
    """Main entry point."""
    # Allow custom task via command line argument
    custom_task = sys.argv[1] if len(sys.argv) > 1 else None

    demo = GeminiExecutorDemo(custom_task)
    demo.run_all_demos()


if __name__ == "__main__":
    main()