import os
import subprocess
import time

def kill_port_8000():
    print("🔍 Checking for process on port 8000...")
    try:
        # Find PID using netstat
        cmd = "netstat -ano | findstr :8000"
        try:
            result = subprocess.check_output(cmd, shell=True).decode()
        except subprocess.CalledProcessError:
            print("✅ Port 8000 is found free (no netstat result).")
            return

        lines = result.strip().split('\n')
        pids = set()
        for line in lines:
            if "LISTENING" in line or "TIME_WAIT" in line:
                parts = line.strip().split()
                pid = parts[-1]
                if pid != "0":
                    pids.add(pid)
        
        if not pids:
            print("✅ Port 8000 is free.")
            return

        for pid in pids:
            print(f"⚠️ Killing process PID: {pid}")
            os.system(f"taskkill /F /PID {pid}")
            
        print("✅ Port 8000 cleaned.")
        time.sleep(2)
        
    except Exception as e:
        print(f"❌ Error cleaning port: {e}")

if __name__ == "__main__":
    kill_port_8000()
