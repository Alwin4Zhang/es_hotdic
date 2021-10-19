# ES词典热更新问题

Tags: Elasticsearch

本文旨在解决elasticsearch不同版本，包括es6、es7等版本的同义词典、ik分词扩展词典热更新问题。不作elasticsearch基础的详细普及。

## 使用环境:

系统:Macos Catalina:10.15.7

CPU:Intel Core i7-10510u

内存:16GB

硬盘:500G


## 痛点:

Elasticsearch修改索引配置代价比较高。修改同义词典，一般情况下是需要重启索引后才能生效；修改扩展词典，一般需要更新手动更新索引。

## Elasticsearch配置同义词表、扩展词典

### 同义词典

同义词表路径

```bash
/elasticsearch-${version}/config/analysis/synonyms.txt
```

同义词典内容

```bash
社保,社会保险
周三,星期三
```

### ik分词词典

IKAnalyzer.cfg.xml

路径

```bash
/elasticsearch-${version}/plugins/ik/config/IKAnalyzer.cfg.xml
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">
<properties>
	<comment>IK Analyzer 扩展配置</comment>
	<!--用户可以在这里配置自己的扩展字典 -->
	<entry key="ext_dict">my.dic</entry>
	 <!--用户可以在这里配置自己的扩展停止词字典-->
	<entry key="ext_stopwords"></entry>
	<!--用户可以在这里配置远程扩展字典 -->
	<entry key="remote_ext_dict">http://localhost:9527/extdic</entry>
	<!--用户可以在这里配置远程扩展停止词字典-->
	<entry key="remote_ext_stopwords">http://localhost:9527/stopwords</entry>
</properties>
```

其中ext_dict适用于不怎么需要更新的本地扩展词典，ext_stopwords适用于不怎么需要更新的扩展停用词；remote开头的路径指定的一般用一个轮询服务来定时更新远程扩展词典，其中remote_ext_dict可以配置远程扩展字典，remote_ext_stopwords可以在这里配置远程扩展停止词字典。

### 热更新词典方式

```bash

├── es_hotdic.py
├── ext.dic
├── stop.dic
└── synonyms.txt
├── elasticsearch-analysis-dynamic-synonym-6.8.12.zip
├── es_utils.py
├── mysql_db.py
├── requirements.txt
└── tor_test.py
```

- es_hotdic.py

```python

# -*- coding: utf-8 -*-
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
```

## 同义词更新

### Elasticsearch7

Elasticsearch7中创建索引配置可参考

请注意我们将同义词筛选器标记为了 updateable（可更新）。这一点很重要，因为当我们调用新的重新加载端点时，只会重新加载可更新的筛选器；

```bash
PUT /my-index-000001
{
  "settings": {
    "index": {
      "analysis": {
        "analyzer": {
          "my_synonyms": {
            "tokenizer": "whitespace",
            "filter": [ "synonym" ]
          }
        },
        "filter": {
          "synonym": {
            "type": "synonym_graph",
            "synonyms_path": "analysis/synonym.txt",  
            "updateable": true                        
          }
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "text": {
        "type": "text",
        "analyzer": "standard",
        "search_analyzer": "my_synonyms"              
      }
    }
  }
}
```

此时更新synonyms.txt词典中内容后，使用_reload_search_analyzer更新索引

```bash
POST /my-index-000001/_reload_search_analyzers
```

API response:

```bash
{
  "_shards": {
    "total": 2,
    "successful": 2,
    "failed": 0
  },
  "reload_details": [
    {
      "index": "my-index-000001",
      "reloaded_analyzers": [
        "my_synonyms"
      ],
      "reloaded_node_ids": [
        "mfdqTXn_T7SGr2Ho2KT8uw"
      ]
    }
  ]
}
```

链接:

1.[https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-reload-analyzers.html](https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-reload-analyzers.html)

