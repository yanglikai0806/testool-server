# testool-server
* 与testool配合使用的测试平台服务端  
* 基于tornado实现   
* 数据库使用 Mongo, 需要在Mongo中建立名称为“testool”的database（或者在源码common/mongo_client.py 的__init__ 方法中修改默认db参数）  
* 执行 ts-start.py 启动服务

* 在Testool工具端的配置文件config.json中设置 "SERVER_BASE_URL":"http:\\/\\/xxx.xx.xx.xx:8566\\/test\\/".  (根据自身服务的情况修改ip) 

