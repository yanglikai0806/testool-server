'''
# 图像识别基础方法
'''
import heapq
import os
import time
from PIL import Image, ImageDraw, ImageFont
from matplotlib import pyplot as plt

from cvUtils.Base64Helper import *
import cv2

RESIZE = 1


def getMatchImg(srcBase64: str, schBase64: str, targetBounds="", matchMethod=cv2.TM_CCOEFF_NORMED, mIndex=-1,
                threshold=0.98, similarity=0.0) -> dict:
    '''
    模板匹配
    :param inFile: 源文件
    :param tempFile: 模板文件
    :param targetBounds: 目标匹配区域
    :param matchMethod: 匹配方法，默认 cv2.TM_CCOEFF_NORMED
    :param mIndex: > 0 时表示匹配多个结果
    :param threshold: 匹配度限制
    :param similarity: 相似度判断
    :return: resBounds 匹配的图像区域
    '''
    result = {}
    resBounds = ""
    match_score = None
    isSame = True  # 轮廓相似度判断结果
    sch_img_color = cv2.cvtColor(base64_cv2(schBase64), cv2.COLOR_BGR2RGB)
    src_img_color = cv2.cvtColor(base64_cv2(srcBase64), cv2.COLOR_BGR2RGB)
    sch_img = cv2.cvtColor(sch_img_color, cv2.COLOR_RGB2GRAY)

    src_img = cv2.cvtColor(src_img_color, cv2.COLOR_RGB2GRAY)
    w, h = sch_img.shape[::-1]  # 得到模板的宽和高
    res = cv2.matchTemplate(src_img, sch_img, matchMethod)
    # 归一化处理
    cv2.normalize(res, res, 0, 1, cv2.NORM_MINMAX, -1)
    if mIndex >= 0:
        loc = np.where(res >= threshold)
        n = 0
        for i, pt in enumerate(zip(*loc[::-1])):
            if i > 0:
                if not (pt[0] - pt_copy[0] > w - 1 or pt[1] - pt_copy[1] > h - 1):  # 避免相邻区域重复匹配
                    continue
            pt_copy = pt
            cv2.putText(src_img_color, "#%s" % n, (pt[0] - 1, pt[1] - 1), cv2.FONT_HERSHEY_SCRIPT_COMPLEX, 1.0,
                        (0, 0, 255))
            cv2.rectangle(src_img_color, pt, (pt[0] + w, pt[1] + h), (0, 255, 0), 5)
            if n == mIndex:
                print(resBounds)
                resBounds = "[%s,%s]" % pt + "[%s,%s]" % (pt[0] + w, pt[1] + h)
                match_score = res[pt[1]][pt[0]]
                break
            n = n + 1
    else:
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if matchMethod < 2:
            match_score = min_val
            left_top = min_loc
        else:
            match_score = max_val
            left_top = max_loc
        right_bottom = (left_top[0] + w, left_top[1] + h)
        if len(targetBounds) > 9:
            print(parseBounds(targetBounds))
            left, top, right, bottom = parseBounds(targetBounds)
            cv2.rectangle(src_img_color, (left, top), (right, bottom), (0, 0, 255), 2)  # 绘制targetbound范围
        cv2.rectangle(src_img_color, left_top, right_bottom, (0, 255, 0), 2)  # 根据得到的top_left和bottom_tight来画矩形
        if left_top:
            resBounds = "[%s,%s]" % left_top + "[%s,%s]" % right_bottom
            if similarity > 0:
                sim = isSameContour(sch_img, src_img[left_top[1]:right_bottom[1], left_top[0]:right_bottom[0]])
                isSame = similarity < sim
                result["similarity"] = sim
    success = isInBounds(resBounds, targetBounds, 50) and isSame
    return generateResult(result, resBounds, cv2_base64(src_img_color), success, score=match_score, method="template")


