import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('123.56.84.160', username='root', password='lsjhappy123..', timeout=30)

# SFTP upload
sftp = ssh.open_sftp()
local_path = r"D:\Claude Code\study-main\study-main\frontend\index.html"
remote_path = "/opt/zhilian-campus/frontend/index.html"
sftp.put(local_path, remote_path)
sftp.close()
ssh.close()
print("Upload successful via paramiko/SFTP")
