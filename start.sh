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

# 1. Clean old packages
echo "📦 Cleaning old packages..."
pip uninstall discord.py-selfbot discord.py-self protobuf -y > /dev/null 2>&1
pip cache purge > /dev/null 2>&1
echo "✅ Cleaned"

# 2. Install core build tools
echo "📦 Installing core build tools..."
pip install --no-cache-dir wheel setuptools --upgrade
check_success

# 3. Install protobuf
echo "📦 Installing protobuf..."
pip install --no-cache-dir protobuf==3.20.3
check_success

# 4. Install the CORRECT package from GitHub (THIS IS THE FIX)
echo "📦 Installing discord.py-self from GitHub..."
pip install --no-cache-dir git+https://github.com/dolfies/discord.py-self.git
check_success

# 5. Install remaining packages
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
