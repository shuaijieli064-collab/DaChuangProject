#!/bin/bash
# 智校通 - 阿里云ECS服务器部署脚本
# 适用于: Alibaba Cloud Linux 3.2104 LTS 64位
# 使用方法: bash deploy.sh

set -e

# 配置
APP_NAME="zhixiaotong"
APP_DIR="/var/www/zhixiaotong"
PYTHON_VERSION="3.10"
DOMAIN="${DOMAIN:-example.com}"
EMAIL="${EMAIL:-admin@example.com}"

echo "=========================================="
echo "智校通 - 阿里云服务器部署脚本"
echo "系统: Alibaba Cloud Linux 3.2104 LTS"
echo "=========================================="

# 1. 更新系统
echo "[1/8] 更新系统..."
dnf update -y

# 2. 安装Python和依赖
echo "[2/8] 安装Python环境..."
dnf install -y python3 python3-pip python3-venv

# 3. 安装 Nginx 和 Certbot
echo "[3/8] 安装Nginx和SSL证书工具..."
dnf install -y nginx certbot python3-certbot-nginx

# 4. 创建应用目录
echo "[4/9] 创建应用目录..."
mkdir -p $APP_DIR
cp -r backend data $APP_DIR/ 2>/dev/null || true

# 构建前端（如果本地有 Node.js）
if command -v node &> /dev/null && [ -d "frontend-vue" ]; then
    echo "构建 Vue3 前端..."
    cd frontend-vue
    npm ci 2>/dev/null || npm install
    npm run build
    cd ..
    cp -r frontend-vue/dist $APP_DIR/frontend 2>/dev/null || true
else
    echo "未检测到 Node.js 或 frontend-vue 目录，使用已有 frontend 目录"
    cp -r frontend $APP_DIR/ 2>/dev/null || true
fi

# 5. 创建虚拟环境
echo "[5/9] 创建虚拟环境..."
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# 6. 配置环境变量
echo "[6/9] 配置环境变量..."
if [ -z "$AI_API_KEY" ]; then
    echo "ERROR: AI_API_KEY environment variable is not set"
    echo "Usage: export AI_API_KEY='your_key' && bash deploy.sh"
    exit 1
fi
cat > $APP_DIR/.env << 'EOF'
AI_API_KEY=${AI_API_KEY}
AI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_MODEL=qwen-plus
AI_TIMEOUT_SECONDS=120
DEBUG=false
EOF

# 7. 配置systemd服务
echo "[7/9] 配置系统服务..."
cat > /etc/systemd/system/zhixiaotong.service << EOF
[Unit]
Description=Zhixiaotong Flask App
After=network.target

[Service]
User=nginx
Group=nginx
WorkingDirectory=$APP_DIR/backend
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port 5000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 8. 配置Nginx
echo "[8/9] 配置Nginx..."
cat > /etc/nginx/conf.d/zhixiaotong.conf << EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 16M;

    location / {
        root $APP_DIR/frontend;
        try_files \$uri \$uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }

    location /ws {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400;
    }
}
EOF

# 9. 健康检查
echo "[9/9] 健康检查..."
sleep 3
if curl -sf http://127.0.0.1:5000/api/health > /dev/null 2>&1; then
    echo "API 服务运行正常"
else
    echo "警告: API 服务可能未正常启动"
    journalctl -u zhixiaotong --no-pager -n 20
fi

# 启动服务
echo ""
echo "启动服务..."
systemctl daemon-reload
systemctl enable nginx zhixiaotong
systemctl start nginx
systemctl restart zhixiaotong

# 检查状态
sleep 2
systemctl status zhixiaotong --no-pager

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "访问地址: http://你的服务器IP"
echo ""
echo "后续步骤:"
echo "1. 在阿里云控制台开放端口: 80, 443"
echo "2. 购买域名并配置DNS解析"
echo "3. 启用 HTTPS（需要域名）:"
echo "   certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL"
echo ""
echo "管理命令:"
echo "  查看状态: systemctl status zhixiaotong"
echo "  重启服务: systemctl restart zhixiaotong"
echo "  查看日志: journalctl -u zhixiaotong -f"
echo "=========================================="