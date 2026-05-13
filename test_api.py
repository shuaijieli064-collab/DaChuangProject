import paramiko
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('123.56.84.160', username='root', password='lsjhappy123..', timeout=30)

# Test upload with a .txt file
cmd = 'echo "Hello world, this is a test file for knowledge extraction." > /tmp/test_upload.txt && curl -s -X POST http://127.0.0.1:80/api/academic/upload-file -F "file=@/tmp/test_upload.txt"'
stdin, stdout, stderr = ssh.exec_command(cmd)
out = stdout.read().decode('utf-8', errors='replace').strip()
sys.stdout.buffer.write(f"upload-file txt: {out}\n".encode('utf-8'))

# Also test health endpoint
cmd = 'curl -s http://127.0.0.1:80/api/health'
stdin, stdout, stderr = ssh.exec_command(cmd)
out = stdout.read().decode('utf-8', errors='replace').strip()
sys.stdout.buffer.write(f"health: {out}\n".encode('utf-8'))

ssh.close()
