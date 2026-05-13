import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('123.56.84.160', username='root', password='lsjhappy123..', timeout=30)

# Kill old gunicorn
stdin, stdout, stderr = ssh.exec_command("pkill -f 'gunicorn main:app' 2>/dev/null; echo KILLED")
print(stdout.read().decode().strip())
time.sleep(1)

# Start gunicorn with full path and cd
cmd = "cd /opt/zhilian-campus/backend && nohup /opt/miniconda3/bin/python3.13 /opt/miniconda3/bin/gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000 --timeout 120 --daemon 2>&1 && echo STARTED"
stdin, stdout, stderr = ssh.exec_command(cmd)
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
print(f"Start: {out} {err}")
time.sleep(3)

# Verify
stdin, stdout, stderr = ssh.exec_command("ps aux | grep gunicorn | grep -v grep")
out = stdout.read().decode().strip()
if out:
    lines = out.split('\n')
    print(f"Gunicorn running: {len(lines)} processes")
    for line in lines[:3]:
        print(f"  {line[:100]}...")
else:
    print("Gunicorn NOT running!")
    # Check logs
    stdin, stdout, stderr = ssh.exec_command("cat /tmp/gunicorn.log 2>/dev/null || echo NO LOG")
    print(stdout.read().decode()[:500])

ssh.close()
