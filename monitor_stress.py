import requests
import time
import csv
import datetime

# URL for the metrics endpoint
url = "http://localhost:8000/api/v1/health/stress-metrics"
output_file = "stress_metrics.csv"
duration_sec = 200 # Run for slightly longer than the test (3.5 mins)

print(f"Starting monitoring for {duration_sec} seconds...")

with open(output_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "CPU%", "Memory(MB)", "DB_Active", "DB_Pool_Size", "DB_Overflow"])

    start_time = time.time()
    
    while time.time() - start_time < duration_sec:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                data = response.json()
                sys_res = data.get("system_resources", {})
                db_conn = data.get("db_connections", {})
                
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                cpu = sys_res.get("cpu_percent", 0)
                mem = sys_res.get("memory_rss_mb", 0)
                db_active = db_conn.get("active", 0)
                db_pool = db_conn.get("pool_size", 0)
                db_over = db_conn.get("overflow", 0)
                
                writer.writerow([timestamp, cpu, mem, db_active, db_pool, db_over])
                print(f"{timestamp} | CPU: {cpu}% | RAM: {mem}MB | DB: {db_active}/{db_pool}")
            else:
                print(f"Error: Status {response.status_code}")
        except Exception as e:
            print(f"Monitor Error: {e}")
        
        time.sleep(2) # Poll every 2 seconds

print("Monitoring finished.")
