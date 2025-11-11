#!/bin/bash

echo "🔍 Checking .env file configuration..."
echo ""

if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "   Create it by copying env.template:"
    echo "   cp env.template .env"
    exit 1
fi

echo "✅ .env file exists"
echo ""
echo "📋 Current configuration (values masked for security):"
echo ""

# Read .env and mask values
while IFS='=' read -r key value; do
    # Skip empty lines and comments
    if [[ -z "$key" ]] || [[ "$key" =~ ^# ]]; then
        continue
    fi
    
    # Mask the value
    if [[ -n "$value" ]]; then
        if [[ ${#value} -gt 8 ]]; then
            masked="${value:0:4}...${value: -4}"
        else
            masked="***"
        fi
        echo "  ✅ $key = $masked"
    else
        echo "  ⚠️  $key = (empty)"
    fi
done < .env

echo ""
echo "To edit: nano .env"

