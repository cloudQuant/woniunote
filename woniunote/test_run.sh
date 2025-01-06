#!/bin/bash

# 拉取最新代码
git pull

# 切换到项目根目录
cd ../..

# 安装或更新 woniunote 包
pip install -U ./woniunote/

# 切换到 woniunote 应用目录
cd woniunote/woniunote

# 使用 gunicorn 启动应用
gunicorn -w 3 -b 0.0.0.0:8888 app:app