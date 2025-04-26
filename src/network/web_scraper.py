import requests
from PyQt6.QtCore import pyqtSignal
import time
import random
# 不再需要 BeautifulSoup for get_english_game_name
# from bs4 import BeautifulSoup 
import urllib.parse
import os
import sys
import hashlib
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# 确保 playwright 可用
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError as e:
    print(f"无法导入 playwright: {e}")
    # 如果在打包环境中，尝试从其他位置导入
    if getattr(sys, 'frozen', False):
        print("正在打包环境中尝试导入 playwright...")
        try:
            # 添加所有可能的路径
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            possible_paths = [
                os.path.join(base_dir, "site-packages"),
                os.path.join(base_dir, "Lib", "site-packages"),
                base_dir,
                os.path.dirname(sys.executable)
            ]
            for path in possible_paths:
                if path not in sys.path and os.path.exists(path):
                    sys.path.append(path)
                    print(f"添加路径到 sys.path: {path}")
            
            from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
            print("成功从打包环境导入 playwright")
        except ImportError as e2:
            print(f"从打包环境导入 playwright 失败: {e2}")
            print("sys.path:", sys.path)
            raise

class WebScraper:
    def __init__(self):
        self.base_url = "https://flingtrainer.com"
        self.baidu_url = "https://www.baidu.com"
        self.headers = {
            # 保留这个headers给其他非playwright的请求
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # 创建线程池用于并行请求
        self.executor = ThreadPoolExecutor(max_workers=3)
        
    def search_game(self, game_name):
        """
        搜索游戏 - 直接从服务器获取最新内容
        """
        encoded_game_name = urllib.parse.quote(game_name)
        url = f"{self.base_url}/?s={encoded_game_name}"
        
        # 直接发送请求
        content = self._make_request(url, timeout=10)  # 减少超时时间
        return content
        
    def get_trainer_page(self, url):
        """
        使用Playwright获取修改器页面内容
        这样可以确保动态内容（如自动更新版本EXE）被正确抓取
        """
        print(f"使用Playwright抓取修改器页面: {url}")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # 优化: 禁用图片和样式以加快加载速度
                page.route('**/*.{png,jpg,jpeg,gif,css}', lambda route: route.abort())
                
                # 增加User-Agent模拟真实浏览器
                page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
                })
                
                # 导航到目标页面，减少超时
                page.goto(url, timeout=15000)  # 减少到15秒
                
                # 等待页面加载完成（等待下载区域出现）
                try:
                    page.wait_for_selector("div.download-attachments", timeout=5000)  # 减少到5秒
                except PlaywrightTimeoutError:
                    print("等待下载区域超时，尝试继续获取内容")
                
                # 获取页面内容
                html_content = page.content()
                
                # 关闭浏览器
                browser.close()
                
                return html_content
        except Exception as e:
            print(f"使用Playwright抓取页面时出错: {e}")
            # 出错时回退到旧方法
            print(f"回退到requests方法抓取页面")
            content = self._make_request(url, timeout=10)
            return content
    
    def get_english_game_name(self, chinese_name, progress_callback=None):
        """
        获取游戏的英文名称。
        
        Args:
            chinese_name: 中文游戏名
            progress_callback: 可选的回调函数，用于报告翻译进度
        
        Returns:
            英文游戏名称，如果找不到则返回 None
        """
        query = f"{chinese_name} 的英文游戏名称"
        encoded_query = urllib.parse.quote(query)
        search_url = f"{self.baidu_url}/s?wd={encoded_query}"
        # 目标元素的CSS选择器
        selector = "div.cosd-markdown-content h2 mark.flexible-marker.flexible-marker-default"
        
        english_name = None
        
        if progress_callback:
            progress_callback(f"正在查询 \"{chinese_name}\" 的英文名称...")
        else:
            print(f"使用 Playwright 访问: {search_url}")
            print(f"等待选择器: {selector}")

        try:
            with sync_playwright() as p:
                if progress_callback:
                    progress_callback("正在初始化翻译环境...")
                
                # 尝试启动 Chromium 浏览器，可以改为 'firefox' 或 'webkit'
                # headless=True 表示无头模式，不显示浏览器窗口
                # headless=False 可以用于调试，会显示浏览器窗口
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # 增加User-Agent模拟真实浏览器，防止被检测
                page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"})
                
                if progress_callback:
                    progress_callback("正在查询中，请稍候...")
                else:
                    print("正在导航到页面...")
                    
                page.goto(search_url, timeout=20000) # 设置导航超时为20秒
                
                if progress_callback:
                    progress_callback("查询中，正在等待结果生成...")
                else:
                    print("导航完成，等待目标元素...")

                try:
                    # 等待目标元素出现，最长等待15秒
                    if progress_callback:
                        progress_callback("正在分析数据 (可能需要约15秒)...")
                        
                    page.wait_for_selector(selector, timeout=15000)
                    
                    if progress_callback:
                        progress_callback("已找到结果，提取英文名称...")
                    else:
                        print("目标元素已找到!")
                    
                    # 获取元素文本
                    element = page.query_selector(selector)
                    if element:
                        english_name = element.text_content().strip()
                        if progress_callback:
                            progress_callback(f"成功获取英文名: {english_name}")
                        else:
                            print(f"提取到英文名: {english_name}")
                    else:
                        if progress_callback:
                            progress_callback("已分析完成，但无法提取有效内容")
                        else:
                            print("元素找到但无法获取内容")
                        
                except PlaywrightTimeoutError:
                    if progress_callback:
                        progress_callback("查询超时，未能找到英文名称")
                    else:
                        print(f"等待元素超时（15秒），未能找到选择器: {selector}")
                    # 超时后，可以尝试保存页面快照或HTML用于调试
                    # page.screenshot(path='baidu_timeout_screenshot.png')
                    # with open('baidu_timeout_page.html', 'w', encoding='utf-8') as f:
                    #     f.write(page.content())
                except Exception as wait_err:
                    if progress_callback:
                        progress_callback(f"分析过程中出错: {wait_err}")
                    else:
                        print(f"等待或查找元素时发生错误: {wait_err}")

                if progress_callback:
                    progress_callback("查询完成，正在关闭环境...")
                else:
                    print("关闭浏览器...")
                browser.close()
                
        except Exception as e:
            if progress_callback:
                progress_callback(f"翻译过程中出错: {e}")
            else:
                print(f"Playwright 操作过程中出错: {e}")
        
        if english_name:
             # 可以在这里进行一些最终的清理
             pass

        return english_name
        
    def download_file(self, url, save_path, progress_signal):
        # 这个方法仍然使用 requests
        try:
            response = requests.get(url, headers=self.headers, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            downloaded_size = 0
            
            # 初始化下载速度和大小计算相关变量
            start_time = time.time()
            last_time = start_time
            last_bytes = 0
            
            # 设置标志，防止下载时被取消后继续更新进度
            cancelled = False
            
            with open(save_path, 'wb') as file:
                for data in response.iter_content(block_size):
                    # 检查线程是否被标记为取消
                    # 由于此代码运行在QThread中，需要检查QThread.isRunning()
                    # 这里无法直接访问QThread，所以用一个变量标记
                    if cancelled:
                        return False
                        
                    size = file.write(data)
                    downloaded_size += size
                    
                    current_time = time.time()
                    time_diff = current_time - last_time
                    bytes_diff = downloaded_size - last_bytes

                    # 更新进度和速度信息 (每0.5秒更新一次避免过于频繁)
                    if time_diff > 0.5 or downloaded_size == total_size:
                        speed = bytes_diff / time_diff if time_diff > 0 else 0
                        speed_str = self._format_speed(speed)
                        
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            try:
                                progress_signal.emit(progress, speed_str) # 传递速度信息
                            except RuntimeError:
                                # 当线程被终止时可能会抛出RuntimeError
                                cancelled = True
                                return False
                        else:
                            # 如果总大小未知，只显示已下载量和速度
                            try:
                                progress_signal.emit(-1, speed_str) # 使用-1表示进度未知
                            except RuntimeError:
                                cancelled = True
                                return False
                            
                        last_time = current_time
                        last_bytes = downloaded_size
                        
            return True
        except requests.RequestException as e:
            print(f"下载文件失败: {str(e)}")
            raise Exception(f"下载文件失败: {str(e)}")
        
    def _make_request(self, url, is_baidu=False, timeout=15):
        """改进的网络请求方法，支持自定义超时"""
        try:
            headers_to_use = self.headers.copy()
            
            response = requests.get(url, headers=headers_to_use, timeout=timeout)
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type.lower() and not url.endswith(('.zip', '.rar', '.7z')): 
                 print(f"警告：请求 {url} 返回的不是HTML ({content_type})")

            response.encoding = response.apparent_encoding if response.apparent_encoding else 'utf-8'
            return response.text
        except requests.Timeout:
             print(f"网络请求超时: {url}")
             if url.startswith(self.base_url) and "?s=" in url:  # 这是搜索请求
                 # 搜索请求超时时返回空HTML而不是抛出异常，保持与原来的行为一致
                 print("搜索请求超时，返回空结果")
                 return "<html><body></body></html>"
             # 其他请求仍然抛出异常
             raise Exception(f"网络请求超时: {url}")
        except requests.RequestException as e:
            print(f"网络请求失败: {str(e)}")
            if url.startswith(self.base_url) and "?s=" in url:  # 这是搜索请求
                 # 搜索请求失败时返回空HTML而不是抛出异常，保持与原来的行为一致
                 print("搜索请求失败，返回空结果")
                 return "<html><body></body></html>"
            # 其他请求仍然抛出异常
            raise Exception(f"网络请求失败: {str(e)}")
        finally:
            pass

    def _format_speed(self, speed_bps):
        """格式化速度显示"""
        if speed_bps < 1024:
            return f"{speed_bps:.2f} B/s"
        elif speed_bps < 1024 * 1024:
            return f"{speed_bps / 1024:.2f} KB/s"
        else:
            return f"{speed_bps / (1024 * 1024):.2f} MB/s"