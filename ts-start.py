
import sys
import os
import logging
import logging.config

# import concurrent_log_handler  # pip install concurrent-log-handler
import traceback
import time
import yaml
import tornado.httpserver
import tornado.options
import tornado.web
import tornado.ioloop
from tornado.options import define, options
from apscheduler.schedulers.tornado import TornadoScheduler

from common.mongo_client import MongoClient
from handlers import *
from handlers.BaseActionMap import BaseActionMap
from handlers.BaseCheckpointMap import BaseCheckpointMap
from handlers.DeviceDump import DeviceDump
from handlers.DeviceRemote import DeviceRemote
from handlers.DeviceState import DeviceState
from handlers.LogHandler import LogHandler
from handlers.TaskEngine import TaskEngine
from handlers.TaskPlan import TaskPlan
from handlers.TestCases import TestCases
from handlers.DeviceManager import DeviceManager
from handlers.UploadFile import UploadFile

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)


def read_yaml():
    with open("conf/application.yaml", encoding="utf8") as f:
        execute_yaml = yaml.load(f, Loader=yaml.FullLoader)
    return execute_yaml


"""
conf value
"""
define("profile", default="local", help="run env config", type=str)
tornado.options.parse_command_line()

profile = options.profile
yaml = read_yaml()
conf = yaml[profile]
port = conf["port"]
host = conf["host"]
mongo_client = MongoClient(conf["mongo_url"])

# 初始化logging句柄
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'conf/logger.ini')
logging.config.fileConfig(log_file_path)
logger = logging.getLogger(__name__)
logger.info("初始化 logger")


# 初始化 scheduler
scheduler = TornadoScheduler()
scheduler.start()
logger.info('[Scheduler Init]APScheduler has been started')



"""
tornado application
"""


class Application(tornado.web.Application):
    def __init__(self):
        self.base_url = r"/test/"
        handlers = [
            # 测试用例
            (self.base_url + r"cases", TestCases, {"mongo_client": mongo_client, "logger": logger}),
            # 测试设备
            (self.base_url + r"devices", DeviceManager, {"mongo_client": mongo_client, "logger": logger}),
            # 设备远程
            (self.base_url + r"device_remote", DeviceRemote),
            (self.base_url + r"device_dump", DeviceDump, {"mongo_client": mongo_client, "logger": logger}),
            # 测试计划
            (self.base_url + r"task_plan", TaskPlan, {"mongo_client": mongo_client, "logger": logger}),
            # 测试执行引擎
            (self.base_url + r"task_engine", TaskEngine, {"mongo_client": mongo_client, "logger": logger}),
            # 基础操作库
            (self.base_url + r"action_map", BaseActionMap, {"mongo_client": mongo_client, "logger": logger}),
            # 基础检查库
            (self.base_url + r"check_map", BaseCheckpointMap, {"mongo_client": mongo_client, "logger": logger}),

            # API接口实现
            (self.base_url + r"api/device_state", DeviceState, {"mongo_client": mongo_client, "logger": logger}),
            (self.base_url + r"api/upload", UploadFile, {"logger": logger, "conf": conf}),
            # 日志查看接口
            (r"/test/log", LogHandler),
        ]
        settings = dict(
            blog_title="Tornado Blog",
            template_path=os.path.join(os.path.dirname(__file__), "template"),
            static_path=os.path.join(os.path.dirname(__file__), "statics"),
            static_url_prefix="/statics/",
            # ui_modules={"Entry": EntryModule},
            xsrf_cookies=False,
            login_url="/auth/login",
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            debug=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)



def start_crontab():
    pass
    # time.sleep(60)
    # url_task = "http://%s:%s/test/task_plan?add_jobs=yes" % (host, port)
    # res = requests.get(url_task)
    # time.sleep(1)
    # logger.info("启动定时任务 %s" % res.text)
    # logger.info("启动定时任务完成 %s" % url_task)

def main():
    http_server = tornado.httpserver.HTTPServer(Application(), max_buffer_size=504857600)
    http_server.listen(port, address=host)
    # http_server.start(4)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    import threading
    threading.Thread(target=start_crontab).start()
    main()
