最近腾讯云上的免费的ssl证书到期了，并且改为每3个月需要更新一次，感觉有些麻烦。

下面是更新ssl证书的步骤：
1. 登录腾讯云SSL证书管理控制台，找到需要更新的证书，点击“管理”按钮。
2. 申请新的免费证书，申请成功之后，下载nginx配置文件，并将证书文件和密钥文件上传到woniunote/configs文件夹下
3. 重新安装woniunote，用于更新证书：pip install --upgrade ./woniunote
4. 重启：sudo nginx -s reload -c /home/ubuntu/woniunote/woniunote/configs/woniunote_nginx_config
5. 在app.py所在文件夹，运行gunicorn -w 3 -b 0.0.0.0:8888 app:app
6. 等待一段时间，访问https://你的域名，如果可以正常访问，证书更新成功。
7. ctrl+c 停止gunicorn，再次运行nohup gunicorn -w 3 -b 0.0.0.0:8888 app:app > woniunote_run.log 2>&1 &