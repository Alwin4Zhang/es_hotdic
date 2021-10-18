# -*- coding: utf-8 -*-
"""
    @Time    : 2020/10/28 4:33 PM
    @Author  : alwin
    @Email   : alwin114@hotmail.com
"""
import tornado.ioloop
import tornado.web
import tornado
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.options import define, options
from flask import Flask
import os
import time
import datetime

conf = {"port": 9527, "ext_dic": "ext.dic",
        "stopwords": "stop.dic", "synonyms": "synonyms.txt"}
"""
remote_ext_dict
该http请求需要返回两个header，一个是Last-Modified,一个是ETag，这两者都是字符串类型，只要有一个发生变化，该插件就会去抓取新的分词进而更新词库
该http请求返回的内容格式是一行一个分词，换行符用\n即可
满足以上两点要求就可以实现热更新分词了，不需要重启ES实例
"""


# server句柄
class MainHandler(tornado.web.RequestHandler):
    # 初始化,传入字典文件
    def initialize(self, file):
        self.file = file
        # 文件不存在就创建
        if not os.access(self.file, os.F_OK):
            f = open(self.file, "w")
            f.close()

    # get method
    def get(self):
        f = open(self.file, "r", encoding="utf-8")
        data = f.read()
        f.close()
        self.set_header("Content-Type", "text/plain; charset=UTF-8")
        self.set_header("ETag", "2")
        self.write(data)

    # head method
    # head方法判断修改时间，并在get方法将header中的信息传递给客户端
    def head(self):
        mTime = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(os.stat(self.file).st_mtime)
        )
        # mTime = datetime.datetime.strftime(
        #     datetime.datetime.fromtimestamp(os.stat(self.file).st_mtime)
        #     + datetime.timedelta(seconds=30),
        #     "%Y-%m-%d %H:%M:%S",
        # )
        self.set_header("Last-Modified", mTime)
        self.set_header("ETag", "2")
        self.set_header("Content-Length", "0")
        self.finish()


# 注册webMapping
def make_app():
    return tornado.web.Application(
        [
            (r"/extdic", MainHandler, {"file": conf["ext_dic"]}),
            (r"/stopwords", MainHandler, {"file": conf["stopwords"]}),
            (r'/synonyms',MainHandler,{"file":conf["synonyms"]})
        ],
        debug=True,
    )


app = Flask(__name__)


@app.route("/")
def tst():
    return {"result": "Hello World!"}


if __name__ == "__main__":
    options.parse_command_line()
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(8008)

    tornado_app = make_app()
    tornado_app.listen(conf["port"])
    tornado.ioloop.IOLoop.current().start()
