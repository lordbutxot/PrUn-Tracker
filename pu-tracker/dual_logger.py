import sys

logfile = sys.argv[1]
with open(logfile, "a", encoding="utf-8") as f:
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        print(line, end='')  # Console
        f.write(line)        # Log file
        f.flush()