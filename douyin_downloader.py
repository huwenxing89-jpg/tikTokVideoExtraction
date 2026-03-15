#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频下载器
支持从分享链接解析并下载抖音视频
"""

import re
import os
import json
import requests
from urllib.parse import urlparse, parse_qs
from pathlib import Path


class DouyinDownloader:
    """抖音视频下载器类"""

    def __init__(self, save_dir: str = "./downloads"):
        """
        初始化下载器

        Args:
            save_dir: 视频保存目录
        """
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # 请求头，模拟手机浏览器
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
        }

        # 创建session保持会话
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def extract_share_url(self, share_text: str) -> str:
        """
        从分享文本中提取URL

        Args:
            share_text: 分享文本，如 "5.33 复制打开抖音... https://v.douyin.com/xxx/"

        Returns:
            提取到的URL
        """
        # 匹配抖音短链接 v.douyin.com/xxx (包含下划线、连字符等字符)
        pattern = r'https?://v\.douyin\.com/[A-Za-z0-9_-]+/?'
        match = re.search(pattern, share_text)
        if match:
            return match.group(0)

        # 匹配 www.douyin.com 链接
        pattern = r'https?://www\.douyin\.com/[^\s]+'
        match = re.search(pattern, share_text)
        if match:
            return match.group(0)

        # 匹配 vm.douyin.com 链接
        pattern = r'https?://vm\.douyin\.com/[A-Za-z0-9_-]+/?'
        match = re.search(pattern, share_text)
        if match:
            return match.group(0)

        raise ValueError("无法从分享文本中提取有效的抖音链接")

    def get_redirect_url(self, short_url: str) -> tuple:
        """
        获取短链接重定向后的真实URL

        Args:
            short_url: 短链接

        Returns:
            (重定向后的真实URL, 所有的重定向历史)
        """
        redirect_history = []

        try:
            # 使用GET请求，不自动跟随重定向，手动处理
            response = self.session.get(short_url, allow_redirects=False, timeout=10)
            redirect_history.append(response.url)

            # 手动跟随重定向
            max_redirects = 10
            for _ in range(max_redirects):
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get('Location', '')
                    if location:
                        # 处理相对URL
                        if location.startswith('/'):
                            parsed = urlparse(short_url)
                            location = f"{parsed.scheme}://{parsed.netloc}{location}"
                        redirect_history.append(location)
                        response = self.session.get(location, allow_redirects=False, timeout=10)
                    else:
                        break
                else:
                    break

            final_url = response.url
            return final_url, redirect_history

        except Exception as e:
            raise ValueError(f"获取重定向URL失败: {e}")

    def get_video_id_from_url(self, url: str) -> str:
        """
        从URL中提取视频ID

        Args:
            url: 视频URL

        Returns:
            视频ID
        """
        # 匹配 /video/xxx 格式
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)

        # 匹配 modal_id 参数
        match = re.search(r'modal_id=(\d+)', url)
        if match:
            return match.group(1)

        # 匹配 /note/xxx 格式（图文）
        match = re.search(r'/note/(\d+)', url)
        if match:
            return match.group(1)

        return None

    def get_video_id_from_redirects(self, redirects: list) -> str:
        """
        从重定向历史中提取视频ID

        Args:
            redirects: 重定向URL列表

        Returns:
            视频ID
        """
        for url in redirects:
            video_id = self.get_video_id_from_url(url)
            if video_id:
                return video_id
        return None

    def get_video_id_from_page(self, url: str) -> str:
        """
        从页面内容中提取视频ID

        Args:
            url: 页面URL

        Returns:
            视频ID
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            }
            response = self.session.get(url, headers=headers, timeout=10)
            html = response.text

            # 尝试从页面中提取视频ID
            patterns = [
                r'"aweme_id"\s*:\s*"(\d+)"',
                r'"video_id"\s*:\s*"(\d+)"',
                r'"itemId"\s*:\s*"(\d+)"',
                r'/video/(\d+)',
                r'modal_id=(\d+)',
            ]

            for pattern in patterns:
                match = re.search(pattern, html)
                if match:
                    return match.group(1)

        except Exception as e:
            print(f"从页面提取视频ID失败: {e}")

        return None

    def get_video_info(self, video_id: str) -> dict:
        """
        获取视频信息

        Args:
            video_id: 视频ID

        Returns:
            视频信息字典
        """
        # 方法1: 尝试 iesdouyin API
        api_url = f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={video_id}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Referer': f'https://www.douyin.com/video/{video_id}',
        }

        try:
            response = self.session.get(api_url, headers=headers, timeout=10)
            if response.text:
                data = response.json()
                if data.get('status_code') == 0 and data.get('item_list'):
                    return data
        except Exception as e:
            print(f"API方式获取失败，尝试页面解析: {e}")

        # 方法2: 从分享页面解析
        share_url = f"https://www.iesdouyin.com/share/video/{video_id}/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'no-cache',
        }

        try:
            # 使用新的session避免headers冲突
            response = requests.get(share_url, headers=headers, timeout=10)
            html = response.text

            # 从页面中提取视频信息
            # 查找 _ROUTER_DATA，使用更灵活的匹配
            idx = html.find('_ROUTER_DATA')
            if idx != -1:
                # 找到JSON开始位置
                json_start = html.find('{', idx)
                if json_start != -1:
                    # 使用括号计数来找到匹配的结束位置
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
                    try:
                        data = json.loads(json_str)
                        return self._parse_page_data(data, html)
                    except json.JSONDecodeError as e:
                        print(f"JSON解析失败: {e}")

            # 直接从页面提取视频URL
            return self._extract_video_from_html(html, video_id)

        except Exception as e:
            raise ValueError(f"获取视频信息失败: {e}")

    def _parse_page_data(self, data: dict, html: str) -> dict:
        """解析页面数据"""
        try:
            # 尝试从 _ROUTER_DATA 结构中提取
            loader_data = data.get('loaderData', {})

            # 优先查找 video_(id)/page 这个key
            for key in loader_data:
                if 'video_(id)/page' in key or key == 'video_(id)/page':
                    page_data = loader_data[key]
                    video_info_res = page_data.get('videoInfoRes', {})
                    item_list = video_info_res.get('item_list', [])
                    if item_list:
                        return {'item_list': item_list, 'status_code': 0}

            # 备用：查找包含 videoInfoRes 的key
            for key in loader_data:
                page_data = loader_data[key]
                if isinstance(page_data, dict) and 'videoInfoRes' in page_data:
                    video_info_res = page_data.get('videoInfoRes', {})
                    item_list = video_info_res.get('item_list', [])
                    if item_list:
                        return {'item_list': item_list, 'status_code': 0}

        except Exception as e:
            print(f"解析页面数据失败: {e}")

        return {'item_list': [], '_raw_html': html}

    def _extract_video_from_html(self, html: str, video_id: str) -> dict:
        """从HTML中直接提取视频信息"""
        # 提取视频播放地址
        video_patterns = [
            r'"playApi"\s*:\s*"([^"]+)"',
            r'"playAddr"\s*:\s*\[?\s*\{\s*"src"\s*:\s*"([^"]+)"',
            r'"video_url"\s*:\s*"([^"]+)"',
            r'playAddr.*?src.*?["\']([^"\']+)["\']',
        ]

        video_url = None
        for pattern in video_patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                video_url = match.group(1)
                # 处理转义字符
                video_url = video_url.replace('\\u002F', '/')
                video_url = video_url.replace('\\/', '/')
                break

        # 提取视频标题
        title_match = re.search(r'"desc"\s*:\s*"([^"]*)"', html)
        title = title_match.group(1) if title_match else f"douyin_{video_id}"

        # 提取作者
        author_match = re.search(r'"nickname"\s*:\s*"([^"]*)"', html)
        author = author_match.group(1) if author_match else "未知作者"

        # 构造返回数据
        return {
            'item_list': [{
                'desc': title,
                'author': {'nickname': author},
                'video': {'play_addr': {'url_list': [video_url]}} if video_url else {},
                '_raw_html': html
            }],
            '_video_url': video_url,
            '_title': f"{author}_{title}"
        }

    def get_video_play_url(self, video_info: dict) -> str:
        """
        从视频信息中提取播放URL

        Args:
            video_info: 视频信息

        Returns:
            视频播放URL
        """
        # 如果有直接提取的URL
        if video_info.get('_video_url'):
            return video_info['_video_url']

        try:
            item = video_info['item_list'][0]

            # 检查是否有原始HTML
            if item.get('_raw_html'):
                html = item['_raw_html']
                # 尝试从HTML中提取视频URL
                patterns = [
                    r'"src"\s*:\s*"(https?://[^"]*\.mp4[^"]*)"',
                    r'"playAddr"\s*:\s*\[\s*\{\s*"src"\s*:\s*"([^"]+)"',
                    r'video_url["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                ]

                for pattern in patterns:
                    match = re.search(pattern, html, re.DOTALL)
                    if match:
                        url = match.group(1)
                        url = url.replace('\\u002F', '/').replace('\\/', '/')
                        if url.startswith('//'):
                            url = 'https:' + url
                        return url

            # 优先获取无水印视频地址
            video = item.get('video', {})

            # 方法1: 获取 play_addr
            play_addr = video.get('play_addr', {})
            url_list = play_addr.get('url_list', [])
            if url_list:
                video_url = url_list[0]
                video_url = video_url.replace('playwm', 'play')
                return video_url

            # 方法2: 获取 download_addr
            download_addr = video.get('download_addr', {})
            url_list = download_addr.get('url_list', [])
            if url_list:
                return url_list[0]

            # 方法3: 尝试其他字段
            for key in ['play_addr_h264', 'play_addr_265', 'download_addr']:
                addr = video.get(key, {})
                url_list = addr.get('url_list', [])
                if url_list:
                    return url_list[0]

            raise ValueError("无法获取视频播放地址")

        except (KeyError, IndexError) as e:
            raise ValueError(f"解析视频信息失败: {e}")

    def get_video_title(self, video_info: dict) -> str:
        """
        获取视频标题

        Args:
            video_info: 视频信息

        Returns:
            视频标题
        """
        # 如果有直接提取的标题
        if video_info.get('_title'):
            return video_info['_title']

        try:
            item = video_info['item_list'][0]
            desc = item.get('desc', '')
            author = item.get('author', {}).get('nickname', '未知作者')
            return f"{author}_{desc}"[:50]
        except (KeyError, IndexError):
            return "douyin_video"

    def sanitize_filename(self, filename: str) -> str:
        """
        清理文件名中的非法字符

        Args:
            filename: 原始文件名

        Returns:
            清理后的文件名
        """
        illegal_chars = r'[<>:"/\\|?*\r\n]'
        filename = re.sub(illegal_chars, '_', filename)
        filename = filename.strip()
        # 限制文件名长度
        if len(filename) > 100:
            filename = filename[:100]
        return filename

    def download_video(self, video_url: str, filename: str) -> str:
        """
        下载视频

        Args:
            video_url: 视频URL
            filename: 保存的文件名

        Returns:
            保存的文件路径
        """
        filepath = self.save_dir / filename

        # 下载视频
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.douyin.com/',
        }
        response = self.session.get(video_url, headers=headers, stream=True, timeout=60)
        total_size = int(response.headers.get('content-length', 0))

        print(f"正在下载: {filename}")
        if total_size > 0:
            print(f"文件大小: {total_size / 1024 / 1024:.2f} MB")

        with open(filepath, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = downloaded / total_size * 100
                        print(f"\r下载进度: {progress:.1f}%", end='')

        print(f"\n下载完成: {filepath}")
        return str(filepath)

    def download(self, share_text: str) -> str:
        """
        从分享文本下载视频的主函数

        Args:
            share_text: 分享文本

        Returns:
            下载的文件路径
        """
        print("=" * 50)
        print("抖音视频下载器")
        print("=" * 50)

        # 1. 提取URL
        print("\n[1/6] 提取分享链接...")
        share_url = self.extract_share_url(share_text)
        print(f"分享链接: {share_url}")

        # 2. 获取重定向URL
        print("\n[2/6] 解析真实链接...")
        real_url, redirects = self.get_redirect_url(share_url)
        print(f"真实链接: {real_url}")

        # 3. 获取视频ID
        print("\n[3/6] 获取视频ID...")
        video_id = self.get_video_id_from_url(real_url)

        if not video_id:
            video_id = self.get_video_id_from_redirects(redirects)

        if not video_id:
            print("尝试从页面内容提取...")
            video_id = self.get_video_id_from_page(real_url)

        if not video_id:
            raise ValueError("无法获取视频ID，链接可能已过期或无效")

        print(f"视频ID: {video_id}")

        # 4. 获取视频信息
        print("\n[4/6] 获取视频信息...")
        video_info = self.get_video_info(video_id)
        video_url = self.get_video_play_url(video_info)
        video_title = self.get_video_title(video_info)
        print(f"视频标题: {video_title}")

        # 5. 下载视频
        print("\n[5/6] 下载视频...")
        filename = self.sanitize_filename(video_title) + ".mp4"
        filepath = self.download_video(video_url, filename)

        print("\n[6/6] 完成！")
        print("=" * 50)
        print(f"文件保存在: {filepath}")
        print("=" * 50)

        return filepath


def main():
    """主函数"""
    print("抖音视频下载器")
    print("请输入抖音分享链接（输入 q 退出）:")
    print("-" * 50)

    downloader = DouyinDownloader()

    while True:
        try:
            share_text = input("\n分享链接: ").strip()

            if share_text.lower() == 'q':
                print("再见！")
                break

            if not share_text:
                print("请输入有效的分享链接")
                continue

            downloader.download(share_text)

        except KeyboardInterrupt:
            print("\n\n用户取消操作")
            break
        except Exception as e:
            print(f"\n错误: {e}")
            print("请检查链接是否正确后重试")


if __name__ == "__main__":
    main()
