# 抖音视频下载器

一个简单的抖音视频下载工具，可以从分享链接解析并下载无水印视频。

## 功能特点

- 支持解析抖音分享链接
- 自动获取无水印视频
- 显示下载进度
- 支持批量下载

## 安装

1. 确保已安装 Python 3.7+

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

### 方式一：交互式运行

```bash
python douyin_downloader.py
```

运行后，粘贴抖音分享链接即可下载。

### 方式二：代码调用

```python
from douyin_downloader import DouyinDownloader

downloader = DouyinDownloader(save_dir="./my_videos")

# 分享文本示例
share_text = """5.33 复制打开抖音，看看【嘉靖学长-只讲干货的作品】高三最后100天... https://v.douyin.com/I_fDIXwXg98/"""

# 下载视频
filepath = downloader.download(share_text)
print(f"视频已保存到: {filepath}")
```

## 获取分享链接

1. 打开抖音APP
2. 找到想下载的视频
3. 点击右侧"分享"按钮
4. 选择"复制链接"
5. 粘贴使用

## 注意事项

- 本工具仅供学习交流使用
- 请勿用于商业用途
- 尊重原创者的版权

## 常见问题

### 下载失败？

1. 检查网络连接
2. 确认分享链接格式正确
3. 视频可能已被删除或设为私密

### 视频有水印？

程序会尝试获取无水印版本，但部分视频可能无法去除水印。

## 项目结构

```
douyinVideo/
├── douyin_downloader.py  # 主程序
├── requirements.txt      # 依赖文件
├── README.md            # 说明文档
└── downloads/           # 下载目录（自动创建）
```
