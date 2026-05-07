#!/usr/bin/env python3
"""
启动后端服务的脚本
解决 Python 版本和依赖包路径问题
"""

import sys
import os

# 添加 Python 3.8 的 site-packages 路径（包含 langchain 相关包）
python38_site_packages = os.path.join(
    os.path.expanduser('~'),
    'AppData', 'Roaming', 'Python', 'Python38', 'site-packages'
)

# 将 Python 3.8 的 site-packages 路径添加到系统路径
sys.path.insert(0, python38_site_packages)

print(f"Python version: {sys.version}")
print(f"Added path: {python38_site_packages}")

# 切换到 backend 目录
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
os.chdir(backend_dir)
print(f"Changed to directory: {os.getcwd()}")

# 运行 app.py
if __name__ == "__main__":
    # 直接执行 app.py
    exec(open('app.py').read())
