import os
import requests
import json
from base.wedice_base import DiceBase
import re
# from wcferry import Wcf, WxMsg
import time
from bs4 import BeautifulSoup

class WeDiceUser(DiceBase):
    def __init__(self, config, send_text=None, send_file=None, send_image=None, get_info_by_wxid=None):
        super(WeDiceUser, self).__init__(config, send_text, send_file, send_image, get_info_by_wxid)
        self.cmds_self = [
            {"re": "\.jrrp", "fun": self.jrrp_self, "help": ".jrrp 今日人品"},
            {"re": "每日一卦", "fun": self.jrrp_yj_self, "help": "每日一卦 抽一卦"},
            {"re": "\.pc", "fun": self.coc_pc_self, "help": ".pc 打开角色管理面板"},
            {"re": "\.r.*", "fun": self.coc_roll_self, "help": ".r[表达式] 投骰"},
            {"re": "\.help.*", "fun": self.help_self, "help": ".help 帮助"},
            {"re": "塔罗", "fun": self.jrrp_tl_self, "help": "塔罗 塔罗牌来一卦"}
        ]

    def cmd2fun_self(self, cmd):
        for c in self.cmds_self:
            pattern = re.compile('^%s$'%c["re"])
            match = pattern.match(cmd)
            if match:
                return c
        return False


    def get_user_answer(self, cmd:str, wxid:str):
        # 处理或记录
        cd = self.cmd2fun_self(cmd)
        if cd:
            return cd["fun"](wxid=wxid, cmd=cmd)

    def help_self(self, **kwargs):
        result = "【使用帮助-个人】\n"
        result += "\n".join([l["help"] for l in self.cmds_self])
        return result


    def jrrp_yj_self(self, **kwargs):
        wxid = kwargs["wxid"]
        return self._dice_yijing("", wxid)


    def jrrp_tl_self(self, **kwargs):
        wxid = kwargs["wxid"]
        return self._dice_taluo("", wxid)

    def jrrp_self(self, **kwargs):
        wxid = kwargs["wxid"]
        return self._dice_jrrp("", wxid)

    def coc_pc_self(self, **kwargs):
        wxid = kwargs["wxid"]
        id = self._get_id_from_wxid(wxid)
        url = self.api + "/self?user=%s" % (id)
        return "请打开该链接管理角色卡：\n %s" % ( url)


    def coc_roll_self(self, **kwargs):
        wxid = kwargs["wxid"]
        cmd = kwargs["cmd"]
        return self.coc_roll_self_base(group="", wxid=wxid, cmd=cmd)

    def coc_roll_self_base(self, **kwargs):
        group, wxid = kwargs["group"], kwargs["wxid"]
        cmd = kwargs["cmd"]
        pattern = re.compile(r'\.r(?P<exp>.+)?')
        match = pattern.match(cmd)
        exp = match.group("exp").strip()
        if exp:
            if exp[0] == "h":
                hidden = True
                exp_ = exp[1:].strip()
            else:
                hidden = False
                exp_ = exp
            exp_, what = self._get_exp(exp_)
            if exp_:
                result = self.evaluate_expression(exp_)
            else:
                result = False
            # 基础投掷式
            if result:
                res = self._clear_dice(self._get_name(wxid), result, what if what else exp_)
                if hidden:
                    return "无法在个人中使用"
                else:
                    return res
            else:
                return "无法在个人中使用"
        else:
            result = self.evaluate_expression("1d100")
            res = self._clear_dice(self._get_name(wxid), result, "1d100")
            return res



