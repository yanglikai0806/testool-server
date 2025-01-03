import json
import os
import re
import threading
import time
import traceback
from datetime import datetime

from apscheduler.triggers.interval import IntervalTrigger
from tornado import gen
from websocket import create_connection

from common import CONST
from common.mongo_client import MongoClient
from handlers import BaseHandler, response
from handlers.DeviceManager import DeviceManager

class TaskPlan(BaseHandler):
    def initialize(self, mongo_client=None, logger=None, scheduler=None, conf=None):
        self.logger = logger
        self.mongo_client = mongo_client if mongo_client is not None else MongoClient()
        self.conf = conf
        self.scheduler = scheduler
        self.sql_test_result = mongo_client
        self.table_task_plan = "task_plan"
        self.table_task_case = "task_case"
    def get(self):
        task_id = int(self.get_query_argument("task_id", "0"))
        task_date = self.get_query_argument("task_date", "")
        case_id = self.get_query_argument("case_id", "")
        device_id = self.get_query_argument("device_id", "")
        add_job = self.get_query_argument("add_jobs", "")  # add_job不为空时，激活已执行的自动任务
        get_task_info = self.get_query_argument("get_task_info", "")  # get_task_info不为空时，返回任务详情信息
        if add_job:  # 激活已执行的自动任务，用于重启服务时初始化
            self.add_jobs()
            self.write(response(code=200, desc="激活自动任务"))
            return
        if task_id:
            task_date_list = self.get_task_date(task_id)
            task_date_prev = task_date_list[-2] if len(task_date_list) > 1 else ""  # 获取上一次测试执行的日期
            # 获取某条测试log数据
            if all([task_id, task_date, case_id, device_id]):
                try:
                    test_log, img, result_mark, result_note = self.get_test_case_log(task_id, task_date, task_date_prev, device_id, case_id)
                    self.write(response(code=200, data={"test_log": test_log, "img": img, "result_mark": result_mark, "result_note": result_note}))
                except:
                    self.logger.error(traceback.format_exc())
            # 获取某个测试任务的详情
            elif get_task_info:
                task_info = self.get_task_info(task_id)
                self.write(str(task_info.get(get_task_info, task_info)).strip())
                self.write(response(code=200, desc=str(task_info.get(get_task_info, task_info)).strip()))
            # 打开测试结果展示页面
            else:
                try:
                    report_html = "task_report.html"
                    if not task_date:
                        task_date = task_date_list[-1] if task_date_list else ""
                    device_list = self.get_task_devices(task_id, task_date)
                    task_result_data, task_result_info = self.get_task_result(task_id, task_date, task_date_prev,device_list)
                    case_id_list = self.get_task_cases_id(task_id)
                    self.render(report_html, device_list=device_list, case_id_list=case_id_list, task_result_data=task_result_data, task_result_info=task_result_info, date_list=task_date_list[::-1])
                    # self.write(response(code=200, data={"device_list": device_list, "case_id_list":case_id_list, "task_result_data": task_result_data,
                    #                                    "task_result_info": task_result_info, "date_list":task_date_list[::-1]}))
                except Exception as e:
                    self.logger.error(traceback.format_exc())
                    self.write(response(code=400, desc=traceback.format_exc()))

        # 获取数据
        query = self.get_query_argument("query", "")
        if query:
            apk = self.get_query_argument("apk", "")
            data = {}
            if "task_list" in query or query == "all":
                data["task_list"] = self.get_task_list()
            if "apk_map" in query or query == "all":
                data["apk_map"] = CONST.APP_DICT
            if "case_domain_map" in query or query == "all":
                case_domain_map, case_id_map = self.get_case_map(apk=apk, table=CONST.APK_TABLE_DICT.get(apk, ""))
                data["case_domain_map"] = case_domain_map
                data["case_id_map"] = case_id_map
            self.write(response(code=200, data=data))

    @gen.coroutine
    def post(self):
        '''
        任务创建
        {"apk_name":"", "case_list":[], "task_mode":"", "task_id":""}
        :return:
        '''
        _data = json.loads(self.request.body.decode('utf-8'))
        post_data = _data.get("data", {})
        apk_name = post_data.get("apk", "")
        case_list = post_data.get("case_list", [])
        case_map = post_data.get("case_map", {})
        task_mode = post_data.get("task_mode", "全量")
        task_env = post_data.get("task_env", "production")
        task_owner = post_data.get("task_owner", "")
        task_note = post_data.get("task_note", "")
        task_status = post_data.get("task_status", 0)  # -1 下线; 0 空闲；1 执行； 2 已完成; 3 更新;
        task_condition = post_data.get("task_condition", "")
        task_id = int(post_data.get("task_id", -1))
        if task_id == -1:
            try:
                self.create_task({"apk": apk_name, "case_list": case_list, "case_map": case_map,"task_mode": task_mode, "task_env": task_env,
                                  "task_owner": task_owner, "task_note": task_note, "task_status": 0})
                msg = {"code": 200, "desc": "新建创建完成"}
            except Exception as e:
                msg = {"code": 400, "desc": "新建任务异常：" + traceback.format_exc()}
        else:
            try:
                if task_status == 1:  # 启动任务
                    if case_list:
                        if task_mode == "自动":
                            self.add_scheduler_job(eval(task_condition), task_id, case_list)
                            msg = {"code": 200, "desc": "测试任务已执行"}
                        else:
                            self.insert_task_case_table(task_id, case_list)
                            msg = {"code": 200, "desc": "已生成测试用例表"}
                    else:
                        msg = {"code": 200, "desc": "测试用例为空"}
                elif task_status == -1:  # 删除任务
                    self.modify_task(task_id, {"task_status": -1})
                    msg = {"code": 200, "desc": "任务已删除"}
                elif task_status == 2:
                    if task_mode == "自动":  # 任务完成，只实现条件模式下任务终止，对于普通任务只更新状态，无需操作
                        try:
                            self.scheduler.remove_job(str(task_id))
                        except Exception as e:
                            self.logger.error(traceback.format_exc())
                    else:
                        self.modify_task(task_id, {"task_status": 2})
                    msg = {"code": 200, "desc": "任务已终止"}
                elif task_status == 3:  # 编辑任务
                    modify_data = {"apk": apk_name, "case_list": case_list, "case_map": case_map, "task_mode": task_mode, "task_env": task_env,
                                  "task_owner": task_owner, "task_note": task_note}
                    self.modify_task(task_id, modify_data)
                    msg = {"code": 200, "desc": "更新任务"}

                else:
                    msg = {"code": 200, "desc": "无实现"}
                self.update_task_status(task_id, task_status)
            except:
                msg = {"code": 400, "desc": "任务运行异常：" + traceback.format_exc()}
        self.write(json.dumps(msg, ensure_ascii=False))

    def create_task(self, data_body):
        '''
        创建测试任务
        :param data_body:
        :return:
        '''
        data_body_temp = {
            "apk": "",
            "case_list": [],
            "task_mode": "",
            "task_env": "",
            "task_owner": "",
            "task_note": "",
            "task_date": "",
            "task_status": ""
        }

        return self.mongo_client.insert(self.table_task_plan, data_body)

    def modify_task(self, task_id, data_modify: dict):
        return self.mongo_client.update(self.table_task_plan, {"id": task_id}, data_modify)

    def update_task_status(self, task_id, status):
        '''
        更新任务状态
        :param task_id:
        :param status:
        :return:
        '''
        return self.mongo_client.update(self.table_task_plan, {"id": task_id}, {"task_status": status})

    def update_task_case(self, task_id, case_list):
        '''
        更新测试用例
        :param task_id:
        :param status:
        :return:
        '''
        return self.mongo_client.update(self.table_task_plan, {"id": task_id}, {"case_list": case_list})

    def update_task_condition(self, task_id, task_condition:str):
        '''
        更新测试执行条件
        :param task_id:
        :param status:
        :return:
        '''
        return self.mongo_client.update(self.table_task_plan, {"id": task_id}, {"task_condition": task_condition})

    def get_task_date(self, task_id) -> list:
        '''
        根据任务id获得任务启动日期列表
        :param task_id:
        :return:
        '''
        res_lst = []
        try:
            res_lst = self.mongo_client.find(self.table_task_plan, {"id": task_id})
        except:
            self.logger.error(traceback.format_exc())
        return [res.get("task_date", "") for res in res_lst]

    def insert_task_case_table(self, task_id, case_list):
        task_date = time.strftime("%Y-%m-%d_%H-%M-%S")
        self.mongo_client.insert(self.table_task_case, {"task_id": task_id, "task_date": task_date, "case_list": case_list, "case_num": len(case_list)})

    def get_task_list(self):
        '''
        获取未下线任务列表
        :return:
        '''
        task_lst = self.mongo_client.find(self.table_task_plan, {"task_status": {"$gte": 0}})
        return task_lst

    def get_task_info(self, task_id):
        '''
        获取任务详情
        :return:
        '''
        task_info = self.mongo_client.find(self.table_task_plan, {"id": task_id})
        return task_info[0] if task_info else ""

    def get_task_cases_id(self, task_id) -> list:
        '''
        获取任务用例列表
        :param task_id:
        :return:
        '''
        return self.get_task_info(task_id).get("case_list", [])

    def get_case_map(self, apk="", table=""):
        case_domain_map = {}
        case_id_map = {}
        if apk and table:
            domain_list = self.mongo_client.distinct(table, "domain", {})
            for item in domain_list:
                _domain = item
                _case_list = self.mongo_client.find(table, {"domain": _domain, "flag": 1})
                case_id_list = [cs.get("id") for cs in _case_list]
                case_id_map[_domain] = case_id_list
            case_domain_map[apk] = domain_list
        return case_domain_map, case_id_map

        # for apk, table in CONST.APK_TABLE_DICT.items():
        #     domain_list = self.mongo_client.distinct(table, "domain", {})
        #     for item in domain_list:
        #         _domain = item
        #         _case_list = self.mongo_client.find(table, {"domain": _domain, "flag": 1})
        #         case_id_list = [cs.get("id") for cs in _case_list]
        #         case_id_map[apk + "_" + _domain] = case_id_list
        #     case_domain_map[apk] = domain_list
        # return case_domain_map, case_id_map

    def get_task_devices(self, task_id, task_date) -> list:
        '''
        获取任务执行的设备列表
        :param task_id: 任务id
        :param task_date: 任务日期
        :return:
        '''
        res = self.mongo_client.distinct("task_result", "device_id", {"task_id": task_id, "task_date": task_date})
        device_set = set()
        for item in res:
            if item.get("device_id"):
                device_set.add(item.get("device_id"))
        return list(device_set)

    def get_result_cases_id(self, task_id, task_date, test_result) -> list:
        '''
        获取任务执行的用例id列表
        :param task_id: 任务id
        :param task_date: 任务日期
        :return:
        '''
        if test_result:
            res = self.mongo_client.find("task_result", {"task_id": task_id, "task_date": task_date, "test_result": test_result})
        else:
            res = self.mongo_client.find("task_result", {"task_id": task_id, "task_date": task_date})

        try:
            cases_id_lst = [_id.get("case_id") for _id in res]
            cases_id_lst.sort()
        except Exception as e:
            self.logger.error(traceback.format_exc())
            cases_id_lst = []
        return cases_id_lst

    def get_task_result(self, task_id, task_date, task_date_prev, device_list):
        '''
        根据任务执行的设备列表输入任务执行结果
        :param task_id: 任务id
        :param task_date: 任务日期
        :param device_list: 执行的设备列表
        :return: 任务执行结果列表
        '''
        result_data_dict = {}  # 测试结果数据
        result_info_dict = {}  # 测试结果信息（apk版本，设备名等）
        case_mark_dic = {}  # 用例以往标注信息
        for i, device_id in enumerate(device_list):
            if i == 0 and task_date_prev:  # 准备好上一轮的测试数据样本，用于对新结果进行对比分析
                # for rp in res_prev:
                #     if rp[7]:
                #         case_mark_dic[rp[0]] = rp[7]
                res_prev = self.mongo_client.find("task_result", {"task_id": task_id, "task_date": task_date_prev, "device_id": device_id})
                case_mark_dic = {rp.get("case_id"): rp.get("result_mark") for rp in res_prev if rp.get("result_mark")}
            _case_result = {}
            res = self.mongo_client.find("task_result", {"task_id": task_id, "task_date": task_date, "device_id": device_id})
            case_sum = 0
            pass_num = 0

            for item in res:
                case_result_dict = {}
                case_id = item.get("case_id")
                result = item.get("test_result")
                case_result_dict["id"] = item.get("id")
                result_mark = item.get("result_mark")
                # case_result_dict["device_name"] = item[1]
                # case_result_dict["test_log"] = item[2]
                # 查询上一轮的标注结果
                if result == "pass":
                    pass_num += 1
                if not result_mark:
                    result_mark = case_mark_dic.get(case_id, "")
                case_result_dict["test_result"] = result + ":" + result_mark if result_mark else result
                # case_result_dict["apk_version"] = item[4]
                # case_result_dict["img"] = item[5]
                _case_result[case_id] = case_result_dict
                case_sum += 1
            try:

                pass_rate = '{:.2%}'.format(pass_num/case_sum) if case_sum else 0
                result_info_dict[device_id] = {"应用版本": item.get("apk_version"), "设备名": item.get("device_name"),
                                               "通过用例": pass_num, "用例总数": case_sum, "通过率": pass_rate}
            except:
                pass
            result_data_dict[device_id] = _case_result
        return result_data_dict, result_info_dict

    def get_test_case_log(self, task_id, task_date, task_date_prev, device_id, case_id):
        '''
        根据条件获取测试case的log，图像信息，标注结果
        :param task_id:
        :param task_date:
        :param device_id:
        :param case_id:
        :return:
        '''

        find_dict = {"task_id": task_id, "task_date": task_date, "device_id": device_id, "case_id": case_id}
        res = self.mongo_client.find("task_result", find_dict, )
        data = ()
        if res:
            data =res[-1]
            resutl_mark, result_note = data[2], data[3]
            #  从上一次测试任务中获取标注内容
            if not resutl_mark:
                res_prev = self.mongo_client.find("task_result", {"task_id": task_id, "case_id": case_id, "task_date": task_date_prev}, limit_num=1)
                for rp in res_prev:
                    if rp[2]:
                        resutl_mark, result_note = rp[2], rp[3]
                        data = (data[0], data[1], resutl_mark, result_note)
                        break
        return data if data else ("", "", "", "")

    def add_scheduler_job(self, condition: dict, task_id: int, case_list):
        self.scheduler.add_job(self.job_runner, args=(condition, task_id, case_list), id=str(task_id), trigger=IntervalTrigger(hours=condition.get("hours", 0), minutes=condition.get("minutes", 1), seconds=condition.get("seconds", 0)), next_run_time=datetime.now(), max_instances=100)

    def job_runner(self, condition: dict, task_id: int, case_list):
        apk_url = condition.get("apk_url", "")
        self.logger.info(apk_url)
        apk_file_name = apk_url.split("/")[-1]
        if apk_url and self.is_apk_update(apk_file_name):  # 根据应用更新情况触发测试执行
            self.insert_task_case_table(task_id, case_list)  # 插入执行用例
            condition["task_id"] = task_id  # 在Condition中增加 task_id
            self.logger.info(condition)
            _device_list = []
            _device_list = self.run_connected_devices(condition)
            device_count_max = condition.get("device_count_max", 3)  # 最大调用设备数
            while len(_device_list) < device_count_max:  # 动态进行设备获取，直到达到最大设备调度数
                _device_list = self.run_connected_devices(condition)
                time.sleep(60)
            self.finish_apk_update(apk_file_name)

    def run_connected_devices(self, condition: dict) -> list:
        device_lst = []
        res_data = self.mongo_client.find("devices_state", {"remote": 1})
        device_count_max = condition.get("device_count_max", 5)  # 最大调用设备数
        target_device_list = condition.get("device_list", [])  # 特别指定的测试设备列表
        for item in res_data:
            device_id = item[0]
            idle = item[3]
            update_date = item[6]
            owner = item[8]
            update_time = time.mktime(time.strptime(update_date, "%Y-%m-%d %H:%M:%S"))
            if time.time() - update_time > 20 and idle != 1:
                self.logger.info(device_id +"设备离线或忙碌")
                continue

            if target_device_list:  # 任务指定执行设备
                if device_id not in target_device_list:  # 指定执行设备在此判断
                    continue
                else:
                    owner = ""  # 指定的设备不进行owner条件过滤
            if owner:  # 独占设备不进行分配
                continue
            task_id_str = item[7]
            self.logger.info(device_id +"的任务task_id:" + task_id_str)
            ip = str(item[4])
            if len(ip) > 7:  # 判断device_ip 是否存在
                device_dic = {}
                if item[5]:
                    device_dic = eval(item[5])
                device_dic["device_type"] = item[2]
                device_dic["device_id"] = device_id
                # device_dic["update_date"] = item[6]
                try:
                    task_id = eval(task_id_str)  # 转化一下任务id
                except:
                    task_id = 0
                flag = False  # 设备可分配任务标志
                if not task_id:# 设备当前无任务
                    flag = True
                elif task_id == condition.get("task_id"):  # 当前设备已分配该任务
                    flag = False
                    device_lst.append(device_dic)  # 将设备加入到列表中
                else:  # 当前设备已有其他任务
                    flag = False
                if flag:
                    if is_device_match_condition(device_dic, condition):
                        self.update_task(device_dic, condition)
                        device_lst.append(device_dic)
                self.logger.info(item)
                if len(device_lst) >= int(device_count_max):  # 达到最大调用设备数后跳出循环
                    break
        return device_lst

    def is_apk_update(self, apk_file_name):
        """
        判断被测apk是否更新
        :param apk_file_name:
        :return:
        """
        self.path = os.path.join(CONST.ROOT_PATH, "statics", "apks")
        info_file = os.path.join(self.path, "info.json")
        with open(info_file, "r") as jr:  # 读取状态
            info = json.load(jr)
            # self.logger.info(info)
            if info.get(apk_file_name, 1) != 1:  # 1 表示更新， 0 表示更新已消费
                # self.logger.info("%s 应用无更新" % apk_file_name)
                return False
        self.logger.info("%s 应用更新" % apk_file_name)
        return True

    def finish_apk_update(self, apk_file_name):
        """
        判断被测apk是否更新
        :param apk_file_name:
        :return:
        """
        self.path = os.path.join(CONST.ROOT_PATH, "statics", "apks")
        info_file = os.path.join(self.path, "info.json")
        with open(info_file, "r") as jr:  # 读取状态
            info = json.load(jr)
        with open(info_file, "w") as jw:  # 更新状态写入
            info[apk_file_name] = 0  # 状态更新为已消费
            jw.write(json.dumps(info))
            self.logger.info("%s 应用更新已消费" % apk_file_name)

    def update_task(self, device_info, condition):
        """
        更新设备的task_id参数
        :param device_info:
        :param condition:
        :return:
        """
        self.logger.info("更新设备任务："+str(device_info))
        self.logger.info("更新设备任务："+str(condition))
        self.mongo_client.update("devices_state", {"device_id": device_info.get("device_id")}, {"task_id":condition.get("task_id")})

    def add_jobs(self):
        task_lst = self.get_task_list()
        for _task in task_lst:
            task_status = _task.get("task_status")
            task_condition = _task.get("task_condition", "")
            if task_status == 1 and task_condition:
                self.add_scheduler_job(eval(task_condition), _task.get("id"), _task.get("case_list"))


