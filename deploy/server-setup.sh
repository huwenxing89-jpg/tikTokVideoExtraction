#!/bin/bash
# 腾讯云轻量应用服务器 - 初始化部署脚本
# 在服务器上运行此脚本进行首次部署配置

set -e

DEPLOY_DIR="/opt/tiktok-video-extraction"

echo "=== 初始化部署环境 ==="

# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Python 和 pip
sudo apt install -y python3 python3-pip python3-venv

# 创建部署目录
sudo mkdir -p $DEPLOY_DIR
sudo mkdir -p $DEPLOY_DIR/downloads
sudo mkdir -p $DEPLOY_DIR/static

# 安装 gunicorn（生产服务器）
pip3 install gunicorn --break-system-packages || pip3 install gunicorn

# 安装 systemd 服务
sudo cp tiktok-extraction.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tiktok-extraction

echo "=== 初始化完成 ==="
echo "请将项目文件上传到 $DEPLOY_DIR 目录"
echo "然后运行: sudo systemctl start tiktok-extraction"
