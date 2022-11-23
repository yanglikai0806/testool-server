# @Date : 2021/2/19
# @Author : 杨立凯
# @description : 基础操作 展示列表
import json
import traceback

from common.mongo_client import MongoClient
from handlers import BaseHandler, response


class BaseCheckpointMap(BaseHandler):
    def initialize(self, mongo_client=None, logger=None, conf=None):
        self.logger = logger
        self.mongo_client = mongo_client if mongo_client is not None else MongoClient()
        self.conf = conf

    def get(self):
        id = self.get_query_argument("id", "")
        name = self.get_query_argument("name", "")
        if id:
            res = self.get_check_by_id(id)
            if res:
                self.write(response(code=200, data=res))
            else:
                self.write(response(code=200, desc="id不存在"))
            return

        if name:
            res = self.get_check_by_name(name)
            if res:
                self.write(response(code=200, data=res))
            else:
                self.write(response(code=200, desc="name不存在"))
            return
        self.logger.info('query[%s]  处理时间 time[%s]' % (self.request.full_url, self.request.request_time()))
        self.write(response(code=200, data=self.get_check_lst()))

    def post(self):
        try:
            data = json.loads(self.request.body.decode('utf-8'))
        except Exception as e:
            self.logger.error(traceback.format_exc())
            data = eval(self.request.body.decode('utf-8'))
        _data = data.get("data")
        if _data:
            id = _data["id"]
            check = _data.get("check", "")
            name = _data["name"]
            try:
                self.store_check_data(id, check, name)
                self.logger.info('query[%s]  处理时间 time[%s]' % (self.request.full_url, self.request.request_time()))
                self.write(response(code=200, desc="success"))
            except Exception as e:
                self.logger.error(traceback.format_exc())
                self.write(response(code=400, desc=traceback.format_exc()))

    def get_check_lst(self) -> list:
        check_lst = self.mongo_client.find("check_map", {})
        return check_lst

    def store_check_data(self, id, check, name):

        res_data = self.mongo_client.update("check_map", {"id": id}, {"check": check, "name": name})
        return res_data

    def get_check_by_id(self, id):
        res_data = self.mongo_client.find("check_map", {"id": id})
        return res_data[-1] if res_data else ""

    def get_check_by_name(self, tag):
        res_data = self.mongo_client.find("check_map", {"name": tag})
        return res_data[-1] if res_data else ""
