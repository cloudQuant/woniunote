# woniunote
A blog and website (https://www.yunjinqi.top) written by python, flask, HTML, CSS, JavaScript and mysql.

User info
### 介绍
在ubuntu20.04上，安装好anaconda后，使用flask、html、css和mysql建的个人博客，目前已经在个人网站(yunjinqi.top)上运行。

### 安装教程
```bash
# 国内克隆项目
git clone https://gitee.com/yunjinqi/woniunote.git
# 国外克隆项目
git clone https://github.com/cloudQuant/woniunote.git
# 安装依赖包
pip install -r ./woniunote/requirements.txt
cd woniunote/woniunote
# 创建账户名和密码的配置文件
touch user_password_config.yaml
# 打开文件，写入账户名和密码，参考user_password_config_example.yaml
nano user_password_config.yaml
# 如果需要本地测试，在configs目录下，运行
openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365
# 返回到主目录
cd ../../..
# 安装
pip install -U ./woniunote
# 首次运行的时候，创建数据库：python common/create_database.py
cd woniunote/woniunote
# 启动博客: 在woniunote包目录下执行
python app.py
# 生产环境执行: 
nohup gunicorn -w 3 -b 0.0.0.0:8888 app:app > woniunote_run.log 2>&1 &
# 本地测试使用
nohup python app.py > woniunote_run.log 2>&1 &
```


### 测试项目
```bash
# 首先安装测试依赖：
pip install -r requirements.txt
# 安装 Playwright 浏览器：
playwright install
# 运行功能测试：
pytest . -v --cov=woniunote --cov-report=html -n auto
# 运行性能测试：
locust -f tests/test_performance.py --host=http://localhost:5000
```




### 个人网站

这套开源代码实现的个人网站: https://www.yunjinqi.top


#### 待实现功能



