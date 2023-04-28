# 通过死循环加时间判断的方式来执行定时任务
import os, glob, requests
import time
import datetime 

def can_use_minute():
    '''计算两个时间点之间的分钟数'''
    # 处理格式,加上秒位
    # 计算分钟数
    startTime2 = datetime.datetime.now()
    endTime2 = datetime.datetime.strptime("2078-05-07 23:59:59", "%Y-%m-%d %H:%M:%S")
    # 来获取时间差中的秒数。注意，seconds获得的秒只是时间差中的小时、分钟和秒部分的和，并没有包含时间差的天数（既是两个时间点不是同一天，失效）
    total_seconds = (endTime2 - startTime2).total_seconds()
    # 来获取准确的时间差，并将时间差转换为秒
    mins = total_seconds / 60
    return int(mins)

# while True:
#     now = time.strftime('%H:%M')
#     if now == '02:00':
#         # 每天清空index-static缓存目录文件
#         list = glob.glob('../template/index-static/*.html')
#         for file in list:
#             os.remove(file)
#         # 清空完成后，再调用http://127.0.0.1:5000/static重新生成
#         requests.get('http://127.0.0.1:5000/static')
#         print('%s: 成功清空缓存文件并重新生成.' % now)
#     time.sleep(60)  # 暂时时间不能低于60秒，也不能多于120秒
