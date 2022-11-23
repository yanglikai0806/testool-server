import json
import os
import tornado.web
from tornado import gen
from common import CONST


class BaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers', '*')
        self.set_header('Access-Control-Max-Age', 3600)
        # self.set_header('Content-type', 'application/json')
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        # self.set_header('Access-Control-Allow-Headers',  # '*') 'authorization, Authorization, Content-Type,
        # Access-Control-Allow-Origin, Access-Control-Allow-Headers, X-Requested-By, Access-Control-Allow-Methods')

    def options(self):
        pass


def response(data=None, code=200, desc="", **kwargs):
    return json.dumps({**{"data": data, "code": code, "desc": desc}, **kwargs}, ensure_ascii=False, default=str)
