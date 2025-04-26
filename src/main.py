import os
import sys
import struct

# 将src目录添加到Python路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的环境
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    # 如果是开发环境
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if base_path not in sys.path:
        sys.path.insert(0, base_path)

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit, QTextEdit, QMessageBox
from PyQt6.QtCore import Qt, QSharedMemory
from src.gui.main_window import MainWindow
import subprocess

# 确保 Playwright 浏览器已安装
def ensure_playwright_browsers():
    # 在打包环境中，浏览器应该已经包含在资源中
    if getattr(sys, 'frozen', False):
        print("在打包环境中运行，检查 Playwright 浏览器")
        playwright_browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
        if playwright_browsers_path and os.path.exists(playwright_browsers_path):
            print(f"Playwright 浏览器路径存在: {playwright_browsers_path}")
        else:
            print(f"警告: Playwright 浏览器路径不存在: {playwright_browsers_path}")
            print("尝试安装 Playwright 浏览器")
            try:
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                               capture_output=True, text=True, check=True)
                print("Playwright browsers installation completed successfully")
            except subprocess.CalledProcessError as e:
                print(f"错误: 无法安装 Playwright 浏览器: {e}")
            except Exception as e:
                print(f"错误: Playwright 浏览器安装过程中出现错误: {e}")
        return
    
    # 在开发环境中，尝试安装浏览器
    try:
        print("在开发环境中运行，尝试安装 Playwright 浏览器")
        # 检查 playwright 命令是否可用
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                      capture_output=True, text=True, check=True)
        print("Playwright browsers installation completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to install Playwright browsers: {e}")
    except Exception as e:
        print(f"Warning: Error during Playwright browsers installation: {e}")

# 设置浏览器路径
if getattr(sys, 'frozen', False):
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    playwright_browsers_path = os.path.join(base_dir, "playwright-browsers")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = playwright_browsers_path
    print(f"设置 PLAYWRIGHT_BROWSERS_PATH 为: {playwright_browsers_path}")
else:
    # 在开发环境中，使用默认路径或设置为项目根目录下的特定文件夹
    playwright_browsers_path = os.path.join(base_path, "playwright-browsers")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = playwright_browsers_path
    print(f"设置 PLAYWRIGHT_BROWSERS_PATH 为: {playwright_browsers_path}")

def main():
    # 确保 Playwright 浏览器已安装
    ensure_playwright_browsers()
    
    app = QApplication(sys.argv)
    
    print("Starting FLYYING application...")
    
    # 创建共享内存对象
    shared_memory = QSharedMemory("FLYYING_INSTANCE")
    
    # 首先尝试附加到现有的共享内存
    if shared_memory.attach():
        print("Found existing shared memory. Another instance is running.")
        shared_memory.detach()
        QMessageBox.warning(None, "警告", "FLYYING 程序已经在运行中。")
        return
    
    # 如果附加失败，尝试创建新的共享内存
    if not shared_memory.create(8):  # 使用8字节来存储进程ID
        print("Failed to create shared memory. Another instance might be running.")
        QMessageBox.warning(None, "警告", "FLYYING 程序已经在运行中。")
        return
    
    # 将当前进程ID写入共享内存
    current_pid = os.getpid()
    print(f"Current process ID: {current_pid}")
    shared_memory.lock()
    shared_memory.data()[:8] = struct.pack('Q', current_pid)
    shared_memory.unlock()
    
    print("Successfully created shared memory. This is the first instance.")
    
    window = MainWindow()
    window.show()
    
    # 运行应用
    print("Starting main event loop...")
    exit_code = app.exec()
    
    # 在应用退出时释放共享内存
    print("Application exiting. Detaching shared memory...")
    shared_memory.detach()
    
    print(f"Exiting with code: {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()