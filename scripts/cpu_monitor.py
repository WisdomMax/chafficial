#!/usr/bin/env python3
import time
import subprocess
import re

samples = []
print("Starting CPU monitoring (10 samples, 1s interval)...")
for i in range(10):
    res = subprocess.run(["top", "-l", "1"], capture_output=True, text=True)
    match = re.search(r"CPU usage:\s+([\d\.]+)%\s+user,\s+([\d\.]+)%\s+sys,\s+([\d\.]+)%\s+idle", res.stdout)
    if match:
        user = float(match.group(1))
        sys_cpu = float(match.group(2))
        idle = float(match.group(3))
        total_used = user + sys_cpu
        samples.append((user, sys_cpu, idle, total_used))
        print(f"Sample {i+1:02d}: User={user:5.1f}%, Sys={sys_cpu:5.1f}%, Idle={idle:5.1f}% | Total Used={total_used:5.1f}% (Under 70%: {total_used < 70.0})")
    time.sleep(1)

avg_used = sum(s[3] for s in samples) / len(samples)
max_used = max(s[3] for s in samples)
min_idle = min(s[2] for s in samples)

print(f"\n[CPU AUDIT SUMMARY]")
print(f"- Average CPU Used: {avg_used:.2f}%")
print(f"- Peak CPU Used: {max_used:.2f}% (Limit: 70.0%)")
print(f"- Minimum CPU Idle: {min_idle:.2f}%")
print(f"- 70% Limit Strictly Respected: {max_used < 70.0}")
