import subprocess

def adb(sn="", cmd="", timeout=None):
    if sn:
        print("adb -s %s " % sn + cmd)
        res = subprocess.Popen("adb -s %s " % sn + cmd, shell=True, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE).communicate(timeout=timeout)
    else:
        print("adb " + cmd)
        res = subprocess.Popen("adb " + cmd, shell=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE).communicate(timeout=timeout)
    print(res)
    return res[0].decode()


def shell(sn="", cmd="", timeout=None):
    return adb(sn, "shell " + cmd, timeout=timeout)