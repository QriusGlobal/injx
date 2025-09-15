#!/bin/bash
set -e

echo "Building MkDocs documentation..."
uvx --with mkdocs-material mkdocs build

echo "Copying raw markdown files..."
mkdir -p site/raw
cp raw/*.md site/raw/ 2>/dev/null || echo "No raw markdown files found"

echo "Deploying to GitHub Pages..."
uvx --with mkdocs-material mkdocs gh-deploy --force --ignore-version

echo "✅ Documentation deployed successfully!"
echo "📖 Documentation site: https://qriusglobal.github.io/injx/"
echo "🤖 LLM standard endpoint: https://qriusglobal.github.io/injx/llms.txt"