# @Date : 2021/2/19
# @Author : 杨立凯
# @description : activity 展示列表
import json
import os
import traceback

from handlers import BaseHandler
import tornado

class LogHandler(BaseHandler):

    def get(self):
        '''
            查看服务日志
            '''
        what = self.get_query_argument("what")
        clear = self.get_query_argument("clear", "")
        res = {}
        log_list = [log for log in os.listdir(
            os.path.join(os.path.dirname(__file__), os.pardir, "log")) if
                    log.endswith(".log")]

        if str(what).endswith(".log"):
            file_path = os.path.join(os.path.dirname(__file__), os.pardir, "log", what)
            # 清除已有log
            if clear:
                with open(file_path, "w") as f:
                    f.write("")
            # 生成log目录链接
            _html = ''
            for _log in log_list:
                _html += '''<a href='{url_prefix}log?what={log_file}'>{log_file}</a>'''.format(url_prefix="/test/",
                                                                                          log_file=_log)
            # 获取log内容
            file_size = os.path.getsize(file_path)
            block_size = 10240 * 10
            with open(file_path, "rb", ) as f:
                if file_size > block_size:
                    f.seek(-block_size, 2)
                elif file_size:  # 文件大小不为空
                    f.seek(0, 0)
                last_lines = []
                for line in f.readlines():
                    try:
                        last_lines.append(line.decode())
                    except:
                        pass
            res = '''
                <div style='width:100%; height:100%;overflow:auto'>
                    <div style='margin:2px 0;display:flex;justify-content:space-around;height:15px'>
                        {html}
                    </div>
                    <div style='background:black;margin:5px;'>
                        <code style='color: #fff'>{log}</code>
                    </div>
                </div>

                '''.format(log="<br>".join(last_lines), html=_html)

            # return "".join(last_lines).strip(), 200
        # 获取log列表
        elif str(what) == "list":
            res["result"] = log_list
        self.write(res)

