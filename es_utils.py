# -*- coding: utf-8 -*-
'''
  @CreateTime	:  2021/10/19 10:27:27
  @Author	:  Alwin Zhang
  @Mail	:  zjfeng@homaytech.com
'''

from elasticsearch import Elasticsearch


class SearchHelper(object):
    def __init__(self, es_ip, es_port, es_username, es_password, index_name=None):
        self.index_name = index_name
        if not es_port:
            es_port = 9200
        es_ip = es_ip + ":" + es_port
        self.es = Elasticsearch(es_ip, http_auth=(es_username, es_password))

    def _update_by_query(self, index_name, body):
        return self.es.update_by_query(index=index_name, doc_type="_doc", body=body, conflicts="proceed")

    def _ik_tokenize(self, text, index_name, thres=0, analyzer=None):
        if isinstance(text, str):
            text = text.strip()
        if not analyzer:
            analyzer = "ik_max_word"
        bd = {
            "text": text,
            "analyzer": analyzer
        }
        token_res = self.es.indices.analyze(index=index_name, body=bd)
        tokens = token_res.get("tokens", [])
        tokens = [tk for tk in tokens if len(tk["token"]) > thres]
        return tokens
