#!/bin/bash
echo "Starting Launchpad Job Alert System Background Server..."
source venv/bin/activate
nohup python server.py > server.log 2>&1 &
echo "Server started in background! PID: $!"
echo "You can view logs with: tail -f server.log"
echo "To stop the server, run: kill $!"
