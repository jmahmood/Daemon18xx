#!/bin/bash

# Startup script for Daemon18xx Multiplayer Frontend

echo "🎮 Starting Daemon18xx Multiplayer Frontend..."
echo ""

# Check Node.js version
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
echo "✅ Node.js version: $(node --version)"

if [ "$NODE_VERSION" -lt 18 ]; then
    echo "⚠️  Node.js 18+ is recommended. Current version may not work."
fi

# Navigate to frontend directory
cd "$(dirname "$0")/frontend" || exit

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo ""
    echo "📦 Installing dependencies..."
    npm install
fi

# Get local IP address
if command -v hostname &> /dev/null; then
    LOCAL_IP=$(hostname -I | awk '{print $1}')
else
    LOCAL_IP="localhost"
fi

echo ""
echo "✅ Frontend starting on:"
echo "   Local:   http://localhost:5173"
echo "   Network: http://$LOCAL_IP:5173"
echo ""
echo "🎯 Make sure the backend server is running on port 8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the development server
npm run dev
