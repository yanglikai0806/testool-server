# @Date : 2021/2/19
# @Author : 杨立凯
# @description : 基础操作 展示列表
import json
import os
import traceback

from common.mongo_client import MongoClient
from handlers import BaseHandler, response
import tornado

class BaseActionMap(BaseHandler):
    def initialize(self, mongo_client=None, logger=None, conf=None):
        self.logger = logger
        self.mongo_client = mongo_client if mongo_client is not None else MongoClient()
        self.conf = conf

    def get(self):
        id = self.get_query_argument("id", "")
        name = self.get_query_argument("name", "")
        if id:
            res = self.get_action_by_id(id)
            if res:
                self.write(response(code=200, data=res))
            else:
                self.write(response(code=200, desc="id不存在"))
            return

        if name:
            self.logger.info(name)
            res = self.get_action_by_name(name)
            if res:
                self.write(res)
            else:
                self.write(json.dumps({"code": 200, "desc": "name不存在"}, ensure_ascii=False))
            return
        self.write(json.dumps({"code": 200, "data": self.get_action_lst()}, ensure_ascii=False))

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
                self.write(response(code=200, desc="success"))
            except Exception as e:
                self.logger.error(traceback.format_exc())
                self.write(response(code=200, desc=traceback.format_exc()))

    def get_action_lst(self) -> list:
        action_lst = self.mongo_client.find("action_map", {})
        return action_lst

    def store_action_data(self, id, action, name):
        res_data = self.mongo_client.update("action_map", {"id": id}, {"action": action, "name": name})
        return res_data

    def get_action_by_id(self, id):
        res_data = self.mongo_client.find("action_map", {"id": id})
        return res_data[-1].get("action", "") if res_data else ""

    def get_action_by_name(self, tag):
        res_data = self.mongo_client.find("action_map", {"name": tag})
        return res_data[-1].get("action", "") if res_data else ""
