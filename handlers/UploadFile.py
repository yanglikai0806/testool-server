import json
import os
import traceback
from tornado import gen
from common import CONST
from handlers import BaseHandler, response
import time
import filecmp


class UploadFile(BaseHandler):
    def initialize(self, logger=None, conf=None):
        self.logger = logger
        self.conf = conf
        self.path = self.conf['img_path']
        self.img_url = self.conf['img_url']

    def get(self):
        self.write(response(msg="无实现"))

    @gen.coroutine
    def post(self):
        try:
            start_time = time.time()
            size = int(self.request.headers.get('Content-Length'))
            imgfile = self.request.files.get('img', '')  # request里定义的key
            zipFile = self.request.files.get("zipfile", '')
            apkFile = self.request.files.get("apkfile", "")
            targetApp = self.request.arguments.get("target_app", [b""])[0].decode()
            if imgfile:
                if size / 1000.0 > 40000:
                    self.logger.info("上传文件过大 %s" % size)
                    self.set_status(400)
                    self.write({'msg': "file is too bigger than 40M."})
                for img in imgfile:
                    # img有三个键值对可以通过img.keys()查看
                    # 分别是 'filename', 'body', 'content_type' 对应着文件名,内容(二进制)和文件类型
                    self.logger.info('上传文件 %s %s' % (img['filename'], img['content_type']))
                    with open(os.path.join(self.path, img['filename']), 'wb') as f:
                        f.write(img['body'])
                end_time = int(time.time()) - int(start_time)
                self.logger.info('上传文件 %s %s 耗时 %s' % (img['filename'], img['content_type'], end_time))
                self.write({'code': 200, "description": "finished", "img_path": self.img_url + img['filename']})
            # 接收 monkey log
            elif zipFile:
                deviceId = self.request.arguments.get("device_id", [b""])[0].decode()
                deviceName = self.request.arguments.get("device_name", [b""])[0].decode()
                self.path = os.path.join(CONST.ROOT_PATH, "statics", "monkey_log", targetApp)
                if not os.path.exists(self.path):
                    os.makedirs(self.path)
                for _file in zipFile:
                    self.logger.info('上传文件 %s %s' % (_file['filename'], _file['content_type']))
                    save_path = os.path.join(self.path, _file['filename'].replace(".zip", ""), deviceName+"_"+deviceId)
                    if not os.path.exists(save_path):
                        os.makedirs(save_path)
                    save_log_zip = os.path.join(save_path, "log.zip")
                    with open(save_log_zip, 'wb') as f:
                        f.write(_file['body'])
                    # 避免重复提交log
                    is_same = False
                    for _zf in os.listdir(save_path):
                        file_name, file_type = os.path.splitext(_zf)
                        if file_type == ".zip":
                            is_same = filecmp.cmp(save_log_zip, os.path.join(save_path, _zf), shallow=False)
                            if is_same:
                                break
                    if not is_same:
                        os.rename(save_log_zip, os.path.join(save_path, str(int(time.time()*1000))+".zip"))
                end_time = int(time.time()) - int(start_time)
                self.logger.info('上传文件 %s %s 耗时 %s' % (_file['filename'], _file['content_type'], end_time))
                self.write(json.dumps({'code': 200, "description": "上传完成"}, ensure_ascii=False))
            elif apkFile:
                self.path = os.path.join(CONST.ROOT_PATH, "statics", "apks")
                if not os.path.exists(self.path):
                    os.makedirs(self.path)
                for _file in apkFile:
                    self.logger.info('上传文件 %s %s' % (_file['filename'], _file['content_type']))

                    if not os.path.exists(self.path):
                        os.makedirs(self.path)
                    save_path = os.path.join(self.path, _file['filename'])
                    info_file = os.path.join(self.path, "info.json")
                    with open(save_path, 'wb') as f:
                        f.write(_file['body'])
                    with open(info_file, "r") as jr:  # 读取状态
                        info = json.load(jr)
                        info[_file['filename']] = 1  # 1 表示更新， 0 表示更新已消费
                    with open(info_file, "w") as jw:  # 更新状态写入
                       jw.write(json.dumps(info))
                end_time = int(time.time()) - int(start_time)
                self.logger.info('上传文件 %s %s 耗时 %s' % (_file['filename'], _file['content_type'], end_time))
                self.write(json.dumps({'code': 200, "description": "APK上传完成"}, ensure_ascii=False))
        except Exception as e:
            self.logger.error('文件上传失败 %s' % e)
            self.write({'code': 400, "description": traceback.format_exc()})

if __name__ == "__main__":
    pass




