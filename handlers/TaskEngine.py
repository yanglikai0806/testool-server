import copy
import json
import time
import traceback
from tornado import gen
from common import CONST
from common.mongo_client import MongoClient
from handlers import BaseHandler


class TaskEngine(BaseHandler):
    def initialize(self, mongo_client=None, logger=None, conf=None):
        self.logger = logger
        self.mongo_client = mongo_client if mongo_client is not None else MongoClient()
        self.conf = conf
        self.sql_test_result = mongo_client

    @gen.coroutine
    def get(self):
        '''
        获得测试用例
        :return:
        '''
        task_id = int(self.get_query_argument("task_id", "0"))
        result = self.get_query_argument("result", "")
        device_id = self.get_query_argument("device_id", "")
        task_date = self.get_query_argument("task_date", "")
        try:
            task_data, task_mode = self.task_engine(task_id, result=result, device_id=device_id, task_date=task_date)

            if task_mode == "全量":
                msg = {"code": 200, "description": "finished", "data": task_data}
            elif task_mode == "分布":
                msg = {"code": 200, "description": "continue", "data": task_data}
            elif task_mode == "调试":
                msg = {"code": 200, "description": "debug", "data": task_data}
            else:
                msg = {"code": 200, "description": "finished", "data": []}
        except Exception as e:
            self.logger.error(traceback.format_exc())
            msg = {"code": 400, "description": "error", "error": traceback.format_exc()}
        self.write(json.dumps(msg, ensure_ascii=False))

    @gen.coroutine
    def post(self):
        '''
        处理测试结果
        '''
        try:
            _dict = {1: "pass", 0: "fail", -1: "null"}  # 测试结果
            _data = json.loads(self.request.body.decode('utf-8'))
            post_data = _data.get("data", {})[0]
            result = {}
            result["apk"] = _data.get("apk", "")
            result["apk_version"] = _data.get("apk_version", "")
            result["task_id"] = _data.get("task_id", 0)
            result["task_date"] = _data.get("test_date", "")
            result["task_env"] = _data.get("test_env", "")
            # case_content = post_data.get("test_case", "")
            result["device_id"] = _data.get("device_id", "")
            result["device_name"] = _data.get("device_name", "")
            result["case_id"] = post_data.get("case_id", 0)
            result["test_log"] = post_data.get("test_log", "")
            result["test_result"] = _dict[post_data.get("test_result", -1)]
            result["case_domain"] = post_data.get("case_domain", "")
            result["img"] = post_data.get("img_url", "")
            result["result_mark"] = post_data.get("result_mark", "")
            result["result_note"] = post_data.get("result_note", "")
            result["id"] = post_data.get("id", "")
            #  更新标注结果
            if result["id"] and result["result_mark"]:
                self.update_result_mark_info(result)
                msg = {"code": 200, "desc": "标注内容已更新"}

            #  插入测试结果
            elif result["device_id"]:
                self.insert_test_result_info(result)
                msg = {"code": 200, "desc": "测试结果已写入"}
            else:
                msg = {"code": 200, "desc": "设备id为空"}
        except Exception as e:
            self.logger.error(traceback.format_exc())
            msg = {"code": 400, "desc": traceback.format_exc()}
        self.write(json.dumps(msg, ensure_ascii=False))

    def get_case_by_task_id(self, task_id, result="", device_id="", task_date=""):
        '''
        根据task id 获取任务执行用例
        :param task_id:
        :return:
        '''
        try:
            # 调试任务
            if task_id == -1:
                return self.mongo_client.find("debug_case", {"device_id": device_id})
            # 测试任务
            if not result:
                res_data = self.mongo_client.find("task_case", {"task_id": task_id, "task_date": task_date})
                case_lst = res_data[-1].get("case_list", [])
            else:
                case_lst = self.get_cases_by_result(task_id, result=result, device_id=device_id, task_date=task_date)
        except:
            case_lst = []
        return case_lst

    def get_cases_by_result(self, task_id, result="", device_id="", task_date=""):
        res_data = self.mongo_client.find("task_result", {"task_id": task_id, "task_date": task_date, "device_id": device_id, "result": result})
        case_lst = [item.get("case_id") for item in res_data]
        return case_lst

    def update_task_case_by_id(self, task_id, task_date, case_list):
        '''
        分布式执行模式下更新任务执行列表
        :param task_id:
        :param task_date:
        :param case_list:
        :return:
        '''

        try:
            self.mongo_client.update("task_case", {"task_id": task_id, "task_date": task_date}, {"case_list": case_list})
        except:
            self.logger.error(traceback.format_exc())

    def get_test_date_task_id(self, task_id):
        """
        根据测试task_id 获取最近一次任务的 date
        :param task_id:
        :return:
        """
        try:
            res_data = self.mongo_client.find("task_case", {"task_id": task_id})
            test_date = res_data[-1].get("task_date")
        except:
            test_date = ""
        return test_date

    def task_engine(self, task_id, result="", device_id="", task_date=""):
        if task_id == -1:
            debug_case = self.get_case_by_task_id(task_id, device_id=device_id)
            return debug_case, "调试"
        task_date = self.get_test_date_task_id(task_id) if not task_date else task_date
        case_list = self.get_case_by_task_id(task_id, result=result, device_id=device_id, task_date=task_date)  # 任务的id
        # self.logger.info(case_list)

        task_mode = self.get_task_info(task_id, "task_mode")
        self.logger.info("目前的任务模式是:" + task_mode)
        task_env = self.get_task_info(task_id, "task_env")
        task_apk = self.get_task_info(task_id, "apk")
        if case_list:
            # task_case_list = self.gen_cases(CONST.APK_TABLE_DICT[task_apk], case_list, task_date, task_env, task_id)
            if task_mode == "全量":  # 每个设备跑全部用例
                task_case_list = self.gen_cases(CONST.APK_TABLE_DICT[task_apk], case_list, task_date, task_env, task_id)
                return task_case_list, task_mode
            elif task_mode == "分布":  # 多个设备分布执行一个用例集合ff
                if len(case_list) > 10:
                    self.update_task_case_by_id(task_id, task_date, case_list[10:])
                    task_case_list = self.gen_cases(CONST.APK_TABLE_DICT[task_apk], case_list[:10], task_date, task_env,
                                                    task_id)
                    return task_case_list, task_mode
                else:
                    self.update_task_case_by_id(task_id, task_date, [])  # 用例清空
                    task_case_list = self.gen_cases(CONST.APK_TABLE_DICT[task_apk], case_list, task_date, task_env,
                                                    task_id)
                    return task_case_list, task_mode
            elif task_mode == "自动":
                task_condition = self.get_task_info(task_id, "task_condition")
                self.logger.info("目前的任务模式是" + task_condition)
                if task_condition.get("task_mode", "") == "分布":
                    if len(case_list) > 10:
                        self.update_task_case_by_id(task_id, task_date, case_list[10:])
                        task_case_list = self.gen_cases(CONST.APK_TABLE_DICT[task_apk], case_list[:10], task_date,
                                                        task_env,
                                                        task_id)
                        return task_case_list, "分布"
                    else:
                        self.update_task_case_by_id(task_id, task_date, [])  # 用例清空
                        task_case_list = self.gen_cases(CONST.APK_TABLE_DICT[task_apk], case_list, task_date, task_env,
                                                        task_id)
                        return task_case_list, "分布"
                else:
                    task_case_list = self.gen_cases(CONST.APK_TABLE_DICT[task_apk], case_list, task_date, task_env,
                                                    task_id)
                    return task_case_list, "全量"
        else:
            return None, None

    def get_task_info(self, task_id, info):
        res_data = self.mongo_client.find("task_plan", {"id": task_id})
        return res_data[-1].get(info, "") if res_data else ""

    def gen_cases(self, table, case_list, test_date, test_env, task_id):
        cases = []
        for _id in case_list:
            result_list = self.mongo_client.find(table, {"id": int(_id), "flag": 1})
            if result_list:
                item = result_list[0]
            else:
                continue
            domain = item.get("domain", "")
            case_content = {
                "environment": test_env,
                "test_date": test_date,
                "case_domain": domain,
                "task_id": task_id,
                "test_case": {
                    'id': item.get("id"),
                    'domain': domain,
                    'case': item.get("case", {}),
                    'check_point': item.get("check_point", {}),
                    'skip_condition': item.get("skip_condition", {})
                }
            }
            cases.append(case_content)
        return cases

    def insert_test_result_info(self, result_dic: dict):
        _id = result_dic.pop("id")
        # 先判断是否存在数据，同设备，同任务，同case
        find_dict = copy.deepcopy(result_dic)
        del find_dict["test_result"]
        self.mongo_client.update("task_result", find_dict, result_dic)

    def update_result_mark_info(self, result_dic):
        find_dict = copy.deepcopy(result_dic)
        del find_dict["test_result"]
        self.mongo_client.update("task_result", find_dict, result_dic)


if __name__ == "__main__":
    pass
