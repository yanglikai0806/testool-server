# @Date : 2021/2/19
# @Author : 杨立凯
# @description : activity 展示列表
import json
import os
import traceback

from handlers import BaseHandler

class ActivityMap(BaseHandler):
    def initialize(self, sql=None, logger=None, conf=None):
        self.logger = logger
        self.sql_pool = sql
        self.conf = conf

    def get(self):
        id = self.get_query_argument("id", "")
        name = self.get_query_argument("name", "")
        if id:
            res = self.get_activity_by_id(id)
            if res:
                self.write(res[0][0])
            else:
                self.write(json.dumps({"code": 200, "desc": "id不存在"}, ensure_ascii=False))
            return

        if name:
            index = 0
            if "#" in name:
                index = int(name.split("#")[1])
            res = self.get_activity_by_name(name, index)
            if res:
                self.write(res)
            else:
                self.write(json.dumps({"code": 200, "desc": "name不存在"}, ensure_ascii=False))
            return
        self.logger.info('query[%s]  处理时间 time[%s]' % (self.request.full_url, self.request.request_time()))
        self.render("display/activity_map.html", activity_list=self.get_activity_lst())

    def post(self):
        try:
            data = json.loads(self.request.body.decode('utf-8'))
        except Exception as e:
            traceback.print_exc()
            data = eval(self.request.body.decode('utf-8'))
        _data = data.get("data")
        if _data:
            id = _data["id"]
            activity = _data.get("activity", "")
            name = _data["name"]
            try:
                self.store_activity_data(id, activity, name)
                self.logger.info('query[%s]  处理时间 time[%s]' % (self.request.full_url, self.request.request_time()))
                self.write({"code": 200})
            except Exception as e:
                print(str(e))
                self.write({"code": 200})

    def get_activity_lst(self) -> list:
        activity_lst = []
        conn, cursor = self.sql_pool.get_connect()
        res_data = self.sql_pool.execute(cursor, "SELECT id,name,activity,date_format(date, '%Y-%m-%d %H:%i:%s') FROM `activity_map`;", {})
        for data in res_data:
            activity_lst.append({"id": data[0], "name": data[1], "activity": data[2], "date": str(data[3])})
        self.sql_pool.close_connect(conn)
        return activity_lst

    def store_activity_data(self, id, activity, name):
        conn, cursor = self.sql_pool.get_connect()
        if int(id) > -1:
            if activity:
                sql_cmd = "UPDATE `activity_map` SET activity='%s', name='%s', date=NOW() WHERE id=%s;" % (activity, name, id)
            else:
                sql_cmd = "UPDATE `activity_map` SET name='%s', date=NOW() WHERE id=%s;" % (name, id)
        else:
            sql_cmd = "INSERT IGNORE INTO `activity_map` (`activity`, `name`, `date`) VALUES ('%s', '%s', NOW());" % (activity, name)
        self.logger.info(sql_cmd)
        res_data = self.sql_pool.execute(cursor, sql_cmd, {})
        self.logger.info(res_data)
        self.sql_pool.close_connect(conn)
        return res_data

    def get_activity_by_id(self, id):
        conn, cursor = self.sql_pool.get_connect()
        res_data = self.sql_pool.execute(cursor,
                                         "SELECT activity FROM `activity_map` WHERE `id`=%s;" % id,
                                         {})
        self.sql_pool.close_connect(conn)
        return res_data

    def get_activity_by_name(self, tag, index=0):
        conn, cursor = self.sql_pool.get_connect()
        res_data = self.sql_pool.execute(cursor,
                                         "SELECT activity FROM `activity_map` WHERE `name`='%s';" % tag,
                                         {})
        self.sql_pool.close_connect(conn)
        return res_data[0][index]