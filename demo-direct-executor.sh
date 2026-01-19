#!/bin/bash
#
# Demo script for oneshot with direct executor and Ollama
#
# This script demonstrates using oneshot with the direct provider to call
# a local Ollama model. It shows how to use locally-hosted LLMs with oneshot
# without needing proprietary APIs.
#
# Prerequisites:
# - Ollama running locally (docker run -d -p 11434:11434 ollama/ollama)
# - A model pulled (ollama pull llama-pro)
# - oneshot installed and on PATH
#
# Usage:
#   ./demo-direct-executor.sh
#   ./demo-direct-executor.sh "Your custom task here"
#

set -e

# Configuration
OLLAMA_ENDPOINT="http://localhost:11434/v1/chat/completions"
OLLAMA_MODEL="llama-pro"
DEMO_TASK="${1:-What is the capital of Norway?}"

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Oneshot Direct Executor Demo ===${NC}"
echo -e "${BLUE}Demonstrating oneshot with local Ollama model${NC}\n"

# Check if Ollama is running
echo -e "${YELLOW}Checking Ollama connectivity...${NC}"
if ! curl -s "${OLLAMA_ENDPOINT}" > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Cannot connect to Ollama at ${OLLAMA_ENDPOINT}${NC}"
    echo -e "${RED}Please ensure Ollama is running. Start it with:${NC}"
    echo -e "${RED}  docker run -d -p 11434:11434 ollama/ollama${NC}"
    echo -e "${RED}Or visit: https://ollama.ai${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Ollama is running${NC}\n"

# Check if model is available
echo -e "${YELLOW}Checking for model: ${OLLAMA_MODEL}${NC}"
if ! ollama list 2>/dev/null | grep -q "${OLLAMA_MODEL}"; then
    echo -e "${RED}❌ Model ${OLLAMA_MODEL} not found${NC}"
    echo -e "${RED}Pull the model with:${NC}"
    echo -e "${RED}  ollama pull ${OLLAMA_MODEL}${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Model ${OLLAMA_MODEL} is available${NC}\n"

# Run oneshot with direct executor
echo -e "${BLUE}Running oneshot...${NC}"
echo -e "${YELLOW}Task: ${DEMO_TASK}${NC}\n"

# Create logs directory if it doesn't exist
mkdir -p dev_notes/oneshot

# Run oneshot with direct provider
oneshot \
    --worker-provider direct \
    --worker-endpoint "${OLLAMA_ENDPOINT}" \
    --worker-model "${OLLAMA_MODEL}" \
    --auditor-provider direct \
    --auditor-endpoint "${OLLAMA_ENDPOINT}" \
    --auditor-model "${OLLAMA_MODEL}" \
    --session-log dev_notes/oneshot/demo_session.md \
    --keep-log \
    --max-iterations 3 \
    "${DEMO_TASK}"

echo -e "\n${GREEN}✓ Demo completed!${NC}"
echo -e "${BLUE}Session log saved to: dev_notes/oneshot/${NC}"
echo -e "${BLUE}You can review the complete execution in JSON format${NC}"

# List recent session logs
echo -e "\n${YELLOW}Recent session logs:${NC}"
ls -1t dev_notes/oneshot/*oneshot*.json 2>/dev/null | head -5 || echo "No session logs found"