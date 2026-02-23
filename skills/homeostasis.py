import psutil
import time

def run(data=None):
    cpu = psutil.cpu_percent()
    print(f"[Cerebellum]: Homeostasis Check - CPU at {cpu}%")
    return cpu