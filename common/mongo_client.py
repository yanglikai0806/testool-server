from datetime import datetime

import pymongo
# from bson import ObjectId

from common import CONST


class MongoClient:
    def __init__(self, url=CONST.MONGO_URL, db="testool"):
        self.my_client = pymongo.MongoClient(url)
        self.my_db = self.my_client[db]
        self.coll_counters = self.my_db["counters"]

    # 主键_id自己生成
    def _get_id(self, coll=None):
        if not self.coll_counters.find_one({"coll": coll}):
            self.coll_counters.insert_one({
                "coll": coll,
                "sequence_value": 1
            })
        ret = self.coll_counters.find_one_and_update({"coll": coll}, {"$inc": {"sequence_value": 1}},
                                                     upsert=True)
        nextid = ret["sequence_value"]
        return nextid

    def insert(self, collection, insert_dict):
        """
        插入一条或多条数据
        :param collection: 使用的collection
        :param insert_dict: 插入的数据
        :return: 插入后返回id
        """
        my_col = self.my_db[collection]
        if isinstance(insert_dict, dict):
            insert_dict = [insert_dict]
        insert_data = []
        for item in insert_dict:
            item["id"] = self._get_id(collection)
            item["create_time"] = str(datetime.now())
            insert_data.append(item)
        info = my_col.insert_many(insert_data)
        return info.inserted_ids

    def update(self, collection, filter_dict, update_dict, **keyargs):
        """
        更新一条或多条数据
        :param collection: 使用的collection
        :param filter_dict: 筛选条件
        :param update_dict: 更新数据
        :return: 返回影响了几条数据
        """
        my_col = self.my_db[collection]
        if isinstance(update_dict, list):
            update_dict = [item.update(update_time=str(datetime.now())) for item in update_dict]
        else:
            update_dict.update(update_time=str(datetime.now()))
        info = my_col.update_many(filter_dict, {"$set": update_dict}, **keyargs)
        return info.modified_count

    def update_by_id(self, collection, _id, update_dict):
        if 'create_time' in update_dict:
            update_dict.pop('create_time')
        res = self.update(collection, {'id': _id}, update_dict)
        return "success" if res == 1 else "failed"

    def delete(self, collection, filter_dict, just_one=True, **keyargs):
        """
        删除一条或多条数据
        :param collection: 使用的collection
        :param filter_dict: 筛选条件
        :param just_one: 删除一条或多条
        :return: 返回影响了几条数据
        """
        my_col = self.my_db[collection]
        if just_one:
            info = my_col.delete_one(filter_dict, **keyargs)
        else:
            info = my_col.delete_many(filter_dict, **keyargs)
        return info.deleted_count

    def find(self, collection, filter_dict, field_dict=None, limit_num=0, skip_num=0):
        """
        搜索数据
        :param collection: 使用的collection
        :param filter_dict: 筛选条件
        :param field_dict: 需要显示数据字段
        :param limit_num: 分页中的查询数数目
        :param skip_num: 分页中的从多少条开始查询
        :return: 返回数据
        """
        my_col = self.my_db[collection]
        if field_dict:
            result = my_col.find(filter_dict, field_dict).limit(limit_num).skip(skip_num)
        else:
            result = my_col.find(filter_dict).limit(limit_num).skip(skip_num)
        return [item for item in result]

    def distinct(self, collection, field, filter_dict=None):
        """
        单列数据去重搜索
        :param db: 使用的db
        :param collection: 使用的collection
        :param filter_dict: 筛选条件
        :param field: 需要显示数据字段(只能有一个)
        :return: 返回数据
        """
        my_col = self.my_db[collection]
        if filter_dict:
            result = my_col.distinct(field, filter_dict)
        else:
            result = my_col.distinct(field)
        return [item for item in result]


if __name__ == "__main__":
    a = MongoClient().find("biu", "services", {})
    print(a)
