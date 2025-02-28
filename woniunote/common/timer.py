# 通过死循环加时间判断的方式来执行定时任务
import datetime


def can_use_minute():
    """计算两个时间点之间的分钟数"""
    # 处理格式,加上秒位
    # 计算分钟数
    start_time2 = datetime.datetime.now()
    end_time2 = datetime.datetime.strptime("2078-05-07 23:59:59", "%Y-%m-%d %H:%M:%S")
    # 来获取时间差中的秒数。注意，seconds获得的秒只是时间差中的小时、分钟和秒部分的和，并没有包含时间差的天数（既是两个时间点不是同一天，失效）
    total_seconds = (end_time2 - start_time2).total_seconds()
    # 来获取准确的时间差，并将时间差转换为秒
    min_nums = total_seconds / 60
    return int(min_nums)