threadLock = threading.Lock()
def device_connection(ip):
    try:
        ws = create_connection("ws://%s:9999" % ip, timeout=15)
        # ws.close()
        # ws.recv()
        return ws
    except Exception as e:
        traceback.print_exc()
        print("设备未连接")
        return None
    # ws.send(json.dumps({"msg": "connect"}))
    # result = ws.recv()

def device_run(ip, device_info, condition):
    """
    设备执行测试
    :param ip:
    :param device_info:
    :param condition:
    :return:
    """
    # ws = device_connection(ip)  # 设备websocket连通
    # if ws:
    #     ws.send(json.dumps({"mode": "task", "param": {"status":""}}))  # 询问设备状态
    #     is_idle = ws.recv() == "true"
    #     if is_idle and is_device_match_condition(device_info, condition):
    #         print("测试任务ID:%s 执行设备:%s" % (condition.get("task_id", "None"), str(device_info)))
    #         msg = {"mode": "task", "param": condition}
    #         ws.send(json.dumps(msg))  # 通知手机执行任务
    #         print("信息已发送 %s" % json.dumps(msg))
    #         ws.close()
        # threadLock.acquire()  # 获取线程锁
        # dev_list.append(device_infos)
        # print(dev_list)
        # threadLock.release()  # 释放线程锁

