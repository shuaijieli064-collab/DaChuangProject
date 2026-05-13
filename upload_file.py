import subprocess
import sys

# 用 Python 的 subprocess 调用 ssh，通过 stdin 传递文件内容
# 读取本地文件
with open(r"D:\Claude Code\study-main\study-main\frontend\index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 先注册公钥到服务器（一次性）
import os
pubkey_path = os.path.expanduser(r"~\.ssh\id_ed25519.pub")
if os.path.exists(pubkey_path):
    with open(pubkey_path, "r") as f:
        pubkey = f.read().strip()

# 用 expect 风格的方案不行，改用 sshpass 的纯 Python 替代
# 直接使用 pexpect（如果有的话）
try:
    import pexpect
    child = pexpect.spawn(
        f'ssh -o StrictHostKeyChecking=no root@123.56.84.160 '
        f'"cat > /opt/zhilian-campus/frontend/index.html"',
        encoding='utf-8',
        timeout=30
    )
    child.expect('password:')
    child.sendline('lsjhappy123..')
    child.sendline(content)
    child.sendcontrol('d')  # EOF
    child.expect(pexpect.EOF)
    print("Upload successful via pexpect")
except ImportError:
    print("pexpect not available, trying another method...")

    # 方法2: 用 paramiko（如果 cryptography 可用）
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('123.56.84.160', username='root', password='lsjhappy123..')

        # SFTP 上传
        sftp = ssh.open_sftp()
        # 先读再写，确保目录存在
        sftp.put(r"D:\Claude Code\study-main\study-main\frontend\index.html",
                 "/opt/zhilian-campus/frontend/index.html")
        sftp.close()
        ssh.close()
        print("Upload successful via paramiko/SFTP")
    except Exception as e:
        print(f"paramiko failed: {e}")

        # 方法3: 用 HTTP 上传到临时端点
        import urllib.request
        import json

        payload = json.dumps({
            "filepath": "/opt/zhilian-campus/frontend/index.html",
            "content": content
        }).encode('utf-8')

        req = urllib.request.Request(
            "http://123.56.84.160/api/admin/upload",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Upload-Secret": "zhilian2026"
            },
            method="POST"
        )

        try:
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read().decode())
            print(f"Upload successful via HTTP: {result}")
        except Exception as e:
            print(f"HTTP upload also failed: {e}")
            print("Please manually upload via SSH or Git Bash")
