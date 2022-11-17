# @Date : 2021/2/19
# @Author : 杨立凯
# @description : 基础操作 展示列表
import json
import os
import traceback

from handlers import BaseHandler
import tornado

class BaseActionMap(BaseHandler):
    def initialize(self, sql=None, logger=None, conf=None):
        self.logger = logger
        self.sql_pool = sql
        self.conf = conf

    def get(self):
        id = self.get_query_argument("id", "")
        name = self.get_query_argument("name", "")
        if id:
            res = self.get_action_by_id(id)
            if res:
                self.write(res[0][0])
            else:
                self.write(json.dumps({"code": 200, "desc": "id不存在"}, ensure_ascii=False))
            return

        if name:
            print("-------------------------------------")
            self.logger.info(name)
            res = self.get_action_by_name(name)
            if res:
                self.write(res[0][0])
            else:
                self.write(json.dumps({"code": 200, "desc": "name不存在"}, ensure_ascii=False))
            return
        self.logger.info('query[%s]  处理时间 time[%s]' % (self.request.full_url, self.request.request_time()))
        self.render("display/action_map.html", action_list=self.get_action_lst())

    def post(self):
        try:
            data = json.loads(self.request.body.decode('utf-8'))
        except Exception as e:
            traceback.print_exc()
            data = eval(self.request.body.decode('utf-8'))
        _data = data.get("data")
        if _data:
            id = _data["id"]
            action = _data.get("action", "")
            name = _data["name"]
            try:
                self.store_action_data(id, action, name)
                self.logger.info('query[%s]  处理时间 time[%s]' % (self.request.full_url, self.request.request_time()))
                self.write({"code": 200})
            except Exception as e:
                print(str(e))
                self.write({"code": 200})

    def get_action_lst(self) -> list:
        action_lst = []
        conn, cursor = self.sql_pool.get_connect()
        res_data = self.sql_pool.execute(cursor, "SELECT id,`name`,`action`,date_format(date, '%Y-%m-%d %H:%i:%s') FROM `action_map`;", {})
        for data in res_data:
            action_lst.append({"id": data[0], "name": data[1], "action": data[2], "date": str(data[3])})
        self.sql_pool.close_connect(conn)
        return action_lst

    def store_action_data(self, id, action, name):
        conn, cursor = self.sql_pool.get_connect()
        action = action.strip().replace("\n", "")
        if int(id) > -1:
            if action:
                sql_cmd = "UPDATE `action_map` SET `action`='%s', name='%s', date=NOW() WHERE id=%s;" % (action, name, id)
            else:
                sql_cmd = "UPDATE `action_map` SET name='%s', date=NOW() WHERE id=%s;" % (name, id)
        else:
            sql_cmd = "INSERT IGNORE INTO `action_map` (`action`, `name`, `date`) VALUES ('%s', '%s', NOW());" % (action, name)
        self.logger.info(sql_cmd)
        res_data = self.sql_pool.execute(cursor, sql_cmd, {})
        self.logger.info(res_data)
        self.sql_pool.close_connect(conn)
        return res_data

    def get_action_by_id(self, id):
        conn, cursor = self.sql_pool.get_connect()
        res_data = self.sql_pool.execute(cursor,
                                         "SELECT `action` FROM `action_map` WHERE `id`=%s;" % id,
                                         {})
        self.sql_pool.close_connect(conn)
        return res_data

    def get_action_by_name(self, tag):
        conn, cursor = self.sql_pool.get_connect()
        res_data = self.sql_pool.execute(cursor,
                                         "SELECT `action` FROM `action_map` WHERE `name`='%s';" % tag,
                                         {})
        self.sql_pool.close_connect(conn)
        return res_data
