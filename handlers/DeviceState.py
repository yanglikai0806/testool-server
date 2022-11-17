import json
import traceback
import time
from common.mongo_client import MongoClient
from handlers import BaseHandler, response


class DeviceState(BaseHandler):

    def initialize(self, mongo_client=None, logger=None):
        self.logger = logger
        self.mongo_client = mongo_client if mongo_client is not None else MongoClient()
        self.coll = "devices"

    def get(self):
        device_id = self.get_query_argument("device_id", "")
        device_data = {}
        if device_id:
            device_data = self.get_device_info(device_id)

        self.logger.info('query[%s]  处理时间 time[%s]' % (self.request.full_url, self.request.request_time()))
        self.write(response(data=device_data))

    def post(self):
        try:
            # self.logger.info(json.dumps(self.request.body.decode('utf-8'), ensure_ascii=False))
            rep_str = self.save_device_state(self.request.body.decode('utf-8'))
            # self.logger.info('query[%s]  处理时间 time[%s]' % (self.request.full_url, self.request.request_time()))
            self.write(response(desc=rep_str, code=200))
        except Exception as e:
            self.logger.error(e)
            self.write(response(desc="error:" + str(e), code=400))

    def save_device_state(self, post_data):
        # 检查基本数据结构
        try:
            # idle:{-2: "异常", -1: "离线", 0: "占用", 1: "空闲", 2: "在线"}
            post_data = json.loads(post_data)
            _idle = post_data.get("idle", -1)
            if str(_idle).lower() == "true":
                post_data['idle'] = 1
            elif str(_idle).lower() == "false":
                post_data['idle'] = 0
            else:
                post_data['idle'] = int(_idle)
        except:
            self.logger.error(traceback.format_exc())
            return "json格式化错误"

        # 验证数据
        must_key = ["device_id", "idle"]
        lost_key = [key for key in must_key if key not in post_data]
        if lost_key:
            return '缺少必要参数 %s' % lost_key
        res_device = self.mongo_client.find(self.coll, {"device_id": post_data.get("device_id")})
        if len(res_device) > 0:
            result = self.mongo_client.update(self.coll, {"device_id": post_data.get("device_id")}, post_data)
        else:
            result = self.mongo_client.insert(self.coll, post_data)
        if result:
            return "success"
        return "update failed: " + str(result)

    def get_device_info(self, device_id):
        device_info = self.mongo_client.find(self.coll, {"device_id": device_id})
        return device_info[0] if device_info else {}
