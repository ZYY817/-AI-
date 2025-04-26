from bs4 import BeautifulSoup
import re

class HtmlParser:
    def parse_search_results(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # 查找所有文章条目
        articles = soup.find_all('article', class_='post')
        
        for article in articles:
            # 提取标题和链接
            title_element = article.find('h2', class_='post-title')
            if title_element and title_element.a:
                title = title_element.a.text.strip()
                url = title_element.a['href']
                
                # 提取日期
                day = article.find('div', class_='post-details-day')
                month = article.find('div', class_='post-details-month')
                year = article.find('div', class_='post-details-year')
                
                date = ""
                if day and month and year:
                    date = f"{day.text} {month.text} {year.text}"
                    
                results.append({
                    "title": title,
                    "url": url,
                    "date": date
                })
                
        return results
        
    def parse_trainer_versions(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        versions = []
        
        # 查找下载区域
        download_area = soup.find('div', class_='download-attachments')
        
        if download_area:
            # 1. 首先处理带有类标记的行（如Auto-Updating Version和Standalone Versions）
            for tr in download_area.find_all('tr', class_=lambda c: c and ('exe' in c or 'zip' in c or 'rar' in c or 'autoupdate' in c)):
                # 获取所有列
                cols = tr.find_all('td')
                if not cols:
                    continue
                
                # 查找下载链接
                link_col = cols[0] if cols else None
                link = link_col.find('a') if link_col else None
                
                if link and link.get('href'):
                    href = link.get('href')
                    
                    # 从链接文本或title属性获取文件名
                    filename_text = link.text.strip()
                    if not filename_text and link.get('title'):
                        filename_text = link.get('title').strip()
                    
                    # 获取日期、大小和下载次数
                    date_text = cols[1].text.strip() if len(cols) > 1 else ""
                    size_text = cols[2].text.strip() if len(cols) > 2 else ""
                    downloads_text = cols[3].text.strip() if len(cols) > 3 else ""
                    
                    # 确定文件类型
                    file_type = ""
                    # 根据tr的class属性判断文件类型
                    row_classes = tr.get('class', [])
                    if any('exe' in cls or 'autoupdate' in cls for cls in row_classes):
                        file_type = "exe"
                    elif any('zip' in cls for cls in row_classes):
                        file_type = "zip"
                    elif any('rar' in cls for cls in row_classes):
                        file_type = "rar"
                    
                    # 确保文件名有正确的扩展名
                    if file_type and not filename_text.lower().endswith(f".{file_type}"):
                        filename_text = f"{filename_text}.{file_type}"
                    
                    # 添加到版本列表
                    version_info = {
                        "filename": filename_text,
                        "date": date_text,
                        "size": size_text,
                        "download_url": self._fix_url(href),
                        "downloads": downloads_text,
                        "file_type": file_type
                    }
                    versions.append(version_info)
            
            # 2. 处理表格中的其他行
            tables = download_area.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    # 跳过已处理的带类标记的行
                    if row.get('class') and any(cls in ['exe', 'zip', 'rar', 'autoupdate'] for cls in row.get('class')):
                        continue
                    
                    # 跳过表头行
                    if row.find('th'):
                        continue
                    
                    # 对于colspan标题行，不处理
                    if row.find('td', attrs={'colspan': True}):
                        continue
                    
                    # 获取所有列
                    columns = row.find_all('td')
                    if len(columns) < 1:
                        continue
                        
                    # 查找下载链接
                    filename_cell = None
                    filename = None
                    download_url = None
                    
                    # 遍历所有列，查找包含链接的列
                    for i, col in enumerate(columns):
                        link = col.find('a')
                        if link and link.get('href'):
                            href = link.get('href')
                            # 检查链接是否是下载链接
                            if (href.startswith(('http://', 'https://')) and ('.zip' in href.lower() or '.rar' in href.lower() or '.7z' in href.lower() or '.exe' in href.lower())) or \
                               href.startswith('/download.php') or \
                               'download' in href.lower() or \
                               'attachment' in href.lower() or \
                               'file' in href.lower():
                                filename_cell = col
                                filename = link
                                download_url = href
                                filename_index = i
                                break
                    
                    if filename and download_url:
                        # 提取文件名
                        filename_text = filename.text.strip()
                        if not filename_text and filename.get('title'):
                            filename_text = filename.get('title').strip()
                        if not filename_text:
                            filename_text = download_url.split('/')[-1]
                        
                        # 初始化日期、大小和下载次数
                        date_text = ""
                        size_text = ""
                        downloads_text = ""
                        
                        # 根据列数和文件名列的位置，提取日期和大小信息
                        if len(columns) >= 2:
                            # 如果文件名在第一列，日期可能在第二列
                            if filename_index == 0 and len(columns) > 1:
                                date_text = columns[1].text.strip()
                                # 如果有第三列，可能是大小
                                if len(columns) > 2:
                                    size_text = columns[2].text.strip()
                                # 如果有第四列，可能是下载次数
                                if len(columns) > 3:
                                    downloads_text = columns[3].text.strip()
                        
                        # 确定文件类型
                        file_type = ""
                        # 从下载URL或文件名判断文件类型
                        if download_url.lower().endswith('.exe') or 'autoupdate' in download_url.lower():
                            file_type = "exe"
                        elif download_url.lower().endswith('.zip'):
                            file_type = "zip"
                        elif download_url.lower().endswith('.rar'):
                            file_type = "rar"
                        elif 'exe' in filename_text.lower():
                            file_type = "exe"
                        elif 'zip' in filename_text.lower():
                            file_type = "zip"
                        elif 'rar' in filename_text.lower():
                            file_type = "rar"
                        
                        # 确保文件名有正确的扩展名
                        if file_type and not filename_text.lower().endswith(f".{file_type}"):
                            filename_text = f"{filename_text}.{file_type}"
                        
                        # 添加到版本列表
                        version_info = {
                            "filename": filename_text,
                            "date": date_text,
                            "size": size_text,
                            "download_url": self._fix_url(download_url),
                            "downloads": downloads_text,
                            "file_type": file_type
                        }
                        versions.append(version_info)
        
        # 3. 如果没有找到足够的下载链接，在整个页面中查找
        if not versions:
            # 查找页面中所有可能的下载链接
            all_links = soup.find_all('a', href=lambda h: h and (
                (h.startswith(('http://', 'https://')) and ('.zip' in h.lower() or '.rar' in h.lower() or '.7z' in h.lower() or '.exe' in h.lower())) or
                h.startswith('/download.php') or
                'download' in h.lower() or
                'attachment' in h.lower()
            ))
            
            for link in all_links:
                href = link.get('href')
                # 检查是否已添加
                if any(v["download_url"] == href for v in versions):
                    continue
                
                # 获取文件名
                filename = link.text.strip()
                if not filename and link.get('title'):
                    filename = link.get('title').strip()
                if not filename:
                    filename = href.split('/')[-1]
                
                # 查找日期和大小信息
                parent_row = link.find_parent('tr')
                if parent_row:
                    cols = parent_row.find_all('td')
                    date_text = cols[1].text.strip() if len(cols) > 1 else ""
                    size_text = cols[2].text.strip() if len(cols) > 2 else ""
                    downloads_text = cols[3].text.strip() if len(cols) > 3 else ""
                else:
                    date_text = ""
                    size_text = ""
                    downloads_text = ""
                
                # 确定文件类型
                file_type = ""
                # 检查行的class属性
                if parent_row and parent_row.get('class'):
                    row_classes = parent_row.get('class', [])
                    if any('exe' in cls or 'autoupdate' in cls for cls in row_classes):
                        file_type = "exe"
                    elif any('zip' in cls for cls in row_classes):
                        file_type = "zip"
                    elif any('rar' in cls for cls in row_classes):
                        file_type = "rar"
                
                # 如果无法从行属性确定类型，尝试从URL或文件名判断
                if not file_type:
                    if href.lower().endswith('.exe') or 'autoupdate' in href.lower():
                        file_type = "exe"
                    elif href.lower().endswith('.zip'):
                        file_type = "zip"
                    elif href.lower().endswith('.rar'):
                        file_type = "rar"
                    elif 'exe' in filename.lower():
                        file_type = "exe"
                    elif 'zip' in filename.lower():
                        file_type = "zip"
                    elif 'rar' in filename.lower():
                        file_type = "rar"
                
                # 确保文件名有正确的扩展名
                if file_type and not filename.lower().endswith(f".{file_type}"):
                    filename = f"{filename}.{file_type}"
                
                # 添加到版本列表
                version_info = {
                    "filename": filename,
                    "date": date_text,
                    "size": size_text,
                    "download_url": self._fix_url(href),
                    "downloads": downloads_text,
                    "file_type": file_type
                }
                versions.append(version_info)
        
        return versions
        
    def _fix_url(self, url):
        """确保URL路径完整，将相对路径转换为绝对路径"""
        if url and url.startswith('/'):
            return f"https://flingtrainer.com{url}"
        return url