#!/bin/bash
# Wrapper script to generate search index

cd "$(dirname "$0")"

echo "🔍 Generating search index from Webflow CMS..."

# Activate virtual environment and run script
source venv/bin/activate
python3 generate_search_index.py

echo ""
echo "✨ Search index generation complete!"
echo "📁 Output: search_index.json"

