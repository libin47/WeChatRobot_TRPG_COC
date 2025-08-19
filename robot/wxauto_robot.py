from wxauto import WeChat
from wxauto.msgs import FriendMessage,TextMessage
from wxauto.msgs.friend import QuoteMessage
import time
from base.wedice import WeDice
from configuration import Config

class Robot(object):
    def __init__(self, config):
        self.config = config
        self.wx = WeChat()
        self.dice = WeDice()
        self.chat = WeDice(self.config.Myself, self.send_text, self.send_file, self.send_image)

        self.wx.AddListenChat(nickname="听，风的声音", callback=self.on_message)

        self.wx.KeepRunning()

    def on_message(self, msg, chat):
        if isinstance(msg, FriendMessage):
            if isinstance(msg, TextMessage):
                text = msg.content
                wxid = msg.sender
                chatinfo = msg.chat_info()
                group = chatinfo["chat_name"] if chatinfo["chat_type"]=="group" else None
                rsp = self.chat.get_answer(text, wxid, group)
                msg.quote(rsp)
            elif isinstance(msg, QuoteMessage):
                text = msg.content
                wxid = msg.sender
                chatinfo = msg.chat_info()
                group = chatinfo["chat_name"] if chatinfo["chat_type"]=="group" else None
                refer = msg.quote_content
                rsp = self.chat.get_answer(text, wxid, group, refer=refer)
                msg.quote(rsp)

    def send_text(self, msg, user):
        return self.wx.SendMsg(msg, user)

    def send_file(self, path, user):
        return self.wx.SendFiles(path, user)

    def send_image(self, path, user):
        return self.wx.SendFiles(path, user)