def is_device_match_condition(device_info, condition):
    """
    根据设备信息与测试条件匹配度选择测试设备
    :param device_info:
    :param condition: {"apk_url":"http://","device_count_max":"10","device_type":"PHONE", "厂商":"", "ROOT":"true", "Android版本":"9", "剩余电量":"20", "ROM":"1.0"}
    :return:
    """
    res = [0]
    match_item_txt = ["device_type", "厂商", "ROOT"]
    match_item_num = ["Android版本", "ROM", "剩余电量"]
    for mit in match_item_txt:
        pattern = re.compile(r""+condition.get(mit, ""), flags=0)
        m1 = pattern.match(device_info.get(mit, ""))
        if m1:
            res.append(0)
        else:
            res.append(1)
    for min in match_item_num:
        pattern = re.compile(r"\d+", flags=0)
        d = int("".join(pattern.findall(str(device_info.get(min, "0")))))
        c = int("".join(pattern.findall(str(condition.get(min, "0")))))
        if not c:
            # 默认设备信息中的数字不小于条件中约定的数字，相反可通过 "<" 在条件开头标识
            if condition.get(min, "0").startswith("<"):
                res.append(1) if d >= c else res.append(0)
            elif condition.get(min, "0").startswith("="):
                res.append(0) if d == c else res.append(1)
            elif condition.get(min, "0").startswith(">"):
                res.append(0) if d > c else res.append(1)
            else:
                res.append(0) if d >= c else res.append(1)

    return sum(res) == 0


if __name__ == "__main__":
    print(time.strftime("%Y-%m-%d %H:%M:%S"))