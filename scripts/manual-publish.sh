#!/bin/bash
set -e

echo "Building package..."
rm -rf dist/
uv build

echo "Package built. Contents of dist/:"
ls -la dist/

echo ""
echo "To publish to PyPI, run:"
echo "uv publish --token <YOUR_PYPI_TOKEN>"
echo ""
echo "Or using twine:"
echo "pip install twine"
echo "twine upload dist/* --username __token__ --password <YOUR_PYPI_TOKEN>"