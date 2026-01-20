#!/usr/bin/env python3
"""
Demo script for the Direct Executor functionality.

This script demonstrates how to use the direct executor to query Ollama models
directly through the oneshot CLI.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path so we can import oneshot modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from oneshot.providers.direct_executor import DirectExecutor
from oneshot.providers.ollama_client import OllamaClient

def demo_direct_executor():
    """Demonstrate the DirectExecutor functionality."""
    print("🤖 Direct Executor Demo")
    print("=" * 50)

    # Test 1: Basic functionality
    print("\n1. Testing DirectExecutor instantiation...")
    try:
        executor = DirectExecutor()
        print(f"✅ DirectExecutor created: {executor}")
    except Exception as e:
        print(f"❌ Failed to create DirectExecutor: {e}")
        return False

    # Test 2: Ollama client connection
    print("\n2. Testing Ollama client connection...")
    try:
        client = OllamaClient()
        if client.check_connection():
            print("✅ Ollama service is reachable")
            models = client.list_models()
            print(f"📋 Available models: {models}")
        else:
            print("❌ Cannot connect to Ollama service")
            print("   Make sure Ollama is running with: ollama serve")
            return False
    except Exception as e:
        print(f"❌ Ollama client error: {e}")
        return False

    # Test 3: Simple query execution
    print("\n3. Testing simple query execution...")
    test_queries = [
        "What is 2+2?",
        "What is the capital of Sweden?",
        "Say hello in Spanish"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n   Query {i}: {query}")
        try:
            result = executor.run_task(query)
            if result.success:
                print(f"   ✅ Response: {result.output}")
            else:
                print(f"   ❌ Error: {result.error}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

    print("\n" + "=" * 50)
    print("🎉 Direct Executor demo completed!")
    return True

def demo_cli_usage():
    """Show CLI usage examples."""
    print("\n📖 CLI Usage Examples")
    print("=" * 50)
    print("# Basic usage with direct executor")
    print("oneshot --executor direct 'What is the capital of France?'")
    print()
    print("# With custom model")
    print("oneshot --executor direct --worker-model llama-pro:latest 'Explain quantum computing'")
    print()
    print("# With both worker and auditor using direct executor")
    print("oneshot --executor direct --worker-model llama-pro:latest --auditor-model llama-pro:latest 'Write a haiku about coding'")
    print()
    print("# Note: Ollama must be running for the direct executor to work")
    print("# Start Ollama with: ollama serve")
    print("# Pull models with: ollama pull llama-pro:latest")

if __name__ == "__main__":
    print("Oneshot Direct Executor Demo")
    print("This demo shows the new direct executor that forwards prompts to Ollama.")

    success = demo_direct_executor()
    demo_cli_usage()

    if success:
        print("\n✅ Demo completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Demo failed - check Ollama setup")
        sys.exit(1)