def getMatchImgBySift(srcBase64: base64, schBase64: base64, targetBounds="", ratio=0.59, similarity=0.0):
    """
    sift 特征匹配
    :param srcBase64:
    :param schBase64:
    :param targetBounds:
    :param ratio:
    :return:
    """
    result = {}
    isSame = True
    # sch_img = cv2.imread(templateFile, 0)  # queryImage
    sch_img_color = cv2.cvtColor(base64_cv2(schBase64), cv2.COLOR_BGR2RGB)
    # src_img = cv2.imread(inFile, 0)  # trainImage
    src_img_color = cv2.cvtColor(base64_cv2(srcBase64), cv2.COLOR_BGR2RGB)
    sch_img = cv2.cvtColor(sch_img_color, cv2.COLOR_RGB2GRAY)
    src_img = cv2.cvtColor(src_img_color, cv2.COLOR_RGB2GRAY)
    w, h = sch_img.shape[::-1]  # 得到模板的宽和高
    # Initiate SIFT detector
    sift = cv2.SIFT_create(nfeatures=0, nOctaveLayers=5, contrastThreshold=0.04, edgeThreshold=20, sigma=1.6)
    # find the keypoints and descriptors with SIFT
    kp1, des1 = sift.detectAndCompute(sch_img, None)
    kp2, des2 = sift.detectAndCompute(src_img, None)
    # FLANN parameters
    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
    search_params = dict(checks=50)  # or pass empty dictionary
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    matches = flann.knnMatch(des1, des2, k=2)
    # Need to draw only good matches, so create a mask
    matchesMask = [[0, 0] for _ in range(len(matches))]
    # ratio test as per Lowe's paper
    matchPoints = []
    good = []
    for i, (m, n) in enumerate(matches):
        trainId = m.trainIdx
        queryId = m.queryIdx
        if i == 0:
            refrence_point = kp2[trainId].pt  # 初始化参考点

        if ratio > 0 and m.distance > ratio * n.distance:  # 通过比率过滤掉错误匹配，ratio越小越严格
            continue
        match_point = kp2[trainId].pt
        # 过滤掉偏离较大的点
        if abs(match_point[0] - refrence_point[0]) > 3 * w or abs(match_point[1] - refrence_point[1]) > 3 * h:
            continue
        matchesMask[i] = [1, 0]
        matchPoints.append(match_point)
        good.append(m)
    draw_params = dict(matchColor=None,  # (0,255,0)
                       singlePointColor=None,
                       matchesMask=matchesMask,  # matchesMask
                       flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)  # cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
    img3 = cv2.drawMatchesKnn(sch_img_color, kp1, src_img_color, kp2, matches, None, **draw_params)
    if len(good) > 3:
        bounds = _find_homography(kp1, kp2, good, sch_img, src_img)
        matchBounds = "%s%s" % (bounds[0], bounds[2])
    else:
        if len(matchPoints) > 0:
            matchBounds = matchBoundsFromPoints(matchPoints)
        else:
            matchBounds = ""
    if targetBounds:
        left, top, right, bottom = parseBounds(targetBounds)
        cv2.rectangle(img3, (left + w, top), (right + w, bottom), (255, 0, 0), 2)  # 绘制targetbound范围
    if matchBounds:
        mleft, mtop, mright, mbottom = parseBounds(matchBounds)
        cv2.rectangle(img3, (mleft + w, mtop), (mright + w, mbottom), (0, 255, 0), 2)
        if similarity > 0:
            sim = isSameContour(sch_img, src_img[mtop:mbottom, mleft:mright])
            isSame = similarity <= sim
            result["similarity"] = sim

    success = isInBounds(matchBounds, targetBounds, 50) and isSame
    return generateResult(result, matchBounds, cv2_base64(img3), success, method="sift")

def getMatchImgByContours(srcBase64: base64, schBase64: base64, targetBounds="",similarity=None, min_pix=2300, max_pix=None, wh_ratio=1, mIndex=0):
    '''
    轮廓匹配
    :param srcBase64:
    :param schBase64:
    :param targetBounds:
    :param similarity:
    :param min_pix:
    :param max_pix:
    :param wh_ratio:
    :param mIndex:
    :return:
    '''
    result = {}
    isSame = False
    matchBounds = ""
    srcImg = base64_cv2(srcBase64)
    schImg = base64_cv2(schBase64)
    contours = find_contours(srcImg, min_pix=min_pix, max_pix=max_pix, wh_ratio=wh_ratio)
    sim_list = []
    for rect in contours:
        x = rect[0]
        y = rect[1]
        w = rect[2]
        h = rect[3]
        sim = isSameContour(srcImg[y: y+h, x:x+w], schImg)
        sim_list.append(sim)
    good_sims = heapq.nlargest(mIndex + 1, sim_list)
    for i, sim in enumerate(good_sims):
        if similarity:
            isSame = (similarity <= sim)
            index = sim_list.index(sim)
            x, y, w, h = contours[index]
            if i == mIndex:
                result["similarity"] = sim
                cv2.rectangle(srcImg, (x, y), (x + w, y + h), (0, 255, 0), 2)
                matchBounds = "[%s,%s][%s,%s]" % (x, y, x + w, y + h)
                break
        else:
            index = sim_list.index(sim)
            x, y, w, h = contours[index]
            if i == mIndex:
                result["similarity"] = sim
                cv2.rectangle(srcImg, (x, y), (x + w, y + h), (0, 255, 0), 2)
                matchBounds = "[%s,%s][%s,%s]" % (x, y, x + w, y + h)
                isSame = True
                break
    success = isInBounds(matchBounds, targetBounds, 50) and isSame
    return generateResult(result, matchBounds, cv2_base64(srcImg), success, method="contour")


