#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频下载器 - Web版
提供网页界面，输入链接后提取视频并支持下载
"""

import os
import re
import json
import requests
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app)

# 配置
BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
STATIC_DIR = BASE_DIR / "static"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)


class DouyinParser:
    """抖音视频解析器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

    def extract_share_url(self, share_text: str) -> str:
        """从分享文本中提取URL"""
        patterns = [
            r'https?://v\.douyin\.com/[A-Za-z0-9_-]+/?',
            r'https?://vm\.douyin\.com/[A-Za-z0-9_-]+/?',
            r'https?://www\.douyin\.com/[^\s]+',
        ]
        for pattern in patterns:
            match = re.search(pattern, share_text)
            if match:
                return match.group(0)
        raise ValueError("无法从分享文本中提取有效的抖音链接")

    def get_video_id(self, url: str) -> tuple:
        """从URL中提取视频ID和类型"""
        # 检查是否是图文作品
        match = re.search(r'/note/(\d+)', url)
        if match:
            return match.group(1), 'note'

        # 检查是否是视频
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1), 'video'

        # 检查modal_id参数
        match = re.search(r'modal_id=(\d+)', url)
        if match:
            return match.group(1), 'video'

        return None, None

    def get_redirect_url(self, short_url: str) -> str:
        """获取短链接重定向后的真实URL"""
        try:
            response = requests.get(short_url, headers=self.headers, allow_redirects=False, timeout=10)
            if response.status_code in (301, 302, 303, 307, 308):
                return response.headers.get('Location', short_url)
            return response.url
        except:
            return short_url

    def get_video_info(self, video_id: str, content_type: str = 'video') -> dict:
        """获取视频/图文信息"""
        # 方法1: 尝试使用抖音主站API获取完整数据（包含多清晰度）
        try:
            api_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={video_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': f'https://www.douyin.com/video/{video_id}',
                'Accept': 'application/json',
            }
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('aweme_detail'):
                    return self._extract_video_info(data['aweme_detail'])
        except Exception as e:
            print(f"主站API获取失败: {e}")

        # 方法2: 从分享页面解析（备用）
        # 根据类型选择不同的URL
        if content_type == 'note':
            share_url = f"https://www.iesdouyin.com/share/note/{video_id}/"
        else:
            share_url = f"https://www.iesdouyin.com/share/video/{video_id}/"

        try:
            response = requests.get(share_url, headers=self.headers, timeout=10)
            html = response.text

            # 从页面中提取视频信息
            idx = html.find('_ROUTER_DATA')
            if idx != -1:
                json_start = html.find('{', idx)
                if json_start != -1:
                    brace_count = 0
                    json_end = json_start
                    for i in range(json_start, len(html)):
                        if html[i] == '{':
                            brace_count += 1
                        elif html[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break

                    json_str = html[json_start:json_end]
                    data = json.loads(json_str)
                    return self._parse_page_data(data, content_type)

            raise ValueError("无法解析页面数据")
        except Exception as e:
            raise ValueError(f"获取信息失败: {e}")

    def _parse_page_data(self, data: dict, content_type: str = 'video') -> dict:
        """解析页面数据"""
        loader_data = data.get('loaderData', {})

        # 根据类型查找不同的key
        if content_type == 'note':
            target_key = 'note_(id)/page'
        else:
            target_key = 'video_(id)/page'

        for key in loader_data:
            if target_key in key or key == target_key:
                page_data = loader_data[key]
                video_info_res = page_data.get('videoInfoRes', {})
                item_list = video_info_res.get('item_list', [])
                if item_list:
                    return self._extract_video_info(item_list[0])

        raise ValueError("无法从页面数据中提取信息")

    def _extract_video_info(self, item: dict) -> dict:
        """提取视频/图文关键信息"""
        # 获取视频URL - 尝试获取最高清晰度
        video = item.get('video', {})

        # 收集所有可用的视频地址
        video_urls = {}

        # 检查所有可能的视频地址字段
        addr_fields = [
            ('download_addr', 'download'),
            ('play_addr', 'play'),
            ('play_addr_265', 'h265'),
            ('play_addr_h264', 'h264'),
            ('play_addr_264', 'h264_2'),
            ('origin_addr', 'origin'),
        ]

        for field, quality_name in addr_fields:
            addr = video.get(field, {})
            if addr and isinstance(addr, dict):
                url_list = addr.get('url_list', [])
                if url_list:
                    video_urls[quality_name] = url_list[0]

        # 选择最佳视频URL
        # 优先级：origin > download > h265 > h264 > play
        video_url = None
        video_quality = None

        for quality in ['origin', 'download', 'h265', 'h264', 'h264_2', 'play']:
            if quality in video_urls:
                video_url = video_urls[quality]
                video_quality = quality
                break

        # 处理视频URL，尝试获取最高清晰度
        if video_url:
            # 替换为无水印版本
            video_url = video_url.replace('playwm', 'play')
            # 尝试获取更高清晰度：修改 ratio 参数
            if 'ratio=' in video_url:
                video_url = re.sub(r'ratio=[^&]+', 'ratio=origin', video_url)

        # 同样处理所有视频URL（用于调试显示）
        for quality in video_urls:
            url = video_urls[quality]
            url = url.replace('playwm', 'play')
            if 'ratio=' in url:
                url = re.sub(r'ratio=[^&]+', 'ratio=origin', url)
            video_urls[quality] = url

        # 构造多清晰度选项（基于ratio参数）
        # 注意：抖音服务器只接受特定的ratio值，根据视频源质量不同，可用值也不同
        # 常见有效值：1080p, 720p（部分视频可能只支持特定清晰度）
        quality_options = []
        if video_url and 'video_id=' in video_url:
            # 保留原始URL的所有参数，只修改ratio
            # 添加"自动"选项，使用原始URL（不指定ratio，让服务器自动选择）
            quality_options = [
                {'name': '自动 (推荐)', 'ratio': 'auto', 'url': video_url},
                {'name': '1080p', 'ratio': '1080p', 'url': re.sub(r'ratio=[^&]+', 'ratio=1080p', video_url)},
                {'name': '720p', 'ratio': '720p', 'url': re.sub(r'ratio=[^&]+', 'ratio=720p', video_url)},
            ]
            # 默认使用原始URL（自动），确保视频能播放
            # video_url 保持不变

        # 获取封面
        cover = video.get('cover', {})
        cover_url_list = cover.get('url_list', [])
        cover_url = cover_url_list[0] if cover_url_list else None

        # 获取标题和作者
        desc = item.get('desc', '')
        author = item.get('author', {}).get('nickname', '未知作者')
        author_avatar = item.get('author', {}).get('avatar_thumb', {}).get('url_list', [''])[0]

        # 获取统计数据
        statistics = item.get('statistics', {})

        # 获取图片列表（图文作品）- 尝试获取原图
        images = item.get('images', [])
        image_urls = []
        if images:
            for img in images:
                # 优先获取原图：url_list 通常是降序排列，第一个通常是最高清晰度
                url_list = img.get('url_list', [])
                if url_list:
                    # 优先选择包含 original/poster 的URL，否则取第一个
                    img_url = url_list[0]
                    for url in url_list:
                        # 原图标识
                        if any(keyword in url.lower() for keyword in ['origin', 'poster', 'large', '1080']):
                            img_url = url
                            break
                    image_urls.append(img_url)

        # 判断内容类型
        content_type = 'images' if images else 'video'

        # 获取视频分辨率信息
        video_width = video.get('width', 0)
        video_height = video.get('height', 0)

        return {
            'video_url': video_url,
            'video_quality': video_quality,
            'all_video_urls': video_urls,  # 返回所有可用的视频URL
            'quality_options': quality_options,  # 返回多清晰度选项
            'cover_url': cover_url,
            'title': desc,
            'author': author,
            'author_avatar': author_avatar,
            'like_count': statistics.get('digg_count', 0),
            'comment_count': statistics.get('comment_count', 0),
            'share_count': statistics.get('share_count', 0),
            'play_count': statistics.get('play_count', 0),
            'duration': video.get('duration', 0) // 1000,  # 转换为秒
            'content_type': content_type,
            'images': image_urls,
            'image_count': len(image_urls),
            'video_width': video_width,
            'video_height': video_height,
        }

    def parse(self, share_text: str) -> dict:
        """解析分享链接，返回视频/图文信息"""
        # 提取URL
        share_url = self.extract_share_url(share_text)

        # 获取重定向URL
        real_url = self.get_redirect_url(share_url)

        # 获取视频ID和类型
        video_id, content_type = self.get_video_id(real_url)
        if not video_id:
            # 尝试从重定向URL中获取
            real_url = self.get_redirect_url(share_url)
            video_id, content_type = self.get_video_id(real_url)

        if not video_id:
            raise ValueError("无法获取ID，链接可能已过期")

        # 获取视频/图文信息
        return self.get_video_info(video_id, content_type)
        return self.get_video_info(video_id)


# 创建解析器实例
parser = DouyinParser()


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/parse', methods=['POST'])
def parse_video():
    """解析视频API"""
    try:
        data = request.get_json()
        share_text = data.get('url', '').strip()

        if not share_text:
            return jsonify({'success': False, 'message': '请输入分享链接'})

        video_info = parser.parse(share_text)

        return jsonify({
            'success': True,
            'data': video_info
        })

    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)})
    except Exception as e:
        return jsonify({'success': False, 'message': f'解析失败: {str(e)}'})


