#!/bin/bash
echo "🔥 PLUTOBOT FORCE INSTALLER 🔥"
echo "================================="

# Function to check if a command succeeded
check_success() {
    if [ $? -eq 0 ]; then
        echo "✅ SUCCESS"
    else
        echo "❌ FAILED"
        exit 1
    fi
}

# 1. Force remove any existing problem packages
echo "📦 Cleaning old packages..."
pip uninstall discord.py-selfbot discord.py-self protobuf -y > /dev/null 2>&1
pip cache purge > /dev/null 2>&1
echo "✅ Cleaned"

# 2. Install core dependencies FIRST (this is often the fix)
echo "📦 Installing core build tools..."
pip install --no-cache-dir wheel setuptools --upgrade
check_success

# 3. Install protobuf separately (known problematic dependency)
echo "📦 Installing protobuf..."
pip install --no-cache-dir protobuf==3.20.3
check_success

# 4. Install the main package with verbose output
echo "📦 Installing discord.py-selfbot (this may take a moment)..."
pip install --no-cache-dir --verbose discord.py-selfbot==2.0.0
check_success

# 5. Install remaining requirements
echo "📦 Installing other packages..."
pip install --no-cache-dir colorama==0.4.6 aiohttp==3.9.1 requests==2.31.0
check_success

# 6. Verify installation
echo "🔍 Verifying installations..."
python -c "import discord; print('✅ discord OK')" || { echo "❌ discord failed"; exit 1; }
python -c "import colorama; print('✅ colorama OK')" || { echo "❌ colorama failed"; exit 1; }
echo "🎉 All packages verified!"

# 7. Start the bot
echo "🚀 Starting plutobot.py..."
python plutobot.py
