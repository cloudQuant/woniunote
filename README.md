# woniunote
A blog and website (https://www.yunjinqi.top) written by python, flask, html, css, javascript and mysql.

### 介绍
在ubuntu20.04上，安装好anaconda后，使用flask、html、css和mysql建的个人博客，目前已经在个人网站(yunjinqi.top)上运行。


### 安装教程
```bash
# 克隆项目
git clone https://gitee.com/yunjinqi/woniunote.git
# 安装依赖包
pip install -r ./woniunote/requirements.txt
# 进入woniunote目录，在configs目录下创建config.py文件，内容参考config_example.py，修改数据库配置
cd woniunote/woniunote

```


4. 在configs目录下创建证书，用于https访问的时候验证:`openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365`
5. 在woniunote目录下, 安装依赖包：pip install -r requirements.txt
6. 安装woniunote: 在woniunote所在的目录,比如Downloads，执行`pip install -U ./woniunote`
7. 创建mysql数据库woniunote: 在woniunote包目录下执行，比如site-packages/woniunote，运行`python common/create_database.py`创建数据库，
8. 启动博客: 在woniunote包目录下执行`python app.py`
9. 生产环境执行: `nohup gunicorn -w 3 -b 0.0.0.0:8888 app:app > woniunote_run.log 2>&1 &`
10. 本地测试使用：nohup python app.py > woniunote_run.log 2>&1 &

### 个人网站

这套开源代码实现的个人网站: https://www.yunjinqi.top


#### 待实现功能