def getMatchText(src_base64, text: str, index=0, targetBounds="", debug=False):
    if len(text):
        result = {"text": text}
        res_bounds = ""
        text_dict = getTextsHierarchyByOcr(src_base64)
        img = base64_cv2(src_base64)
        if debug:  # debug 时返回所有文本识别结果图
            for txt in text_dict.keys():
                txt_locs = text_dict.get(txt, [])
                for loc in txt_locs:
                    img = putText(txt, cv2_bgr=img, location=(loc.get("left"), loc.get("top")), font_size=20)

        if text.startswith("re:"):
            res = ["暂不支持"]  # todo 正则匹配
        else:
            res = text_dict.get(text, [])
        if len(res) > index:
            res_index = res[index]
            left = res_index.get("left")
            top = res_index.get("top")
            right = left + res_index.get("width")
            bottom = top + res_index.get("height")
            res_bounds = "[%s,%s][%s,%s]" % (left, top, right, bottom)
            cv2.rectangle(img, (left, top), (right, bottom), (0, 255, 0), 2)
        success = isInBounds(res_bounds, targetBounds, 50)
        return generateResult(result, res_bounds, cv2_base64(img), success, method="ocr")
    else:
        return generateResult({"text": getTextsByOcr(src_base64)}, "", "", True, method="ocr")


def getTextsHierarchyByOcr(src_base64) -> dict:
    """
    通过ocr获得图片文本及位置
    :param src_base64: 图片的base64编码数据
    :return:
    """
    pass

def getTextsByOcr(src_base64) -> list:
    pass

def parseBounds(bounds: str):
    """
    解析bounds的字符串
    :param bounds: like "[100,100][500,500]"
    :return:
    """
    if bounds:
        left, top, right, bottom = [int(a) for a in
                                    bounds.replace(" ", "").replace("[", "").replace("]", ",").strip(",").split(",")]
        return left, top, right, bottom
    else:
        return None


def isInBounds(abounds, bbounds, extend=0) -> bool:
    """
    判断abounds是否包含在bbounds内
    :param abounds:
    :param bbounds:
    :param extend: bbounds的扩展量
    :return:
    """
    if len(abounds.strip()) == 0:
        return False

    if len(bbounds.strip()) == 0:
        return True
    aleft, atop, aright, abottom = parseBounds(abounds)
    bleft, btop, bright, bbottom = parseBounds(bbounds)
    if bleft - extend <= aleft:
        if btop - extend <= atop:
            if bright + extend >= aright:
                return bbottom + extend >= abottom
    return False


def matchBoundsFromPoints(points: list):
    """
    根据point集合计算bound区域
    :param points:
    :return:
    """
    print("根据点集合计算bounds")
    xVal = []
    yVal = []
    if len(points) == 1:
        _point = points[0]
        points.append((_point[0] + 40, _point[1] + 40))
    for pt in points:
        xVal.append(pt[0])
        yVal.append(pt[1])
    try:
        xMax = max(xVal)
        xMin = min(xVal)
        yMax = max(yVal)
        yMin = min(yVal)
    except Exception as e:
        print(str(e))
        return ""
    return "[%s,%s][%s,%s]" % (int(xMin), int(yMin), int(xMax), int(yMax))


def generateResult(result: dict, res_bounds: str, image: base64, success: bool, **keyargs) -> dict:
    """
    生成结果数据结构
    :param result:
    :param resize: 图片缩小比例
    :param res_bounds: bounds结果
    :param image: 结果图片的base64编码
    :param success: 是否匹配成功
    :param keyargs: 其他
    :return: dict
    """
    if res_bounds:
        left, top, right, bottom = [n / RESIZE for n in parseBounds(res_bounds)]
        center_point = [(left + right) / 2, (top + bottom) / 2]
        res_bounds = "[%s,%s][%s,%s]" % (left, top, right, bottom)
    else:
        center_point = ""
    return {**result, **dict(res_bounds=res_bounds, center_point=center_point, success=success, image=image, **keyargs)}


