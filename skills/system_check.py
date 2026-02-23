import psutil
import os

def run(data=None):
    """
    Skill: Homeostasis Check
    Purpose: Ensures the local environment is healthy.
    """
    cpu_usage = psutil.cpu_percent()
    disk_usage = psutil.disk_usage('/').percent
    
    status = f"System Health: CPU {cpu_usage}%, Disk {disk_usage}%"
    
    if cpu_usage > 90 or disk_usage > 95:
        print(f"[Cerebellum WARNING]: {status}")
        # Here you could trigger a specific emergency alert
    else:
        print(f"[Cerebellum]: {status} - Normal.")
        
    return status