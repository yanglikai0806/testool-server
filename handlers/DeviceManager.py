
import json
import os
import threading
import time
import traceback
from common.mongo_client import MongoClient
from common import Adb
from handlers import BaseHandler, response
from tornado import gen
from websocket import create_connection

class DeviceManager(BaseHandler):
    def initialize(self, mongo_client=None, logger=None):
        self.logger = logger
        self.mongo_client = mongo_client if mongo_client is not None else MongoClient()
        self.coll = "devices"

    @gen.coroutine
    def get(self):
        # self.render("display/device_manager.html", device_lst=self.get_remote_devices({}))
        try:
            self.write(response(data=self.get_remote_devices({})))
        except:
            traceback.print_exc()

    def post(self):
        _data = json.loads(self.request.body.decode('utf-8'))
        data = _data.get("data", {})
        device_ip = data.get("device_ip", "")
        task_id = data.get("task_id", "")
        owner = data.get("owner", "")
        action = data.get("action", "")
        # 设备重连
        # if action == "reconnect":
            # res = Adb.adb(cmd="connect " + device_ip+":5555")
            # if "connected to " + device_ip in res:
            #     Adb.shell(sn=device_ip + ":5555", cmd='am start-foreground-service -n com.kevin.testool/.MyIntentService -a com.kevin.testool.action.execute_step --es EXECUTE_STEP [{"unlock":"0000"}]')  # 解锁
            #     time.sleep(5)
            #     if isDeviceOnline(device_ip) != "true":
            #         Adb.shell(sn=device_ip + ":5555", cmd="am force-stop com.kevin.testool")  # 先启动测试工具
            #         time.sleep(5)
            #         Adb.shell(sn=device_ip + ":5555", cmd="am start -n com.kevin.testool/.activity.MainActivity")  # 先启动测试工具
            #         # res = Adb.shell(device_ip + ":5555", "am start-foreground-service -n com.kevin.testool/.service.DeviceRemoteService")  # 重启远程服务
            #         # Adb.shell(sn=device_ip + ":5555", cmd='am start-foreground-service -n com.kevin.testool/.MyIntentService -a com.kevin.testool.action.execute_step --es EXECUTE_STEP [{"text":"立即开始"}]')  # 重启远程服务
            #         time.sleep(3)
            #     Adb.adb(cmd="disconnect " + device_ip + ":5555")  # 解除连接
            #     self.write(response({"code": 200, "action": action, "content": res}))
            # else:
            #     self.write(response({"code": 200, "action": action, "content": "设备无法连接：" + res}))
        # 设备重启
        if action == "reboot":
            res = Adb.adb(cmd="connect " + device_ip)
            if "connected to " + device_ip in res:
                Adb.adb(sn=device_ip + ":5555", cmd="reboot")
                time.sleep(3)
                # res = Adb.adb(cmd="disconnect " + device_ip + ":5555")  # 解除连接
                self.write(response(**{"code": 200, "action": action, "content": "正在重启"}))
            else:
                self.write(response(**{"code": 200, "action": action, "content": "设备无法重启：" + res}))
        # 设备是否连接正常
        elif action == "isconnect":
            self.write(response(**{"code": 200, "action": action, "content": isDeviceOnline(device_ip)}))
        # 获取所有连接状态的设备
        elif action == "connected":
            self.write(response(**{"code": 200, "action": action, "content": self.get_connect_devices()}))
        # 移除设备
        elif action == "remove":
            self.write(response(**{"code": 200, "action": action, "content": self.delete_device_by_ip(device_ip)}))
        # 任务更新
        elif action == "task_update":
            self.write(response(**{"code": 200, "action": action, "content": self.update_device_task_id(device_ip, task_id)}))
        # 设备独占
        elif action == "occupy":
            self.write(response(**{"code": 200, "action": action, "content": self.update_device_owner(device_ip, owner)}))

    def get_remote_devices(self, find_dict) -> list:
        device_lst = []
        device_data = self.mongo_client.find(self.coll, find_dict)
        # keys = ["device_id", "device_name", "device_type", "battery", "apk_version", "idle", "device_ip", "device_info", "task_id", "owner"]
        for item in device_data:
            ip = str(item.get("device_ip", ""))
            if len(ip) > 7:  # 判断device_ip
                # 过滤设备
                update_date = item.get("update_time", item.get("create_time"))
                update_time = time.mktime(time.strptime(update_date.split(".")[0], "%Y-%m-%d %H:%M:%S"))
                if time.time() - update_time > 20:  # 设备信息更新时间大于20s则认为设备已离线（测试工具开启远程后会每个10秒内上传设备状态）
                    item["idle"] = -1
                device_lst.append(item)

        return device_lst

    def get_connect_devices(self, find_dict) -> list:
        device_lst = []
        device_data = self.mongo_client.find(self.coll, find_dict)
        # keys = ["device_id", "device_name", "device_type", "battery", "apk_version", "idle", "device_ip", "device_info", "task_id", "owner"]
        for item in device_data:
            ip = str(item.get("device_ip", ""))
            if len(ip) > 7:  # 判断device_ip
                # 过滤设备
                update_date = item.get("update_time", "")
                update_time = time.mktime(time.strptime(update_date, "%Y-%m-%d %H:%M:%S"))
                if time.time() - update_time < 10:  # 设备信息更新时间小于10s则认为设备在线（测试工具开启远程后会每个10秒内上传设备状态）
                    item["idle"] = -1
                    device_lst.append(item)
        return device_lst

    def get_device_info_by_ip(self, ip):
        device_data = self.mongo_client.find(self.coll, {"device_ip": ip})
        return device_data

    def delete_device_by_ip(self, ip):
        res = self.mongo_client.delete(self.coll, {"device_ip": ip})
        return "success" if res > 0 else "failed: "+res

    def update_device_task_id(self, ip, task_id):
        res = self.mongo_client.update(self.coll, {"device_ip": ip}, {"task_id": task_id})
        return "success" if res > 0 else "failed: "+res

    def update_device_owner(self, ip, owner):
        res = self.mongo_client.update(self.coll, {"device_ip": ip}, {"owner": owner})
        return "success" if res > 0 else "failed: "+res

threadLock = threading.Lock()
threads = []

def isDeviceOnline(ip):
    try:
        ws = create_connection("ws://%s:9999" % ip, timeout=15)
        ws.close()
        return "true"
    except Exception as e:
        traceback.print_exc()
        return "false"
    # ws.send(json.dumps({"msg": "connect"}))
    # result = ws.recv()
def getAvailableDevice(ip,device_infos:dict,dev_list:list):
    if isDeviceOnline(ip) == "true":
        threadLock.acquire()  # 获取线程锁
        dev_list.append(device_infos)
        threadLock.release()  # 释放线程锁
if __name__ == "__main__":
    a = isDeviceOnline("127.0.0.1")
    print(a)