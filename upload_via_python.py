"""
通过服务器已有的 Flask API 上传文件到服务器
利用 Flask 的 static_folder 特性：我们不改后端代码，
直接通过 SSH 创建文件（Python 纯实现，无需 sshpass）
"""
import subprocess
import sys

# 方案: 用 plink (PuTTY Link) 或者 sshpass.exe 的 Windows 原生替代
# 先检查是否有 putty 相关的工具
result = subprocess.run(["where", "putty"], capture_output=True, text=True)
if result.returncode == 0:
    print("PuTTY found")
else:
    print("No PuTTY, trying psftp...")
    result = subprocess.run(["where", "psftp"], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Found psftp: {result.stdout.strip()}")
    else:
        print("No psftp either. Checking for mscp...")

# 最后尝试: 用 PowerShell 的 SSH 交互
# Windows 10+ 的 OpenSSH 可以用 ssh + 密码文件
print("\nTrying interactive SSH via subprocess...")

proc = subprocess.Popen(
    ["ssh", "-o", "StrictHostKeyChecking=no", "root@123.56.84.160",
     "cat > /opt/zhilian-campus/frontend/test.txt && echo OK"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# 等待密码提示
import time
time.sleep(2)
proc.stdin.write("lsjhappy123..\n")
proc.stdin.flush()
time.sleep(2)
proc.stdin.write("test content\n")
proc.stdin.close()
out, err = proc.communicate(timeout=10)
print(f"stdout: {out}")
print(f"stderr: {err}")
print(f"returncode: {proc.returncode}")
