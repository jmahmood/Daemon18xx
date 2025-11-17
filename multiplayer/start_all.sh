#!/bin/bash

# Start both backend and frontend servers in parallel

echo "🚂 Starting Daemon18xx Multiplayer (Backend + Frontend)..."
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend in background
echo "📡 Starting backend server..."
./start_server.sh &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend in background
echo ""
echo "🎮 Starting frontend server..."
./start_client.sh &
FRONTEND_PID=$!

echo ""
echo "✅ Both servers started!"
echo ""
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
