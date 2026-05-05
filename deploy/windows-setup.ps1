# Windows Server 首次部署脚本
# 在服务器上以管理员身份运行 PowerShell 执行此脚本

param(
    [string]$DeployPath = "C:\inetpub\wwwroot\tikTokVideoExtraction"
)

Write-Host "=== 初始化部署环境 ===" -ForegroundColor Green

# 创建目录
Write-Host "创建部署目录..."
New-Item -ItemType Directory -Force -Path $DeployPath
New-Item -ItemType Directory -Force -Path "$DeployPath\downloads"
New-Item -ItemType Directory -Force -Path "$DeployPath\static"
New-Item -ItemType Directory -Force -Path "$DeployPath\logs"

# 检查 Python 是否安装
Write-Host "检查 Python 环境..."
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "请先安装 Python 3.10+" -ForegroundColor Red
    Write-Host "下载地址: https://www.python.org/downloads/"
    exit 1
}

# 安装依赖
Write-Host "安装 Python 依赖..."
cd $DeployPath
pip install -r requirements.txt
pip install waitress

# 配置防火墙开放端口
Write-Host "配置防火墙规则..."
$rule = Get-NetFirewallRule -DisplayName "TikTok Extraction - Port 5000" -ErrorAction SilentlyContinue
if (-not $rule) {
    New-NetFirewallRule -DisplayName "TikTok Extraction - Port 5000" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
    Write-Host "已添加防火墙规则，开放端口 5000" -ForegroundColor Green
} else {
    Write-Host "防火墙规则已存在"
}

Write-Host "=== 初始化完成 ===" -ForegroundColor Green
Write-Host "请将项目文件上传到: $DeployPath"
Write-Host ""
Write-Host "手动启动应用："
Write-Host "  cd $DeployPath"
Write-Host "  python -m waitress --host=0.0.0.0 --port=5000 app:app"
Write-Host ""
Write-Host "如需注册为 Windows 服务，请下载 WinSW: https://github.com/winsw/winsw"
