#!/usr/bin/python
# -*- coding: utf-8 -*-

import pymysql
import json
import logging
import traceback
from datetime import datetime

mysql_config_local = {
    "host": "*",
    "port": 3306,
    "username": "*",
    "password": "*",
    "db_name": "*",
    "charsets": "UTF8"
}


class MysqlUtil(object):
    """mysql util"""
    db = None
    cursor = True

    def __init__(self, db_name=None):
        self.host = mysql_config_local.get("host")
        self.port = mysql_config_local.get("port")
        self.username = mysql_config_local.get("username")
        self.password = mysql_config_local.get("password")
        self.db_name = db_name if db_name else mysql_config_local.get(
            "db_name")
        self.charsets = mysql_config_local.get("charsets")

    def get_con(self):
        """[连接数据库]
        """
        self.db = pymysql.Connect(host=self.host, port=self.port,
                                  user=self.username, password=self.password, database=self.db_name)
        self.cursor = self.db.cursor()

    def close(self):
        """[关闭数据库]
        """
        self.cursor.close()
        self.db.close()

    def show_tables(self):
        """[展示所有表]
        """
        res = {}
        try:
            self.get_con()
            self.cursor.execute("show tables")
            res = {tp[0]: i for i, tp in enumerate(self.cursor.fetchall())}
            self.close()
        except Exception as e:
            print("show tables error --> "+str(e))
            logging.error(traceback.format_exc())
        return res

    def find_one(self, sql):
        res = None
        try:
            self.get_con()
            self.cursor.execute(sql)
            res = self.cursor.fetchone()
            self.close()
        except Exception as e:
            print("query error!" + str(e))
        return res

    def find_all(self, sql):
        res = None
        try:
            self.get_con()
            self.cursor.execute(sql)
            res = self.cursor.fetchall()
            self.close()
        except Exception as e:
            print("query error!" + str(e))
        return res

    def __insert(self, sql):
        count = 0
        try:
            self.get_con()
            count = self.cursor.execute(sql)
            self.db.commit()
            self.close()
        except Exception as e:
            print("操作失败!" + str(e))
            self.db.rollback()
        return count

    def save(self, sql):
        """[保存数据]

        Args:
            sql ([string]): [sql语句]

        Returns:
            [integer]: [操作数量]
        """
        return self.__insert(sql)

    def update(self, sql):
        """[更新数据]

        Args:
            sql ([string]): [sql语句]

        Returns:
            [integer]: [操作数量]
        """
        return self.__insert(sql)

    def delete(self, sql):
        """[删除数据]

        Args:
            sql ([string]): [sql语句]

        Returns:
            [integer]: [操作数量]
        """
        return self.__insert(sql)


if __name__ == '__main__':
    from pprint import pprint

    mysql_util = MysqlUtil()
    # print("对象实例后的属性："+json.dumps(mysql_util.__dict__))

    # 主键查询
    # sql = "select * from zccf_policy where policy_id=405075"
    # doc = mysql_util.find_one(sql)
    # print(doc)

    # 列表查询
    # sql = "select * from zccf_policy_topic"
    # docs = mysql_util.find_all(sql)
    # pprint(docs)

    # pprint(mysql_util.show_tables())
    # 插入
    # 更新
    # 删除

    # sql = "SELECT DICT_VALUE,DICT_NAME FROM zccf_sys_dict WHERE DICT_KEY='SXMK_MATTER_SUPPORT'"
    # doc = mysql_util.find_all(sql)
    # pprint(doc)

    sql = "SELECT ORGCODE,ORGNAME FROM s11t1_gov_org"
    doc = mysql_util.find_all(sql)
    pprint(doc)
