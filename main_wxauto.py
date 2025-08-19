
from wxauto import WeChat
from wxauto.msgs import FriendMessage

from base.func_myself import Myself
from configuration import Config
from base.fun_ai_zhipu import ZhiPu
import time
import datetime
import requests
# 初始化机器人，扫码登陆
bot = WeChat()
# bot.enable_puid()

class Msg(object):
    def __init__(self, msg):
        self.msg = msg
        self.type = self.get_type()
        self.content = self.msg.text
        self.xml = self.msg.text
        self.sender = self.get_sender()
        self.roomid = self.get_room()

    def get_type(self):
        if self.msg.type=="TEXT" or self.msg.type=="text":
            return 1
        else:
            return 2

    def get_room(self):
        # 群聊
        if self.msg.member:
            return self.msg.sender.puid
        # 私聊
        else:
            return False

    def get_sender(self):
        # 群聊
        if self.msg.member:
            return self.msg.member.puid
        # 私聊
        else:
            return self.msg.sender.puid

    def from_group(self):
        if self.msg.member:
            return True
        else:
            return False


class Mychat(object):
    def __init__(self, bot):
        self.bot = bot
        self.friends = self.bot.friends()
        self.chats = self.bot.chats()
        self.config = Config()
        self.filepath = self.config.Myself["image_path"]
        self.chat = Myself(self.config.Myself, self)
        self.zhipu_ai = ZhiPu(self.config.Myself, self)

        self.names = {}

    # 每次有人发消息，把发送者id和昵称对应起来
    def add_name(self, msg):
        if msg.member:
            self.names[msg.member.puid] = msg.member.name
        else:
            self.names[msg.sender.puid] = msg.sender.name

    def send_text(self, text, wxid):
        achat = self.get_chat(wxid)
        achat.send(text)

    def send_file(self, file, wxid):
        achat = self.get_chat(wxid)
        achat.send_file(file)

    def send_image(self, file, wxid):
        achat = self.get_chat(wxid)
        if "http" in file:
            filename = self.filepath + str(int(time.time()))+wxid+".png"
            res = requests.get(file)
            with open(filename, 'wb') as f:
                f.write(res.content)
        else:
            filename = file
        achat.send_image(filename)

    def get_info_by_wxid(self, wxid):
        return self.names[wxid]


    def get_chat(self, id):
        for achat in self.chats:
            if achat.puid == id:
                return achat
        return False
    def get_rsp(self, msg):
        self.add_name(msg)
        text = msg.text

        if len(text)>0:
            if text[:2] == "zp":
                result = self.zhipu_ai.get_answer(text, Msg(msg))
                msg.reply(result)
            else:
                result = self.chat.get_answer(text, Msg(msg))
                msg.reply(result)



ituos = ItUos(bot)

# 回复私聊的消息 (优先匹配后注册的函数!)
@bot.register(User, TEXT)
def reply_anything(msg):
    # print(msg.sender.remark_name+":"+msg.text)
    if time.time() - time.mktime(msg.create_time.timetuple())<10:
        ituos.get_rsp(msg)



# 回复群里的消息 (优先匹配后注册的函数!)
@bot.register(Group, TEXT)
def reply_group(msg):
    # print("[group]"+msg.member.nick_name+":"+msg.text)
    if time.time() - time.mktime(msg.create_time.timetuple()) < 10:
        ituos.get_rsp(msg)

# 消息处理函数
def on_message(msg, chat):
    # 示例3：自动回复收到
    if isinstance(msg, FriendMessage):
        msg.quote('收到')
bot.AddListenChat(nickname="张三", callback=on_message)
bot.KeepRunning()