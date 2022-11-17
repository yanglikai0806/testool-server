from common.mongo_client import MongoClient
from handlers import BaseHandler, response
import traceback
import json


class TestCases(BaseHandler):
    def initialize(self, mongo_client=None, logger=None):
        self.logger = logger
        self.mongo_client = mongo_client if mongo_client is not None else MongoClient()

    def get(self):
        try:
            self.logger.info(self.request.full_url)
            table = self.get_query_argument("table", 'test_cases')
            domain = self.get_query_argument("domain", '')
            domain = '' if domain == 'all' else domain
            flag = self.get_query_argument("flag", "1")
            find_dict = {"domain": domain, "flag": int(flag)} if domain else {"flag": int(flag)}
            _id = self.get_query_argument("id", "")
            if _id:
                find_dict["id"] = int(_id)
            case_dict = self.get_cases(table, find_dict)
            self.write(response(data=case_dict, desc="ok"))
        except Exception as e:
            self.logger.error(e)
            self.logger.error(traceback.format_exc())
            self.write(response(data={}, desc="error", code=400))

    def post(self):
        _data = json.loads(self.request.body.decode('utf-8'))
        case_data = _data.get("case_data", {})
        table = _data.get("table", "test_cases")
        what = _data.get("what", "update")
        res = {}
        if what == "create":
            res = self.create_case(table, case_data)
        elif what == "update":
            find_case = _data.get("find", {})
            try:
                res = self.update_case(table, find_case, case_data)
            except:
                traceback.print_exc()
        self.write(response(data=res, desc="ok"))

    def get_cases(self, table, find_dict):
        return self.mongo_client.find(table, find_dict)

    def create_case(self, table, case_body):
        return self.mongo_client.insert(table, case_body)

    def update_case(self, table, find_case, update_case):
        if not find_case:
            return
        return self.mongo_client.update(table, find_case, update_case)

    def get_domains(self, table):
        pass
