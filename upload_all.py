import paramiko
import sys
import time
import os

# SSH credentials from environment variables (never hardcode passwords)
ssh_host = os.getenv("SERVER_HOST", "123.56.84.160")
ssh_user = os.getenv("SERVER_USER", "root")
ssh_password = os.getenv("SERVER_PASSWORD", "")

if not ssh_password:
    print("ERROR: SERVER_PASSWORD environment variable not set")
    print("Usage: $env:SERVER_PASSWORD='your_password' ; python upload_all.py  (PowerShell)")
    print("Usage: export SERVER_PASSWORD='your_password' && python upload_all.py  (bash)")
    sys.exit(1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(ssh_host, username=ssh_user, password=ssh_password, timeout=30)

sftp = ssh.open_sftp()

BASE = r"D:\Claude Code\study-main\study-main"
REMOTE_BASE = "/var/www/zhixiaotong"

print("=== Uploading Backend ===")

# Core backend files
backend_files = [
    ("backend/main.py", "backend/main.py"),
    ("backend/config.py", "backend/config.py"),
    ("backend/services/agent_engine.py", "backend/services/agent_engine.py"),
    ("backend/services/kb_service.py", "backend/services/kb_service.py"),
    ("backend/services/ai_service.py", "backend/services/ai_service.py"),
    ("backend/services/vector_store.py", "backend/services/vector_store.py"),
    ("backend/services/bm25.py", "backend/services/bm25.py"),
    ("backend/services/rag_chain.py", "backend/services/rag_chain.py"),
    ("backend/scripts/seed_kb.py", "backend/scripts/seed_kb.py"),
]

# Agent files
agent_files = [
    "base_agent.py", "schemas.py", "general_agent.py",
    "academic_agent.py", "affairs_agent.py", "growth_agent.py",
    "orchestrator.py",
]
for f in agent_files:
    backend_files.append((f"backend/agents/{f}", f"backend/agents/{f}"))

for local_path, remote_path in backend_files:
    full_local = os.path.join(BASE, local_path)
    full_remote = os.path.join(REMOTE_BASE, remote_path)
    # Ensure remote directory exists
    remote_dir = os.path.dirname(full_remote)
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        # Create directories recursively
        parts = remote_dir.split("/")
        current = ""
        for part in parts:
            if part:
                current += f"/{part}"
                try:
                    sftp.stat(current)
                except FileNotFoundError:
                    sftp.mkdir(current)
    sftp.put(full_local, full_remote)
    print(f"  Uploaded: {remote_path}")

print("=== Uploading Frontend ===")

# Check if Vue3 dist exists
vue_dist = os.path.join(BASE, "frontend-vue", "dist")
if os.path.exists(vue_dist):
    print("  Using pre-built Vue3 dist/")
    # Upload dist files recursively
    for root, dirs, files in os.walk(vue_dist):
        for fname in files:
            local_file = os.path.join(root, fname)
            rel_path = os.path.relpath(local_file, vue_dist)
            remote_file = os.path.join(REMOTE_BASE, "frontend", rel_path).replace("\\", "/")
            remote_dir = os.path.dirname(remote_file)
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                parts = remote_dir.split("/")
                current = ""
                for part in parts:
                    if part:
                        current += f"/{part}"
                        try:
                            sftp.stat(current)
                        except FileNotFoundError:
                            sftp.mkdir(current)
            sftp.put(local_file, remote_file)
    print("  Uploaded Vue3 dist")
else:
    # Fall back to old frontend
    print("  No Vue3 dist found, uploading frontend/index.html")
    sftp.put(os.path.join(BASE, "frontend", "index.html"),
             os.path.join(REMOTE_BASE, "frontend", "index.html"))

sftp.close()

# Restart service using systemctl (matches deploy.sh)
print("=== Restarting Service ===")
cmd = "systemctl restart zhixiaotong"
stdin, stdout, stderr = ssh.exec_command(cmd)
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
if err:
    print(f"  Restart output: {err}")
else:
    print(f"  Service restarted")

time.sleep(3)

# Verify
stdin, stdout, stderr = ssh.exec_command("systemctl is-active zhixiaotong")
status = stdout.read().decode().strip()
print(f"  Service status: {status}")

stdin, stdout, stderr = ssh.exec_command("curl -sf http://127.0.0.1:5000/api/health || echo 'HEALTH_CHECK_FAILED'")
health = stdout.read().decode().strip()
print(f"  Health check: {health}")

ssh.close()
print("=== Deploy Complete ===")
