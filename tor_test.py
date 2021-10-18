# 准备安装Tornado: pip install tornado
import time
import datetime
import os
import tornado.ioloop
import tornado.web
from mysql_db import MysqlUtil

mysql_util = MysqlUtil(db_name="uba")

conf = {"port": 9527, "ext_dic": "ext.dic", "stopwords": "stop.dic"}


class MainHandler(tornado.web.RequestHandler):  # 注意继承RequestHandler 而不是redirectHandler

    def initialize(self, name):
        self.name = name

    def get(self):
        if self.name == "stopwords":
            sql = "select word from stopwords limit 10"
        if self.name == "confusion":
            sql = "select origin from custom_confusion limit 10"
        words = "\n".join([res[0] for res in mysql_util.find_all(sql) if res])
        words = bytes(words, encoding="utf-8")
        self.set_header("Content-Type", "text/plain; charset=UTF-8")
        self.set_header("ETag", "2")
        self.write(words)

    def head(self):
        # mTime = time.strftime(
        #     "%Y-%m-%d %H:%M:%S", time.localtime(os.stat(__file__).st_mtime)
        # )
        
        mTime = datetime.datetime.strftime(datetime.datetime.now(),"%Y-%m-%d %H:%M:%S")
        self.set_header("Last-Modified", mTime)
        self.set_header("ETag", "2")
        self.set_header("Content-Length", "0")
        self.finish()


# application = tornado.web.Application([
#     (r'/login/', MainHandler)  # 路由
# ])

def make_app():
    return tornado.web.Application(
        [
            (r"/extdic", MainHandler, {"name": "stopwords"}),
            (r"/stopwords", MainHandler, {"name": "confusion"}),
        ],
        debug=True
    )


if __name__ == '__main__':
    application = make_app()
    application.listen(9527)  # 创建1个socket对象
    tornado.ioloop.IOLoop.instance().start()  # conn,addr=socket.accept()进入监听状态