def _find_homography(kp1, kp2, good, template, target):
    """
    变换矩阵计算bounds
    :param kp1:
    :param kp2:
    :param good:
    :param template:
    :param target:
    :return:
    """
    print("变换矩阵计算bounds")
    # 获取关键点的坐标
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    # 计算变换矩阵和MASK
    M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    matchesMask = mask.ravel().tolist()
    h, w = template.shape
    # 使用得到的变换矩阵对原图像的四个角进行变换，获得在目标图像上对应的坐标
    pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
    dst = cv2.perspectiveTransform(pts, M)
    res = [npt[0] for npt in dst.astype(int).tolist()]
    # cv2.polylines(target, [np.int32(dst)], True, 0, 2, cv2.LINE_AA)
    return res


def _find_contours(img: cv2):
    """
    获得图片边缘
    :param img: cv 格式图片
    :return: 轮廓灰度图
    """
    # 灰度化+高斯滤波
    if len(img.shape) > 2:
        gray_dst = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray_dst = img
    blur_dst = cv2.GaussianBlur(gray_dst, (3, 3), 0)
    # OTSU阈值分割
    ret, otsu_dst = cv2.threshold(blur_dst, 0, 200, cv2.THRESH_OTSU)  # cv2.THRESH_OTSU
    # Canny算子提取边缘轮廓
    edge1 = cv2.Canny(otsu_dst, 100, 200)
    # edge1 = cv2.Canny(otsu_dst, 250, 200)
    edge2 = cv2.Canny(img, 200, 250)
    edge3 = cv2.Canny(img, 100, 150)
    # plt.subplot(131)
    # plt.imshow(edge1, cmap="gray")
    # plt.title("edge1"), plt.xticks([]), plt.yticks([])
    # plt.subplot(132)
    # plt.imshow(edge2,cmap="gray")
    # plt.title("edge2"), plt.xticks([]), plt.yticks([])
    # plt.subplot(133)
    # plt.imshow(edge3,cmap="gray")
    # plt.title("edge3"), plt.xticks([]), plt.yticks([])
    # plt.show()
    return [edge1, edge2, edge3]

