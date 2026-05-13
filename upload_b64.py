import urllib.request
import json
import sys

# Read the HTML file
with open(r"D:\Claude Code\study-main\study-main\frontend\index.html", "rb") as f:
    content = f.read().decode("utf-8")

# First, deploy the upload endpoint to the server via SSH command
# Then use it to upload the file

# Step 1: Upload the file in chunks via the existing /api/agent/chat endpoint
# Actually we don't have a file upload endpoint yet

# Let's use a different approach: write the content as base64 via multiple SSH calls
import base64
b64_content = base64.b64encode(content.encode("utf-8")).decode("ascii")

# Split into chunks
chunk_size = 4000
chunks = [b64_content[i:i+chunk_size] for i in range(0, len(b64_content), chunk_size)]

print(f"Total chunks: {len(chunks)}")

# Write chunks to a temp file on the server using a single SSH connection
# with a Python one-liner to write the base64 file
import subprocess

# Create the base64 file on server first, then decode
for i, chunk in enumerate(chunks):
    escaped_chunk = chunk.replace("'", "'\\''")
    cmd = f"printf '{escaped_chunk}' >> /tmp/index_b64.txt"
    if i == 0:
        cmd = f"printf '{escaped_chunk}' > /tmp/index_b64.txt"

    proc = subprocess.Popen(
        ["ssh", "-o", "StrictHostKeyChecking=no", "root@123.56.84.160", cmd],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**__import__("os").environ, "SSH_ASKPASS_REQUIRE": "force", "DISPLAY": ":0", "SSH_ASKPASS": r"C:\Users\lsj\.ssh\askpass.cmd"}
    )
    proc.communicate()
    if proc.returncode != 0:
        print(f"Chunk {i} failed!")
        break
    if (i + 1) % 3 == 0:
        print(f"Uploaded chunk {i+1}/{len(chunks)}")

# Now decode on server
proc = subprocess.Popen(
    ["ssh", "-o", "StrictHostKeyChecking=no", "root@123.56.84.160",
     "base64 -d /tmp/index_b64.txt > /opt/zhilian-campus/frontend/index.html && echo DECODE_OK && wc -l /opt/zhilian-campus/frontend/index.html"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env={**__import__("os").environ, "SSH_ASKPASS_REQUIRE": "force", "DISPLAY": ":0", "SSH_ASKPASS": r"C:\Users\lsj\.ssh\askpass.cmd"}
)
out, err = proc.communicate()
print(out.decode())
if proc.returncode != 0:
    print(f"Error: {err.decode()}")
