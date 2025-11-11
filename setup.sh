#!/bin/bash

echo "🚀 Setting up Blog Automation App..."
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✅ Found $PYTHON_VERSION"
echo ""

# Create virtual environment
if [ -d "venv" ]; then
    echo "📦 Virtual environment already exists. Skipping creation."
else
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✅ pip upgraded"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Check for environment variables
echo "🔍 Checking environment variables..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY is not set"
    echo "   Run: export OPENAI_API_KEY='your-key-here'"
else
    echo "✅ OPENAI_API_KEY is set"
fi

if [ -z "$WEBFLOW_API_TOKEN" ]; then
    echo "⚠️  WEBFLOW_API_TOKEN is not set"
    echo "   Using default from code..."
else
    echo "✅ WEBFLOW_API_TOKEN is set"
fi
echo ""

echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Set environment variables (if not already set):"
echo "      export OPENAI_API_KEY='your-key'"
echo ""
echo "   2. Start the server:"
echo "      ./run.sh"
echo ""
echo "   3. Open your browser to:"
echo "      http://localhost:5000"
echo ""


