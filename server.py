import time
import schedule
import subprocess
import os
import sys

def run_job():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running Launchpad Job Alert System...")
    try:
        # Run the main script
        result = subprocess.run([sys.executable, "main.py"], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
    except Exception as e:
        print(f"Failed to run main.py: {e}")

def start_server():
    print("Starting Launchpad Background Server...")
    print("Scheduling job to run every 30 minutes.")
    
    # Run once immediately
    run_job()
    
    # Schedule every 30 minutes
    schedule.every(30).minutes.do(run_job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    start_server()