@app.route('/api/check_quality', methods=['POST'])
def check_quality():
    """检测视频清晰度可用性和文件大小"""
    try:
        data = request.get_json()
        urls = data.get('urls', [])

        if not urls:
            return jsonify({'success': False, 'message': 'URL列表为空'})

        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Referer': 'https://www.douyin.com/',
        }

        results = []
        for item in urls:
            url = item.get('url')
            ratio = item.get('ratio')

            try:
                response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    size = int(response.headers.get('Content-Length', 0))
                    results.append({
                        'ratio': ratio,
                        'available': True,
                        'size': size,
                        'size_text': format_file_size(size)
                    })
                else:
                    results.append({
                        'ratio': ratio,
                        'available': False,
                        'size': 0,
                        'size_text': '不可用'
                    })
            except Exception:
                results.append({
                    'ratio': ratio,
                    'available': False,
                    'size': 0,
                    'size_text': '不可用'
                })

        return jsonify({'success': True, 'results': results})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


def format_file_size(size):
    """格式化文件大小"""
    if size >= 1024 * 1024:
        return f'{size / 1024 / 1024:.1f}MB'
    elif size >= 1024:
        return f'{size / 1024:.1f}KB'
    return f'{size}B'


@app.route('/api/download', methods=['POST'])
def download_video():
    """下载视频API"""
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        title = data.get('title', 'douyin_video')

        if not video_url:
            return jsonify({'success': False, 'message': '视频地址无效'})

        # 清理文件名
        safe_title = re.sub(r'[<>:"/\\|?*\r\n]', '_', title)
        safe_title = safe_title[:100]
        filename = f"{safe_title}.mp4"
        filepath = DOWNLOAD_DIR / filename

        # 下载视频 - 先获取重定向后的真实URL
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Referer': 'https://www.douyin.com/',
        }

        # 先发送请求获取重定向后的URL
        session = requests.Session()
        response = session.get(video_url, headers=headers, stream=True, timeout=60, allow_redirects=True)

        # 检查是否成功
        if response.status_code != 200:
            return jsonify({'success': False, 'message': f'视频获取失败: HTTP {response.status_code}'})

        # 获取文件大小
        total_size = int(response.headers.get('Content-Length', 0))

        with open(filepath, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

        # 检查文件是否下载完整
        if total_size > 0 and downloaded < total_size * 0.9:
            return jsonify({'success': False, 'message': '视频下载不完整，请重试'})

        return jsonify({
            'success': True,
            'message': '下载成功',
            'filename': filename,
            'download_url': f'/api/file/{filename}'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'下载失败: {str(e)}'})


@app.route('/api/file/<filename>')
def download_file(filename):
    """下载文件"""
    try:
        return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/proxy/video')
def proxy_video():
    """代理视频流，用于前端预览和下载"""
    video_url = request.args.get('url')
    if not video_url:
        return "Missing URL", 400

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Referer': 'https://www.douyin.com/',
        }

        # 跟随重定向获取最终的视频
        response = requests.get(video_url, headers=headers, stream=True, timeout=60, allow_redirects=True)

        # 检查是否成功获取视频
        if response.status_code != 200:
            return f"Video fetch failed: {response.status_code}", response.status_code

        content_type = response.headers.get('Content-Type', 'video/mp4')
        content_length = response.headers.get('Content-Length', '')

        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        return app.response_class(
            generate(),
            mimetype=content_type,
            headers={
                'Content-Length': content_length,
                'Accept-Ranges': 'bytes',
                'Cache-Control': 'public, max-age=3600',
            }
        )
    except Exception as e:
        return f"Proxy error: {str(e)}", 500
    except Exception as e:
        return str(e), 500


if __name__ == '__main__':
    print("=" * 50)
    print("抖音视频下载器 - Web版")
    print("=" * 50)
    print(f"下载目录: {DOWNLOAD_DIR}")
    print("访问地址: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
