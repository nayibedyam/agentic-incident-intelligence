#!/bin/bash
set -e

# --- Configuration ---
# LLM Provider: "anthropic" or "bedrock"
export LLM_PROVIDER="bedrock"

# Model ID
export MODEL_ID="us.anthropic.claude-opus-4-8"

# --- Anthropic Direct API (when LLM_PROVIDER=anthropic) ---
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# --- AWS Bedrock (when LLM_PROVIDER=bedrock) ---
# Option 1: Profile-based (recommended — uses ~/.aws/credentials)
export AWS_PROFILE=""
export AWS_REGION="us-west-2"

# Option 2: Explicit keys (leave AWS_PROFILE empty)
export AWS_ACCESS_KEY_ID=""
export AWS_SECRET_ACCESS_KEY=""

# --- Run ---
echo "Starting Agentic Incident Intelligence..."
echo "  Provider: $LLM_PROVIDER"
echo "  Model:    $MODEL_ID"
if [ "$LLM_PROVIDER" = "bedrock" ]; then
  if [ -n "$AWS_PROFILE" ]; then
    echo "  Auth:     AWS Profile ($AWS_PROFILE)"
  else
    echo "  Auth:     Explicit AWS keys"
  fi
fi
echo ""

docker compose up --build
