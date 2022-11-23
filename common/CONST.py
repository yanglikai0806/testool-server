import os

ROOT_PATH = os.path.join(os.path.dirname(__file__), os.pardir)
CACHE_PATH = os.path.join(os.path.dirname(__file__), "cache")
MONKEY_LOG_PATH = os.path.join(ROOT_PATH, "statics", "monkey_log")
MONGO_URL = "mongodb://127.0.0.1:27017"

APP_DICT = {
    "测试工具": "com.kevin.testool"
}
APP_DICT_X = {v: k for k, v in APP_DICT.items()}

TABLE_APK_DICT = {
    "test_cases": "com.kevin.testool"
}

APK_TABLE_DICT = {v: k for k, v in TABLE_APK_DICT.items()}