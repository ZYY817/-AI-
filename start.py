import os
import sys
import subprocess
import json
import ctypes
from pathlib import Path

# 配置相关函数
def get_config_path():
    """获取配置文件路径"""
    # 在用户文档目录中创建配置目录
    config_dir = os.path.join(os.path.expanduser("~"), "Documents", "FLYYING")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "config.json")

def load_config():
    """加载配置"""
    config_path = get_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"first_run": True}
    return {"first_run": True}

def save_config(config):
    """保存配置"""
    config_path = get_config_path()
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f)

def create_agreement_flag():
    """创建已同意协议的标记文件"""
    # 获取应用程序根目录
    if hasattr(sys, 'frozen'):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建.agreement_accepted文件
    agreement_file = os.path.join(base_dir, ".agreement_accepted")
    try:
        with open(agreement_file, 'w') as f:
            f.write("agreement accepted")
    except Exception as e:
        print(f"无法创建协议接受标记文件: {e}")

# 设置环境变量
def setup_environment():
    if getattr(sys, 'frozen', False):
        # 如果是打包的应用
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        browser_path = os.path.join(base_dir, "playwright-browsers")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browser_path
        
        # 禁用证书验证警告
        os.environ['PYTHONWARNINGS'] = 'ignore:Unverified HTTPS request'
        
        # 创建已同意协议的标记文件，避免显示协议弹窗
        create_agreement_flag()
        
        # 检查是否首次运行
        config = load_config()
        first_run = config.get("first_run", True)
        
        # 如果不是首次运行，则跳过显示声明
        if not first_run:
            # 设置标记表示不是首次运行
            os.environ['FLYYING_SKIP_DISCLAIMER'] = '1'
        
        # 更新配置，标记为非首次运行
        config["first_run"] = False
        save_config(config)

def check_dependencies():
    try:
        import PyQt6
        import requests
        import bs4
        from playwright.sync_api import sync_playwright
        return True
    except ImportError as e:
        print(f"缺少依赖: {e}")
        return False

def install_dependencies():
    print("正在安装依赖...")
    try:
        # 安装基本依赖
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        # 安装 playwright
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        # 安装 playwright 浏览器
        subprocess.check_call([sys.executable, "-m", "playwright", "install"])
        return True
    except subprocess.CalledProcessError:
        print("安装依赖失败，请手动安装requirements.txt中的依赖")
        return False

def main():
    # 设置环境变量
    setup_environment()
    
    # 添加src目录到Python路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(current_dir, "src")
    sys.path.insert(0, src_dir)
    
    # 检查依赖
    if not check_dependencies():
        if not install_dependencies():
            # 避免使用 input()
            print("依赖安装失败，请手动安装requirements.txt中的依赖")
            # 如果可能，使用消息框
            try:
                from PyQt6.QtWidgets import QApplication, QMessageBox
                app = QApplication(sys.argv)
                QMessageBox.critical(None, "错误", "依赖安装失败，请手动安装requirements.txt中的依赖")
            except:
                # 如果无法导入PyQt6，等待几秒钟后退出
                import time
                time.sleep(5)
            return
    
    # 导入并运行主程序
    try:
        import src.main
        src.main.main()
    except Exception as e:
        print(f"启动程序时出错: {e}")
        # 避免使用 input()
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance():
                QMessageBox.critical(None, "错误", f"启动程序时出错: {e}")
            else:
                app = QApplication(sys.argv)
                QMessageBox.critical(None, "错误", f"启动程序时出错: {e}")
        except:
            # 如果无法导入PyQt6，等待几秒钟后退出
            import time
            time.sleep(5)

if __name__ == "__main__":
    main()