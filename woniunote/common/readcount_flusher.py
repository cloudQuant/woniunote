import time
import logging
from woniunote.common.redisdb import redis_connect
from woniunote.common.database import dbconnect
from woniunote.common.create_database import Article

logger = logging.getLogger(__name__)

def flush_readcounts(batch_size: int = 1000):
    red = redis_connect()
    if not red:
        return 0
    dbsession, md, DBase = dbconnect()
    if not dbsession:
        return 0
    cursor = 0
    processed = 0
    while True:
        cursor, keys = red.scan(cursor=cursor, match='article:readcount:*', count=batch_size)
        if not keys:
            if cursor == 0:
                break
        pipe = red.pipeline()
        for key in keys:
            pipe.get(key)
        values = pipe.execute()
        for key, val in zip(keys, values):
            try:
                incr = int(val or 0)
                if incr <= 0:
                    continue
                articleid = int(key.split(':')[-1])
                dbsession.query(Article).filter_by(articleid=articleid).update({
                    'readcount': Article.readcount + incr,
                    'updatetime': Article.updatetime
                })
                red.delete(key)
                processed += 1
            except Exception as e:
                logger.error(f'flush key {key} failed: {e}')
        dbsession.commit()
        if cursor == 0:
            break
    return processed

def start_background_flusher(interval_seconds: int = 60):
    import threading
    def _loop():
        while True:
            try:
                flush_readcounts()
            except Exception as e:
                logger.error(f'readcount flusher error: {e}')
            time.sleep(interval_seconds)
    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t
