import paramiko
import sys
import time
import os

# SSH credentials from environment variables (never hardcode passwords)
import os

ssh_host = os.getenv("SERVER_HOST", "123.56.84.160")
ssh_user = os.getenv("SERVER_USER", "root")
ssh_password = os.getenv("SERVER_PASSWORD", "")

if not ssh_password:
    print("ERROR: SERVER_PASSWORD environment variable not set")
    print("Usage: export SERVER_PASSWORD='your_password' && python upload_all.py")
    sys.exit(1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(ssh_host, username=ssh_user, password=ssh_password, timeout=30)

sftp = ssh.open_sftp()

# Upload frontend
sftp.put(r"D:\Claude Code\study-main\study-main\frontend\index.html", "/opt/zhilian-campus/frontend/index.html")
print("Frontend uploaded")

# Upload backend files
files = [
    (r"D:\Claude Code\study-main\study-main\backend\main.py", "/opt/zhilian-campus/backend/main.py"),
    (r"D:\Claude Code\study-main\study-main\backend\agents\schemas.py", "/opt/zhilian-campus/backend/agents/schemas.py"),
    (r"D:\Claude Code\study-main\study-main\backend\agents\base_agent.py", "/opt/zhilian-campus/backend/agents/base_agent.py"),
    (r"D:\Claude Code\study-main\study-main\backend\agents\general_agent.py", "/opt/zhilian-campus/backend/agents/general_agent.py"),
    (r"D:\Claude Code\study-main\study-main\backend\agents\academic_agent.py", "/opt/zhilian-campus/backend/agents/academic_agent.py"),
    (r"D:\Claude Code\study-main\study-main\backend\agents\affairs_agent.py", "/opt/zhilian-campus/backend/agents/affairs_agent.py"),
    (r"D:\Claude Code\study-main\study-main\backend\agents\growth_agent.py", "/opt/zhilian-campus/backend/agents/growth_agent.py"),
    (r"D:\Claude Code\study-main\study-main\backend\agents\orchestrator.py", "/opt/zhilian-campus/backend/agents/orchestrator.py"),
    (r"D:\Claude Code\study-main\study-main\backend\services\agent_engine.py", "/opt/zhilian-campus/backend/services/agent_engine.py"),
    (r"D:\Claude Code\study-main\study-main\backend\services\ai_service.py", "/opt/zhilian-campus/backend/services/ai_service.py"),
]
for local, remote in files:
    sftp.put(local, remote)
    print(f"Uploaded: {remote}")

sftp.close()

# Kill old gunicorn and restart
cmd = "pkill -f 'gunicorn main:app' 2>/dev/null; sleep 1; cd /opt/zhilian-campus/backend && nohup /opt/miniconda3/bin/python3.13 /opt/miniconda3/bin/gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000 --timeout 120 --daemon 2>&1 && echo STARTED"
stdin, stdout, stderr = ssh.exec_command(cmd)
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
print(f"Restart: {out} {err}")

time.sleep(3)

# Verify
stdin, stdout, stderr = ssh.exec_command("ps aux | grep gunicorn | grep -v grep | wc -l")
count = stdout.read().decode().strip()
print(f"Gunicorn processes: {count}")

ssh.close()
print("All done!")
