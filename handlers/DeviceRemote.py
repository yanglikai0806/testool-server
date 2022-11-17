from handlers import BaseHandler


class DeviceRemote(BaseHandler):
    def get(self):
        self.render("device_remote.html")