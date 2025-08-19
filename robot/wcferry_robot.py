import signal
import logging
import re
import time
import xml.etree.ElementTree as ET
from queue import Empty
from threading import Thread
from wcferry import Wcf, WxMsg
from configuration import Config
from base.wedice import WeDice

import time
from typing import Any, Callable

import schedule


__version__ = "39.0.10.1"

class Job(object):
    def __init__(self) -> None:
        pass

    def onEverySeconds(self, seconds: int, task: Callable[..., Any], *args, **kwargs) -> None:
        """
        每 seconds 秒执行
        :param seconds: 间隔，秒
        :param task: 定时执行的方法
        :return: None
        """
        schedule.every(seconds).seconds.do(task, *args, **kwargs)

    def onEveryMinutes(self, minutes: int, task: Callable[..., Any], *args, **kwargs) -> None:
        """
        每 minutes 分钟执行
        :param minutes: 间隔，分钟
        :param task: 定时执行的方法
        :return: None
        """
        schedule.every(minutes).minutes.do(task, *args, **kwargs)

    def onEveryHours(self, hours: int, task: Callable[..., Any], *args, **kwargs) -> None:
        """
        每 hours 小时执行
        :param hours: 间隔，小时
        :param task: 定时执行的方法
        :return: None
        """
        schedule.every(hours).hours.do(task, *args, **kwargs)

    def onEveryDays(self, days: int, task: Callable[..., Any], *args, **kwargs) -> None:
        """
        每 days 天执行
        :param days: 间隔，天
        :param task: 定时执行的方法
        :return: None
        """
        schedule.every(days).days.do(task, *args, **kwargs)

    def onEveryTime(self, times: int, task: Callable[..., Any], *args, **kwargs) -> None:
        """
        每天定时执行
        :param times: 时间字符串列表，格式:
            - For daily jobs -> HH:MM:SS or HH:MM
            - For hourly jobs -> MM:SS or :MM
            - For minute jobs -> :SS
        :param task: 定时执行的方法
        :return: None

        例子: times=["10:30", "10:45", "11:00"]
        """
        if not isinstance(times, list):
            times = [times]

        for t in times:
            schedule.every(1).days.at(t).do(task, *args, **kwargs)

    def runPendingJobs(self) -> None:
        schedule.run_pending()


