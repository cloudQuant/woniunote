# woniunote

#### 介绍
在ubuntu20.04上，安装好anaconda后，使用flask、html、css和mysql建的个人博客，目前已经在个人网站(yunjinqi.top)上运行。


#### 安装教程

1. cd ./anaconda3/lib/python3.8/site-packages/
2. git clone https://gitee.com/yunjinqi/woniunote.git
3. cd woniunote
4. nohup gunicorn -w 3 -b 0.0.0.0:8888 app:app > woniunote_run.log 2>&1 &

#### 待实现功能

1. 开发一个todo list 能够用于记录日常清单
2. 仿照todo list，trello和柳比歇夫的时间记录日子，开发一个card list，能够实现todo list的功能，使用起来有比较像trello，但是有具有柳比歇夫一样的时间记录与统计功能。
3. 统计每周、每月、每年自己在各类活动上使用的时间。

