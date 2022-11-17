# @Author : yanglikai
# @description : monkey测试LOG分析
import os
import zipfile
from common import CONST


def generate_monkey_result(target_app, target_version):
    monkey_log_path = CONST.MONKEY_LOG_PATH
    target_path = os.path.join(monkey_log_path, target_app, target_version)
    if os.path.exists(target_path):
        # 解压所有zip文件
        for root, dirs, files in os.walk(target_path):
            for file in files:
                if file.endswith(".zip") and not file.startswith("bugreport"):
                    unzip_folder = file[:-4]
                    unzip_path = os.path.join(root, unzip_folder)
                    if not os.path.exists(unzip_path):  # 判断一下是不是解压过了
                        fz = zipfile.ZipFile(os.path.join(root, file), 'r')
                        for _file in fz.namelist():
                            fz.extract(_file, unzip_path)
        error_list = []
        error_info_list = []
        for root, dirs, files in os.walk(target_path):
            for file in files:
                if file.endswith("monkey_error.txt"):
                    error_info_list = error_info_list + analyses_log(os.path.join(root, file), error_list, target_app=target_app)
        return error_info_list


def analyses_log(error_file_local, error_list: list, target_app=""):
    """
    解析log文件
    :param error_file_local: error log 文件本地路径
    :return: error信息
    """
    error_info_lst = []
    # print(error_file_local)
    with open(error_file_local, "r") as l:
        lines = list(l.readlines())
        for i, line in enumerate(lines):
            # print(line)
            if "NOT RESPONDING" in line:
                # print("find anr")
                pkg_name = line.split(": ")[-1].split(" ")[0]
                # 过滤非目标应用的报错
                if (target_app != "") and (target_app.strip() != pkg_name.strip()):
                    continue
                # print("find anr")
                error_info = [os.path.relpath(error_file_local)]
                error_info.append("anr")
                error_info.append(pkg_name)

                if "Reason:" in lines[i + 3]:
                    anr_msg = lines[i + 3].split("Reason:")[1].split("{")[0]
                    error_info.append(anr_msg)
                    error_info_lst.append(error_info)
                    # if anr_msg not in error_list:  # 去重
                    #     error_list.append(anr_msg)
                        # error_info_lst.append(error_info)
                    # else:
                    #     continue

            elif "CRASH" in line:
                pkg_name = line.split(": ")[-1].split(" ")[0]
                # print(target_app)
                # print(pkg_name)
                if (target_app != "") and (target_app.strip() != pkg_name.strip()):
                    continue
                # print("find crash")
                error_info = [os.path.realpath(error_file_local)]
                error_info.append("crash")
                error_info.append(pkg_name)
                # print(lines[i + 1])

                # if "Short Msg:" in lines[i + 1]:
                #     error_info.append(lines[i + 1].split(":")[1].strip())
                if "Long Msg:" in lines[i + 2]:
                    crash_msg = lines[i + 2].split("Long Msg:")[1].strip()
                    error_info.append(crash_msg)
                    error_info_lst.append(error_info)
                    # if crash_msg not in error_list:  # 去重
                    #     error_list.append(crash_msg)
                        # error_info_lst.append(error_info)
                    # else:
                    #     continue
    return error_info_lst


def get_log_info():
    """获取服务器上存储的monkey日志文件信息"""
    app_list = os.listdir(CONST.MONKEY_LOG_PATH)
    app_info_dict = {}
    for _app in app_list:
        app_version_lst = [i for i in os.listdir(os.path.join(CONST.MONKEY_LOG_PATH, _app)) if "." in i]
        try:
            app_version_lst.sort(reverse=True, key=lambda x: x.split("-")[1])
        except Exception as e:
            app_version_lst.sort(reverse=True)
        app_info_dict[_app] = app_version_lst
    return app_list, app_info_dict


if __name__ == "__main__":
    pass