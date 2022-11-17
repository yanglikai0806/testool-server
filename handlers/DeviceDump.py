import json
import traceback

from common import dump
from common.mongo_client import MongoClient
from handlers import BaseHandler, response


class DeviceDump(BaseHandler):
    def initialize(self, mongo_client=None, logger=None):
        self.logger = logger
        self.mongo_client = mongo_client if mongo_client is not None else MongoClient()
        self.coll = "device_dump"

    def get(self):
        device_id = self.get_query_argument("device_id", "")
        if device_id:
            try:
                b64data, dump_json = self.get_device_dump(device_id)
                self.render("device_dump.html", activity="activity", device_id=device_id, screen=b64data,
                            dump=dump_json)
            except:
                self.write(response(msg=traceback.format_exc()))
        else:
            self.logger.info("缺少device_id")


    def post(self):
        data = json.loads(self.request.body.decode('utf-8'))
        print(data)
        screen = data.get("screen", "")
        dump_xml = data.get("dump", "")
        device_id = data.get("device_id", "")
        if screen and dump_xml and device_id:
            self.update_device_dump(device_id, screen, json.dumps(dump.get_android_hierarchy2(dump_xml), ensure_ascii=False))
            self.write(response(code=200, msg="finished"))
        else:
            self.write(response(code=200, msg="empty"))

    def update_device_dump(self, _device_id, screen, dump):
        self.mongo_client.update(self.coll, {"device_id": _device_id}, {"device_id": _device_id, "screen": screen, "dump":dump}, upsert=True)

    def get_device_dump(self, _device_id):
        result = self.mongo_client.find(self.coll, {"device_id": _device_id})[0]
        return result.get("screen", ""), result.get("dump", "")