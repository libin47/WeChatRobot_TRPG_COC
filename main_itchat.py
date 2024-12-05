from wxpy import *
from base.func_myself import Myself
from configuration import Config


# 初始化机器人，扫码登陆
bot = Bot(cache_path=True)
bot.enable_puid()

class Msg(object):
    def __init__(self, msg:Message):
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
            return self.msg.sender

    def from_group(self):
        if self.msg.member:
            return True
        else:
            return False


class ItUos(object):
    def __init__(self, bot):
        self.bot = bot
        self.friends = self.bot.friends()
        self.chats = self.bot.chats()
        self.config = Config()
        self.chat = Myself(self.config.Myself, self)

    def send_text(self, text, wxid):
        achat = self.get_chat(wxid)
        achat.send(text)

    def send_file(self, file, wxid):
        achat = self.get_chat(wxid)
        achat.send_file(file)

    def send_image(self, file, wxid):
        achat = self.get_chat(wxid)
        achat.send_image(file)

    def get_info_by_wxid(self, wxid):
        achat = self.get_chat(wxid)
        return achat.nick_name


    def get_rsp(self, msg):
        text = msg.text
        if len(text)>0:
            result = self.chat.get_answer(text, Msg(msg))
            msg.reply(result)

    def get_chat(self, id):
        for achat in self.chats:
            if achat.puid == id:
                return achat
        return False

ituos = ItUos(bot)

# 回复私聊的消息 (优先匹配后注册的函数!)
@bot.register(User, TEXT)
def reply_anything(msg):
    print(msg.sender.remark_name+":"+msg.text)
    ituos.get_rsp(msg)



# 回复群里的消息 (优先匹配后注册的函数!)
@bot.register(Group, TEXT)
def reply_group(msg):
    print("[group]"+msg.member.nick_name+":"+msg.text)
    ituos.get_rsp(msg)


# 进入 Python 命令行、让程序保持运行
embed()