2.[https://www.elastic.co/cn/blog/boosting-the-power-of-elasticsearch-with-synonyms](https://www.elastic.co/cn/blog/boosting-the-power-of-elasticsearch-with-synonyms)

### Elasticsearch6

如下图所示，非常遗憾的是该方法无法在es6中使用

![Untitled](ES%E8%AF%8D%E5%85%B8%E7%83%AD%E6%9B%B4%E6%96%B0%E9%97%AE%E9%A2%98%203b74d08de09c44d688f3a9513765582a/Untitled.png)

聪明的大佬们开发了类似于ik扩展词典更新的方式，我只是搬运工

参考链接:

1.[https://blog.csdn.net/like_java_/article/details/107379083](https://blog.csdn.net/like_java_/article/details/107379083)

2.[https://github.com/bells/elasticsearch-analysis-dynamic-synonym](https://github.com/bells/elasticsearch-analysis-dynamic-synonym)

- **Dynamic Synonym for ElasticSearch**

[Vesion]  

|  dynamic synonym version   | ES version  |
|  ----  | ----  |
| master  | 7.x -> master |
| 6.1.4  | 6.1.4 |
| 5.2.0 | 5.2.0 |  
| 5.1.1 | 5.1.1 |  
| 2.2.0 | 2.2.0 |  
| 2.1.0 | 2.1.0 |  
| 1.6.0 | 1.6.0 |   

- **Installation**

**1.**mvn package  

**2.**copy and unzip target/releases/elasticsearch-analysis-dynamic-synonym-{version}.zip to your-es-root/plugins/dynamic-synonym   


项目用到的es版本是6.8.12，在已开源的插件版本中没有，在repo的issues中找到了最接近的[https://github.com/lxc-123/elasticsearch-analysis-dynamic-synonym-6.5.0](https://github.com/lxc-123/elasticsearch-analysis-dynamic-synonym-6.5.0)

直接使用报错，虽然以前写过java，想过头铁撸java但最后放弃。

按照下文思路:

[https://blog.csdn.net/weixin_39999637/article/details/90083011](https://blog.csdn.net/weixin_39999637/article/details/90083011)

首先，将pom.xml中的版本号改为6.8.12,

```xml
<groupId>com.bellszhu.elasticsearch</groupId>
<artifactId>elasticsearch-analysis-dynamic-synonym</artifactId>
<version>6.8.12</version>
<packaging>jar</packaging>
<name>elasticsearch-dynamic-synonym</name>
<description>Analysis-plugin for synonym</description>
```

然后打包：

```bash
mvn package
```

很不幸，got errors

![Untitled](ES%E8%AF%8D%E5%85%B8%E7%83%AD%E6%9B%B4%E6%96%B0%E9%97%AE%E9%A2%98%203b74d08de09c44d688f3a9513765582a/Untitled%201.png)

浏览对应目录找到最接近elasticsearch6.8.12版本的elasticsearch-cluster-runner.jar是6.8.9.0

[https://repo.maven.apache.org/maven2/org/codelibs/elasticsearch-cluster-runner/](https://repo.maven.apache.org/maven2/org/codelibs/elasticsearch-cluster-runner/)

继续修改pom.xml

```xml
<dependency>
  <groupId>org.codelibs</groupId>
  <artifactId>elasticsearch-cluster-runner</artifactId>
  <!-- <version>${project.version}.0</version> -->
  <version>6.8.9.0</version>
  <scope>test</scope>
</dependency>
```

maven编译通过

同义词词典远程加载需要在创建索引时加入:

```bash
PUT /test_remote_index
{
  "settings": {
    "index":{
      "analysis":{
        "analyzer":{
          "ikIndexAnalyzer":{
            "tokenizer":"ik_max_word",
            "filter":["remote_synonym"]
          },
          "ikSearchAnalyzer":{
            "tokenizer":"ik_smart",
            "filter":["remote_synonym"]
          }
        },
        "filter":{
          "remote_synonym":{
            "type":"dynamic_synonym",
            "synonyms_path":"http://localhost:9527/synonyms",
            "interval":30
          },
          "local_synonym":{
            "type":"dynamic_synonym",
            "synonyms_path":"synonym.txt"
          }
        }
      }
    }
  },
  "mappings": {
    "_doc":{
      "properties":{
        "content":{
          "analyzer":"ik_max_word",
          "type":"text",
          "fields":{
            "iki":{
              "analyzer":"ikIndexAnalyzer",
              "type":"text"
            },
            "iks":{
              "analyzer":"ikSearchAnalyzer",
              "type":"text"
            }
          }
        }
      }
    }
  }
}
```

创建完索引后，在该索引内所有的数据，均可通过同义词词典进行同义词查询增强。同义词词典内容如上同义词格式所示。

最后，可以使用接口的形式传词条或词条对到对应的本地文件或数据库中。特别注意，同义词典可以自动更新，但扩展词典需要通过_update_by_query的api方式在内容插入后自动触发更新所有相关的索引document才能在后面的query中有效。
