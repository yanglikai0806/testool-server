# @Date : 2020/10/10
# @Author : 杨立凯
# @description : 图片展示
import json
import os
import traceback

from common.mongo_client import MongoClient
from handlers import BaseHandler, response
import tornado

class ImageShop(BaseHandler):
    def initialize(self, mongo_client=None, logger=None, conf=None):
        self.logger = logger
        self.mongo_client = mongo_client if mongo_client is not None else MongoClient()
        self.conf = conf

    def get(self):
        id = self.get_query_argument("id", "")
        tag = self.get_query_argument("tag", "")
        if id:
            res = self.get_image_by_id(id)
            if res:
                self.write(res[0][0])
            else:
                self.write(json.dumps({"code": 200, "desc": "id不存在"}, ensure_ascii=False))
            return

        if tag:
            index = 0
            if "#" in tag:
                index = int(tag.split("#")[1])
            res = self.get_image_by_tag(tag, index)
            if res:
                self.write(res)
            else:
                self.write(json.dumps({"code": 200, "desc": "tag不存在"}, ensure_ascii=False))
            return
        self.logger.info('query[%s]  处理时间 time[%s]' % (self.request.full_url, self.request.request_time()))
        self.write(response(data=self.get_image_lst()))

    def post(self):
        try:
            data = json.loads(self.request.body.decode('utf-8'))
        except Exception as e:
            traceback.print_exc()
            data = eval(self.request.body.decode('utf-8'))
        _data = data.get("data")
        if _data:
            id = _data["id"]
            image = _data.get("image", "")
            tag = _data["tag"]
            try:
                self.store_image_data(id, image, tag)
                self.logger.info('query[%s]  处理时间 time[%s]' % (self.request.full_url, self.request.request_time()))
                self.write({"code": 200, "msg": "finished"})
            except Exception as e:
                self.write({"code": 400, "msg": traceback.format_exc()})

    def get_image_lst(self) -> list:
        image_lst = self.mongo_client.find("image_shop", {})
        return image_lst

    def store_image_data(self, id, image, tag):
        res_data = self.mongo_client.update("image_shop", {"id": id}, {"image": image, "tag": tag})
        return res_data

    def get_image_by_id(self, id):
        res_data = self.mongo_client.find("image_shop", {"id": id})
        return res_data[0].get("image")

    def get_image_by_tag(self, tag, index=0):
        res_data = self.mongo_client.find("image_shop", {"tag": tag})
        return res_data[index].get("image")