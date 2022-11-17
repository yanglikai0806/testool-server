!/usr/bin/bash
set +x
# 先kill掉防止好多进程将服务压垮
ps -ef | grep -E 'ts-start.py' | awk '{print $2}' | xargs kill -9
python=/home/work/anaconda3/envs/py38/bin/python
#python=/home/yanglikai/v9-git/biu-services/venv/bin/python
echo $python

# 启动后台服务
nohup ${python} ts-start.py &
exit