def find_contours(img: cv2, min_pix=2400, max_pix=None, wh_ratio=None, extend=5):
    """
    获取图片中轮廓
    :param img:
    :param min_pix: 限定最小像素数 w * h
    :return:
    """
    edges = _find_contours(img)
    contours_rect = []
    for edge in edges:
        contours, h = cv2.findContours(edge, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        for cont in contours:
            # 画出轮廓
            # cv2.drawContours(src, contours, i, (255,255,255), 1)
            x, y, w, h = cv2.boundingRect(cont)
            if w * h > min_pix and (True if max_pix is None else w * h < max_pix) and (True if wh_ratio is None else abs(w/h - wh_ratio) < 0.1):
                contours_rect.append((x - extend, y - extend, w + 2 * extend, h + 2 * extend))
        # 最小外包圆
        # circle = cv2.minEnclosingCircle(contours[i])
        # cv2.circle(img, (int(circle[0][0]), int(circle[0][1])), int(circle[1]), (0, 255, 0), 2)
        # 绘制多边形
        # approxCurve = cv2.approxPolyDP(contours[i], 0.3, True)
        # t = approxCurve.shape[0]
        # for i in range(t - 1):
        #     cv2.line(img, (approxCurve[i, 0, 0], approxCurve[i, 0, 1]),
        #             (approxCurve[i + 1, 0, 0], approxCurve[i + 1, 0, 1]), (255, 0, 0), 2)
        #     cv2.line(img, (approxCurve[t - 1, 0, 0], approxCurve[t - 1, 0, 1]),
        #             (approxCurve[0, 0, 0], approxCurve[0, 0, 1]), (255, 0, 0), 2)
    contours_rect = sorted(set(contours_rect), key=contours_rect.index)
    # 画出轮廓
    # for rect in contours_rect:
    # # 在img图像画出矩形，(x, y), (x + w, y + h)是矩形坐标，(0, 255, 0)设置通道颜色，2是设置线条粗度
    #     x = rect[0]
    #     y = rect[1]
    #     w = rect[2]
    #     h = rect[3]
    #     cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
    # showImg(img, "lunkuotu")
    # print(len(contours_rect))
    # print(contours_rect)
    return contours_rect

def isSameImage():
    pass

def isSameColor():
    pass

def isSameContour(img1, img2):
    """
    判断两图片轮廓是否相似程度
    :param img1:
    :param img2:
    :return:
    """
    ret = 0.1  # 结果默认值
    # img1_shape = img1.shape
    # img2_shape = img2.shape

    # if abs(img1_shape[0] - img2_shape[0]) > 10 or abs(img1_shape[1] != img2_shape[1]) > 10:
    #     img2 = cv2.resize(img2, (0, 0), fx=float(img1_shape[1]/img2_shape[1]), fy=float(img1_shape[0]/img2_shape[0]),
    #                              interpolation=cv2.INTER_NEAREST)
    try:
        contour1 = _find_contours(img1)[0]
        contour2 = _find_contours(img2)[0]
        if len(contour1) > 0 and len(contour2) > 0:
            ret = cv2.matchShapes(contour1, contour2, 1, 0.0)  # 值越小匹配度越高，下面做了转换
            # print("ret:" + str(ret))
            ret = ret * 10  # 将结果扩大10倍，便于计算
            if 0 <= ret < 1:
                ret = 1 - ret
            else:
                ret = 0.1
    except Exception as e:
        print("轮廓解析报错：" + str(e))
    # print("轮廓相似度:" + str(ret))
    return ret


def showImg(img, title="my picture", save=""):
    """
    :param img: 图像数据
    :param title: 图片显示标题
    :param save: 图片保存路径及名称
    :return:
    """
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    if save:
        cv2.imwrite(save, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    plt.subplot()
    plt.imshow(img)
    plt.title(title), plt.xticks([]), plt.yticks([])
    plt.show()

def putText(text, cv2_bgr=None, location=(10, 10), font_size=20, font_color=(0, 0, 255), font_type=os.path.join(os.path.dirname(__file__), "SimHei.ttf")):
    """
    图片上绘制文字
    :param text: 文字内容
    :param cv2_bgr: 图片cv2
    :param location: 文字开始位置
    :param font_size: 文字大小
    :param font_color: 文字颜色 BGR
    :return:
    """
    # img_rgb = cv2.cvtColor(cv2_bgr, cv2.COLOR_BGR2RGB)  # cv2和PIL中颜色的hex码的储存顺序不同
    # if cv2_bgr == None:
    #     height = font_size + 10 * 2
    #     width = len(text) * font_size + 10 * 2
    #     cv2_bgr = np.ones((height, width, 3), dtype=np.uint8)

    pil_img = Image.fromarray(cv2_bgr)
    # PIL图片上打印汉字
    draw = ImageDraw.Draw(pil_img)  # 图片上打印
    font = ImageFont.truetype(font_type, size=font_size, encoding="utf-8")  # 参数1：字体文件路径，参数2：字体大小
    draw.text(location, text, font_color, font=font)  # 参数1：打印坐标，参数2：文本，参数3：字体颜色，参数4：字体

    # PIL图片转cv2 图片
    cv2_img = np.array(pil_img)
    # cv2.imshow("my picture", cv2_img)  # 汉字窗口标题显示乱码
    return cv2_img


def setSize(resize):
    global RESIZE
    RESIZE = resize


def imageResize(imageFile, resize):
    """
    将图片按比例缩放
    :param imageFile:
    :param resize:
    :return:
    """
    img_resized = cv2.resize(cv2.imread(imageFile, cv2.IMREAD_COLOR), (0, 0), fx=resize, fy=resize,
                             interpolation=cv2.INTER_NEAREST)
    return img_resized


if __name__ == "__main__":
    src = fileToBase64("pic.jpg")
    sch = fileToBase64("te.png")
    # # find_contours(cv2.imread("img.jpeg"), min_pix=5000, wh_ratio=1)
    res = getMatchImg(src, sch, mIndex=1)

    # res = getMatchImgBySift(srcBase64=src, schBase64=sch, targetBounds="", ratio=1)
    # res = getMatchImg(src, aa, targetBounds="", similarity=0.8)
    res = getMatchText(src, "全部技能")
    # res = getTextsHierarchyByOcr(src)
    # cv_img = base64_cv2(src)
    # for key, vlu in res.items():
    #     print(vlu)
    #     cv_img = putText(key, cv_img, (vlu[0]["left"], vlu[0]["top"]),font_size=30, font_color=(0, 255, 255))
    #     cv2.rectangle(cv_img, (vlu[0]["left"], vlu[0]["top"]), (vlu[0]["left"]+vlu[0]["width"], vlu[0]["top"] + vlu[0]["height"]), (0, 255, 0), 2)
    # cv2.imwrite("out.png", cv_img)
    # print(res)
    # print(time.time() - startTime)

    showImg(cv2.cvtColor(base64_cv2(res.get("image")), cv2.COLOR_BGR2RGB), save="res.png")
    del res["image"]
    print(res)

