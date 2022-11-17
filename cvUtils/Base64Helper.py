import base64
import numpy as np
import cv2


def base64ToFile(base64Code, filePath):
    with open(filePath, 'wb') as f:
        f.write(base64.b64decode(base64Code))


def fileToBase64(filePath):
    with open(filePath, 'rb') as f:  # 以二进制读取图片
        data = f.read()
        image_bs64 = str(base64.b64encode(data), 'utf-8')  # 重新编码数据
    return image_bs64

def cv2_base64(image):
    """
    将cv2格式图片转为base64编码
    :param image: cv2 图片数据
    :return: base64编码
    """
    base64_str = cv2.imencode('.jpg', image)[1].tostring()
    base64_str = base64.b64encode(base64_str)
    return base64_str.decode("utf8")


def base64_cv2(base64_str):
    """
    将base64编码转为cv2
    :param base64_str:
    :return:
    """
    if base64_str:
        imgString = base64.b64decode(base64_str)
        nparr = np.fromstring(imgString, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return image
    else:
        raise Exception("base64_str is empty")