# This is a 'Muscle Memory' script. 
# It runs locally and costs $0 in tokens.

def run(data):
    """The Cerebellum executes this reflex."""
    print(f"[REFLEX ACTION]: Logged event '{data}' to security_log.txt")
    with open("security_log.txt", "a") as f:
        f.write(f"{time.ctime()}: {data}\n")
    return "Reflex Complete."