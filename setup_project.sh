#!/bin/bash

# Creates the initial folder structure for the insurance PDS RAG project.
# Run from the root of your repository.
# Usage: bash setup_project.sh

set -e

echo "Creating project structure..."

# Docs - written as you go, lives in the repo
mkdir -p docs/decisions
mkdir -p docs/setup
mkdir -p docs/evaluation

# Corpus - raw source PDFs and processed output
mkdir -p corpus/raw
mkdir -p corpus/processed
mkdir -p corpus/metadata

# Notebooks - exploration, chunking experiments, eval analysis
mkdir -p notebooks

# Source - pipeline components, kept flat until architecture is confirmed
mkdir -p src

# Tests
mkdir -p tests

# Evaluation - ground truth pairs, RAGAS results, reports
mkdir -p evaluation/ground_truth
mkdir -p evaluation/results

# Keep empty directories in git
touch docs/decisions/.gitkeep
touch docs/setup/.gitkeep
touch docs/evaluation/.gitkeep
touch corpus/raw/.gitkeep
touch corpus/processed/.gitkeep
touch corpus/metadata/.gitkeep
touch notebooks/.gitkeep
touch src/.gitkeep
touch tests/.gitkeep
touch evaluation/ground_truth/.gitkeep
touch evaluation/results/.gitkeep

# Create the running progress log
cat > docs/progress.md << 'EOF'
# Project Progress Log

Newest entries at the top.

---

EOF

# Create a placeholder for the first decision log
cat > docs/decisions/template.md << 'EOF'
# Decision: [Title]

**Date:**
**Status:** decided / revisited / superseded

## Context

What was the situation that required a decision?

## Options considered

What alternatives were on the table?

## Decision

What did you choose and why?

## Consequences

What does this make easier or harder?

---
EOF

echo "Done. Structure created:"
find . -not -path './.git/*' -not -name '.gitkeep' | sort