class Robot(Job):
    """个性化自己的机器人
    """

    def __init__(self, config: Config, wcf: Wcf) -> None:
        super().__init__()
        self.wcf = wcf
        self.config = config
        self.LOG = logging.getLogger("Robot")
        self.wxid = self.wcf.get_self_wxid()
        self.allContacts = self.getAllContacts()
        self.chat = WeDice(self.config.Myself, self.wcf.send_text, self.wcf.send_file, self.wcf.send_image, self.wcf.get_info_by_wxid)

    @staticmethod
    def value_check(args: dict) -> bool:
        if args:
            return all(value is not None for key, value in args.items() if key != 'proxy')
        return False

    def toAt(self, msg: WxMsg) -> bool:
        """处理被 @ 消息
        :param msg: 微信消息结构
        :return: 处理状态，`True` 成功，`False` 失败
        """
        return self.toChitchat(msg)


    def toChitchat(self, msg: WxMsg) -> bool:
        rsp = None
        q = msg.content.replace(" ", "")
        if len(q) > 0:  # and q[0] == '.'
            # 获取回答主函数
            wxid = msg.sender
            group = None
            atwxids = []
            if msg.from_group():
                group = msg.roomid
                atwxids = self._get_at_wxids(msg)
                if "" in atwxids:
                    atwxids.remove("")
            rsp = self.chat.get_answer(q, wxid, group, atwxids)
        if rsp:
            if msg.from_group():
                self.sendTextMsg(rsp, msg.roomid)
            else:
                self.sendTextMsg(rsp, msg.sender)
            return True
        else:
            # self.LOG.error(f"无法从 ChatGPT 获得答案")
            return False

    def processMsg(self, msg: WxMsg) -> None:
        # 非群聊信息，按消息类型进行处理
        if msg.type == 37:  # 好友请求
            self.autoAcceptFriendRequest(msg)

        elif msg.type == 10000:  # 系统信息
            self.sayHiToNewFriend(msg)

        elif msg.type == 0x01:  # 文本消息
            # 让配置加载更灵活，自己可以更新配置。也可以利用定时任务更新。
            if msg.from_self():
                if msg.content == "^更新$":
                    self.config.reload()
                    self.LOG.info("已更新")
            else:
                self.toChitchat(msg)  # 闲聊
        elif msg.type == 49:  # 共享实时位置、文件、转账、链接
            pass
            # if not msg.from_self():
            #     self.toChitchat(msg)  # 闲聊

    def onMsg(self, msg: WxMsg) -> int:
        try:
            self.LOG.info(msg)  # 打印信息
            self.processMsg(msg)
        except Exception as e:
            self.LOG.error(e)

        return 0

    def enableRecvMsg(self) -> None:
        self.wcf.enable_recv_msg(self.onMsg)

    def enableReceivingMsg(self) -> None:
        def innerProcessMsg(wcf: Wcf):
            while wcf.is_receiving_msg():
                try:
                    msg = wcf.get_msg()
                    self.LOG.info(msg)
                    self.processMsg(msg)
                except Empty:
                    continue  # Empty message
                except Exception as e:
                    self.LOG.error(f"Receiving message error: {e}")

        self.wcf.enable_receiving_msg()
        Thread(target=innerProcessMsg, name="GetMessage", args=(self.wcf,), daemon=True).start()

    def sendTextMsg(self, msg: str, receiver: str, at_list: str = "") -> None:
        """ 发送消息
        :param msg: 消息字符串
        :param receiver: 接收人wxid或者群id
        :param at_list: 要@的wxid, @所有人的wxid为：notify@all
        """
        # msg 中需要有 @ 名单中一样数量的 @
        ats = ""
        if at_list:
            if at_list == "notify@all":  # @所有人
                ats = " @所有人"
            else:
                wxids = at_list.split(",")
                for wxid in wxids:
                    # 根据 wxid 查找群昵称
                    ats += f" @{self.wcf.get_alias_in_chatroom(wxid, receiver)}"

        # {msg}{ats} 表示要发送的消息内容后面紧跟@，例如 北京天气情况为：xxx @张三
        if ats == "":
            self.LOG.info(f"To {receiver}: {msg}")
            self.wcf.send_text(f"{msg}", receiver, at_list)
        else:
            self.LOG.info(f"To {receiver}: {ats}\r{msg}")
            self.wcf.send_text(f"{ats}\n\n{msg}", receiver, at_list)

    def getAllContacts(self) -> dict:
        """
        获取联系人（包括好友、公众号、服务号、群成员……）
        格式: {"wxid": "NickName"}
        """
        contacts = self.wcf.query_sql("MicroMsg.db", "SELECT UserName, NickName FROM Contact;")
        return {contact["UserName"]: contact["NickName"] for contact in contacts}

    def keepRunningAndBlockProcess(self) -> None:
        """
        保持机器人运行，不让进程退出
        """
        while True:
            self.runPendingJobs()
            time.sleep(1)

    def autoAcceptFriendRequest(self, msg: WxMsg) -> None:
        try:
            xml = ET.fromstring(msg.content)
            v3 = xml.attrib["encryptusername"]
            v4 = xml.attrib["ticket"]
            scene = int(xml.attrib["scene"])
            self.wcf.accept_new_friend(v3, v4, scene)

        except Exception as e:
            self.LOG.error(f"同意好友出错：{e}")

    def sayHiToNewFriend(self, msg: WxMsg) -> None:
        nickName = re.findall(r"你已添加了(.*)，现在可以开始聊天了。", msg.content)
        if nickName:
            # 添加了好友，更新好友列表
            self.allContacts[msg.sender] = nickName[0]
            self.sendTextMsg(f"Hi {nickName[0]}，我自动通过了你的好友请求。", msg.sender)

    def _get_at_wxids(self, msg):
        text = msg.xml
        text = text.replace("\s", "").replace("\n", "").replace("\t", "")
        pattern = re.compile(r'.*\[CDATA\[(?P<wxids>.*)\]\]')
        match = pattern.match(text)
        if match and match.group("wxids"):
            return match.group("wxids").split(",")
        else:
            return []

config = Config()
wcf = Wcf(debug=True)

def handler(sig, frame):
    wcf.cleanup()  # 退出前清理环境
    exit(0)

signal.signal(signal.SIGINT, handler)

robot = Robot(config, wcf)
robot.LOG.info(f"WeChatRobot【{__version__}】成功启动···")

# 接收消息
# robot.enableRecvMsg()     # 可能会丢消息？
robot.enableReceivingMsg()  # 加队列

# 让机器人一直跑
robot.keepRunningAndBlockProcess()