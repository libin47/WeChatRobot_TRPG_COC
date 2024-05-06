import os
import requests
import json
from base.dicebase import DiceBase
import re
from wcferry import Wcf, WxMsg
import time
from bs4 import BeautifulSoup

class Network(DiceBase):
    def __init__(self, config, wcf:Wcf):
        super(Network, self).__init__(config, wcf)
        self.data = {}
        self.api = config['api']
        self.cmds_group = [
            {"re": "\.boton", "fun": self.bot_on,  "help":".boton 启动骰娘", "super":True},
            {"re": "\.botoff", "fun": self.bot_off, "help": ".botoff 关闭骰娘"},
            {"re": "\.start", "fun": self.game_start, "help": ".start 游戏启动"},
            {"re": "\.pause", "fun": self.game_pause, "help": ".pause 游戏暂停"},
            {"re": "\.end", "fun": self.game_end, "help": ".end 游戏结束"},
            {"re": "\.log", "fun": self.get_log, "help": ".log 获取日志"},
            {"re": "\.jrrp", "fun": self.jrrp_group, "help": ".jrrp 今日人品"},
            {"re": "每日一卦", "fun": self.jrrp_yj_group, "help": "每日一卦 抽一卦"},
            {"re": "塔罗", "fun": self.jrrp_tl_group, "help": "塔罗 塔罗牌来一卦"},
            {"re": "\.pc(new)?", "fun": self.coc_new_pc, "help": ".pc 获取PC角色卡面板地址"},
            {"re": "\.admin", "fun": self.coc_admin, "help": ".admin 获取KP管理面板地址"},
            {"re": "\.r.*", "fun": self.coc_roll, "help": ".r[h][表达式] 投骰"},
            {"re": "\.ra.+", "fun": self.coc_ra, "help": ".ra[h][次数#][属性/技能] 进行属性和技能检定"},
            {"re": "\.stshow", "fun": self.coc_stshow, "help": ".stshow 查看基本信息"},
            {"re": "\.rc.+", "fun": self.coc_ra, "help": ".rc[h][次数#][属性/技能][目标值] 进行属性和技能检定，指定目标检定"},
            {"re": "\.st.+", "fun": self.coc_st, "help": ".st[hp/mp/san][+-][变动值] 数值变更"},
            {"re": "\.dex.+", "fun": self.coc_dex, "help": ".dex[姓名80(敏捷数值)] 敏捷排序"},
            {"re": "\.en", "fun": self.coc_en, "help": ".en 成长检定"},
            {"re": "\.sc.+", "fun": self.coc_sc, "help": ".sc[成功值]/[失败值] 理智检定"},
            {"re": "\.find.*", "fun": self.coc_find, "help": ".find[查询内容] 查询"},
            {"re": "\.ti", "fun": self.coc_ti, "help": ".ti 生成临时疯狂症状"},
            {"re": "\.li", "fun": self.coc_li, "help": ".li 生成总结疯狂症状"},
            {"re": "\.markshow.*", "fun": self.coc_mark_get, "help": ".markshow[线索组名称] 查看所有线索"},
            {"re": "\.mark.*", "fun": self.coc_mark, "help": ".mark[线索组名称] 只有引用其他文本时有效，将此内容标记为线索"},
            {"re": "\.flash", "fun": self.coc_flash, "help": ".flash 刷新群组设置"},
            {"re": "\.group.+", "fun": self.coc_group, "help": ".group [gd[购点数量]] [time[随机次数]] [s[大成功点数]] [f[大失败点数]] 房规设置"},
            {"re": "\.help.*", "fun": self.help_group, "help": ".help[r][ra] 帮助"},
        ]
        self.cmds_self = [
            {"re": "\.jrrp", "fun": self.jrrp_self, "help": ".jrrp 今日人品"},
            {"re": "每日一卦", "fun": self.jrrp_yj_self, "help": "每日一卦 抽一卦"},
            {"re": "\.pc", "fun": self.coc_pc_self, "help": ".pc 打开角色管理面板"},
            {"re": "\.r.*", "fun": self.coc_roll_self, "help": ".r[表达式] 投骰"},
            {"re": "\.help.*", "fun": self.help_self, "help": ".help 帮助"},
            {"re": "塔罗", "fun": self.jrrp_tl_self, "help": "塔罗 塔罗牌来一卦"}
        ]

    def cmd2fun_group(self, cmd):
        for c in self.cmds_group:
            pattern = re.compile('^%s$'%c["re"])
            match = pattern.match(cmd)
            if match:
                return c
        return False

    def cmd2fun_self(self, cmd):
        for c in self.cmds_self:
            pattern = re.compile('^%s$'%c["re"])
            match = pattern.match(cmd)
            if match:
                return c
        return False

    def get_answer(self, cmd: str, msg: WxMsg) -> str:
        if msg.type == 49:
            msgxml = BeautifulSoup(msg.content, 'xml')
            cmd = msgxml.find("title").text
        # 获取回答主函数
        isgroup = msg.from_group()
        wxid = msg.sender
        cmd = self._clear_cmd(cmd)
        if isgroup:
            group = msg.roomid
            self._init_group(group)
            isat = False
            if "users" in self.data[group].keys():
                for key in self.data[group]["users"]:
                    if msg.is_at(key):
                        isat = True
                        result = self.get_group_answer(cmd, key, group, msg, wxid)
                        self.save_log(group=group, wxid=wxid, cmd=cmd, result=result)
                        if result:
                            self.wcf.send_text(f"{result}", group)
            if not isat:
                result = self.get_group_answer(cmd, wxid, group, msg)
                self.save_log(group=group, wxid=wxid, cmd=cmd, result=result)
                return result
            else:
                return ""
        else:
            result = self.get_user_answer(cmd, wxid)
            return result

    def get_group_answer(self, cmd:str, wxid:str, group:str, msg:WxMsg, sender:str=""):
        # 处理或记录
        cd = self.cmd2fun_group(cmd)
        if cd:
            if not ("super" in cd.keys() and cd["super"]) and (not ("status" in self.data[group].keys() and self.data[group]["status"])):
                return
            if sender:
                return cd["fun"](group=group, wxid=wxid, cmd=cmd, sender=sender, msg=msg)
            else:
                return cd["fun"](group=group, wxid=wxid, cmd=cmd, sender=wxid, msg=msg)

    def get_user_answer(self, cmd:str, wxid:str):
        # 处理或记录
        cd = self.cmd2fun_self(cmd)
        if cd:
            return cd["fun"](wxid=wxid, cmd=cmd)

    def coc_flash(self, **kwargs):
        group = kwargs["group"]
        data_new = self._get_group_status(group)
        if data_new:
            self.data[group] = data_new
            self.data[group]["users"] = list(self.wcf.get_chatroom_members(group))
        return "【群规】已刷新：天命%s或购点%s，大成功%s，大失败%s"%(self.data[group]["config"]["dicetime"], self.data[group]["config"]["point"],
                                                                self.data[group]["config"]["succnum"] if "succnum" in self.data[group]["config"].keys() and self.data[group]["config"]["succnum"]>0 else "默认",
                                                                self.data[group]["config"]["failnum"] if "failnum" in self.data[group]["config"].keys()  and  self.data[group]["config"]["failnum"]>0 else "默认")

    def help_group(self, **kwargs):
        cmd = kwargs["cmd"]
        pattern = re.compile(r'\.help\s*(?P<cmd>.*)?')
        match = pattern.match(cmd)
        key = match.group("cmd")
        if key:
            if key.strip() == "r":
                result = "【使用帮助-表达式】\n 1、基础投掷 \n .r[h][5#][1d100][b2][p3][+-*/][2d10] h表示暗骰，#前面数字代表投骰次数，b接奖励数量，p接惩罚骰数量，支持四则运算\n2、快捷投掷 .r沙鹰 这样使用的前提是角色卡中有名为沙鹰的武器\n3、.ra .rc 详见.help ra \n4、.r 等同于.r1d100"
            elif key.strip() == "ra" or key.strip()=="rc":
                result = "【使用帮助-属性技能检定】\n .ra[h][3#][b2][p3][属性/技能][目标值] h表示暗骰，#前面数字代表投骰次数，b接奖励数量，p接惩罚骰数量，，如果指定目标值则以目标值进行判断，但不会为自己的角色卡添加成长标记"
            else:
                result = "【使用帮助-群里】\n 使用.help r或.help ra 查看具体帮助，其他的指令暂无详细说明"
            return result
        else:
            result = "【使用帮助-群里】\n"
            result += "\n".join([l["help"] for l in self.cmds_group])
            return result

    def help_self(self, **kwargs):
        result = "【使用帮助-个人】\n"
        result += "\n".join([l["help"] for l in self.cmds_self])
        return result


    def save_log(self,  **kwargs):
        group, wxid, cmd, result = kwargs["group"], kwargs["wxid"], kwargs["cmd"], kwargs["result"]
        if group in self.data.keys() and "status" in self.data[group].keys() and \
                self.data[group]["status"] and self.data[group]["Gaming"] == "start":
            self.log_input(group, cmd, self._get_name(wxid))
            if result:
                self.log_input(group, result, "骰娘")

    def get_log(self,  **kwargs):
        group = kwargs["group"]
        self.log_get(group)

    def bot_on(self, **kwargs):
        group = kwargs["group"]
        return self._bot_on_or_off(group, True)

    def bot_off(self, **kwargs):
        group = kwargs["group"]
        return self._bot_on_or_off(group, False)

    def game_start(self, **kwargs):
        group = kwargs["group"]
        return self._game_start_or_end(group, "start")

    def game_pause(self, **kwargs):
        group = kwargs["group"]
        return self._game_start_or_end(group, "pause")

    def game_end(self, **kwargs):
        group = kwargs["group"]
        return self._game_start_or_end(group, "end")

    def jrrp_group(self, **kwargs):
        group = kwargs["group"]
        wxid = kwargs["wxid"]
        return self._dice_jrrp(group, wxid)

    def jrrp_yj_group(self, **kwargs):
        group = kwargs["group"]
        wxid = kwargs["wxid"]
        return self._dice_yijing(group, wxid)

    def jrrp_yj_self(self, **kwargs):
        wxid = kwargs["wxid"]
        return self._dice_yijing("", wxid)

    def jrrp_tl_group(self, **kwargs):
        group = kwargs["group"]
        wxid = kwargs["wxid"]
        return self._dice_taluo(group, wxid)

    def jrrp_tl_self(self, **kwargs):
        wxid = kwargs["wxid"]
        return self._dice_taluo("", wxid)

    def jrrp_self(self, **kwargs):
        wxid = kwargs["wxid"]
        return self._dice_jrrp("", wxid)

    def coc_mark(self, **kwargs):
        msg = kwargs["msg"]
        group = kwargs["group"]
        cmd = kwargs["cmd"]
        pattern = re.compile(r'\.mark(?P<key>.*)')
        match = pattern.match(cmd)
        key = match.group("key").strip() if match.group("key") else ""
        if msg.type!=49:
            return "[.mark]指令需引用内容"
        xml = BeautifulSoup(msg.content, 'xml')
        xml2 = xml.find_all("content")[-1].contents[0].strip()
        if BeautifulSoup(xml2, 'xml').find("msg"):
            pass
        else:
            text = xml2
            self.mark_input(group, text, key)

    def coc_mark_get(self, **kwargs):
        group = kwargs["group"]
        cmd = kwargs["cmd"]
        pattern = re.compile(r'\.markshow(?P<key>.*)')
        match = pattern.match(cmd)
        key = match.group("key").strip() if match.group("key") else ""
        self.mark_get(group, key)


    def coc_admin(self, **kwargs):
        group = kwargs["group"]
        url = self.api + "/admin?group=%s" % (group)
        return "【KP】请打开该链接查看和管理所有PC角色卡：\n %s" % (url)

    def coc_pc_self(self, **kwargs):
        wxid = kwargs["wxid"]
        id = self._get_id_from_wxid(wxid)
        url = self.api + "/self?user=%s" % (id)
        return "请打开该链接管理角色卡：\n %s" % ( url)

    def coc_new_pc(self, **kwargs):
        group, wxid = kwargs["group"], kwargs["wxid"]
        url = self.api + "/coc?group=%s&user=%s" % (group, wxid)
        return "【%s】请打开该链接创建或编辑角色卡：\n %s" % (self._get_name(wxid), url)

    def coc_ra(self, user={}, **kwargs):
        group, wxid = kwargs["group"], kwargs["wxid"]
        cmd = kwargs["cmd"]
        pattern = re.compile(r'\.r[ac](?P<hidden>h)?((?P<times>\d+)#)?(?P<bonus>b\d*)?(?P<penalty>p\d*)?(?P<att>[^\d]*)?(?P<gold>\d+)?')
        match = pattern.match(cmd)
        if match:
            gold = match.group("gold")
            att = match.group("att")
            times = int(match.group("times")) if match.group("times") else 1
            hidden = match.group("hidden")
            exp = "1d100"
            if match.group("bonus"):
                number = match.group("bonus")[1:] if match.group("bonus")[1:] else 1
                exp += "b%s" % number
            if match.group("penalty"):
                number = match.group("penalty")[1:] if match.group("penalty")[1:] else 1
                exp += "p%s" % number
            if gold:
                gold = int(gold.strip())
                if times == 1:
                    result = self.roll_dice(exp)
                    res = self._clear_check(self._get_name(wxid), result, self.data[group]["config"], att, gold)
                else:
                    result = [self.roll_dice(exp) for i in range(times)]
                    res = self._clear_check(self._get_name(wxid), result, self.data[group]["config"], att, gold, times)
                if hidden:
                    self._send_hidden(group, kwargs["sender"], res)
                    return self._hidden_result(cmd, wxid)
                else:
                    return res
            else:
                if "name" not in user.keys():
                    return self._nouser_error(cmd, wxid)
                gold = -1
                skillindex = -1
                if att:
                    att = att.strip()
                else:
                    self._cmd_error(cmd, wxid)
                if att in user["attribute"].keys():
                    gold = user["attribute"][att]
                elif att in user["attex"].keys():
                    gold = user["attex"][att]
                else:
                    for i in range(len(user["skill"])):
                        sk = user["skill"][i]
                        if sk["showName"] == att or ("subName" in sk.keys() and sk["subName"]==att) or sk["showName"][-len(att):]==att:
                            gold = sk["defaultPoint"] + sk["interPoint"] + sk["workPoint"] + sk["ensurePoint"]
                            if not sk["ensure"] and sk["levelup"]:
                                skillindex = i
                if gold < 0:
                    return "【%s】未找到【%s】属性/技能" % (user['name'], att)
                else:
                    if times == 1:
                        result = self.roll_dice(exp)
                        # 标记可成长
                        if skillindex >= 0 and (result[-1] == 1 or result[-1] <= gold):
                            self._sign_skill_ensure(user, skillindex)
                        res = self._clear_check(user['name'], result, self.data[group]["config"], att, gold)
                    else:
                        result = []
                        for i in range(times):
                            rt = self.roll_dice(exp)
                            # 标记可成长
                            if skillindex >= 0 and (rt[-1] == 1 or rt[-1] <= gold):
                                self._sign_skill_ensure(user, skillindex)
                            result.append(rt)
                        res = self._clear_check(user['name'], result, self.data[group]["config"], att, gold, times)
                    if hidden:
                        self._send_hidden(group, kwargs["sender"], res)
                        return self._hidden_result(cmd, wxid)
                    else:
                        return res
        else:
            return self._cmd_error(cmd, wxid)

    def coc_roll_self(self, **kwargs):
        wxid = kwargs["wxid"]
        cmd = kwargs["cmd"]
        return self.coc_roll(group="", wxid=wxid, cmd=cmd)

    def coc_dex(self, **kwargs):
        group, wxid = kwargs["group"], kwargs["wxid"]
        cmd = kwargs["cmd"]
        # 指令内涵数据
        pattern = re.compile(r'([^\d]+)([\d]+)')
        matches = pattern.findall(cmd[4:])
        name = []
        for match in matches:
            chinese = match[0].strip()
            number = int(match[1])
            name.append({'name': chinese, 'dex': number})
        # 用户数据
        users = self._get_users_data(group)
        users = users["card"]
        for key in users.keys():
            user = users[key]
            name.append({'name': user["name"], 'dex': int(user["attribute"]["敏捷"])})
        sorted_data = sorted(name, key=lambda x: x["dex"], reverse=True)
        result = "【战斗轮行动顺序】\n"
        for d in sorted_data:
            result += "%s%s[%s] -> "%(d["name"], d["dex"], d["dex"]+50)
        result = result[:-4]
        return result

    def coc_roll(self, **kwargs):
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
            result = self.evaluate_expression(exp_)
            # 基础投掷式
            if result:
                res = self._clear_dice(self._get_name(wxid), result, exp)
                if hidden:
                    self._send_hidden(group, kwargs["sender"], res)
                    return self._hidden_result(cmd, wxid)
                else:
                    return res
            else:
                user = self._get_user_data(group, wxid)
                # 角色获取
                if user:
                    # 武器
                    weapon = self._roll_weapon(exp, user)
                    if weapon:
                        return weapon
                    else:
                        if exp[0] == "a":
                            return self.coc_ra(user=user, **kwargs)
                        elif exp[0] == "c":
                            return self.coc_ra(user=user, **kwargs)
                        else:
                            return self._cmd_error(cmd, wxid)
                else:
                    if exp[0] == "c":
                        return self.coc_ra(user={},**kwargs)
                    else:
                        return self._cmd_error(cmd, wxid)
        else:
            result = self.evaluate_expression("1d100")
            res = self._clear_dice(self._get_name(wxid), result, "1d100")
            return res

    def coc_st(self, **kwargs):
        group, wxid = kwargs["group"], kwargs["wxid"]
        cmd = kwargs["cmd"]

        user = self._get_user_data(group, wxid)
        if user.keys():
            exp = cmd[3:].strip()
            if exp[0] == "&":
                wplist = exp.replace("&", "").split("=")
                if len(wplist)==2:
                    user["weapon"].append({"名称":wplist[0], "伤害":wplist[1]})
                    self._update_card(user)
                    return "【%s】添加武器/快捷表达式:%s:%s"%(user["name"], wplist[0], wplist[1])
                else:
                    return self._cmd_error(cmd, wxid)
            else:
                pattern = re.compile(r'(?P<attex>[^\d+-]+)\s*(?P<cals>[+-])?\s*(?P<number>[\dDd]+)')
                matchs = pattern.findall(exp)
                res = "【%s】更新:"%user["name"]
                errorskill = ""
                errornotfound = ""
                for match in matchs:
                    exp = match[0].strip().upper()
                    cals = match[1]
                    number_exp = match[2]
                    if "d" in number_exp or "D" in number_exp:
                        number = self.roll_dice(number_exp)[-1]
                    else:
                        number = int(number_exp)
                    # 先找exp:属性
                    if exp in user["attribute"].keys():
                        if cals=="+":
                            result = int(user["attribute"][exp]) + number
                        elif cals=="-":
                            result = int(user["attribute"][exp]) - number
                        else:
                            result = number
                        result = result if result > 0 else 0
                        res += "\n【%s】[%s]->[%s]"%(exp, user["attribute"][exp], result)
                        user["attribute"][exp] = result
                    elif exp in user["attex"].keys():
                        if cals=="+":
                            result = int(user["attex"][exp]) + number
                        elif cals=="-":
                            result = int(user["attex"][exp]) - number
                        else:
                            result = number
                        if (exp+"_MAX") in user["attex"].keys():
                            result = user["attex"][exp+"_MAX"] if user["attex"][exp+"_MAX"]<result else result
                        res += "\n【%s】[%s]->[%s]"%(exp, user["attex"][exp], result)
                        user["attex"][exp] = result
                    else:
                        for i in range(len(user["skill"])):
                            sk = user["skill"][i]
                            find = False
                            if sk["showName"]==exp or ("subName" in sk.keys() and sk["subName"]==exp) or sk["showName"][-len(exp):]==exp:
                                find = True
                                if cals=="+":
                                    result = int(user["skill"][i]["ensurePoint"]) + number
                                    res += "\n【%s】[%s]->[%s]"%(exp, user["skill"][i]["ensurePoint"]+user["skill"][i]["defaultPoint"]+user["skill"][i]["workPoint"]+user["skill"][i]["interPoint"], result+user["skill"][i]["workPoint"]+user["skill"][i]["interPoint"]+user["skill"][i]["defaultPoint"])
                                    user["skill"][i]["ensurePoint"] = result
                                elif cals=="-":
                                    result = int(user["skill"][i]["ensurePoint"]) - number
                                    res += "\n【%s】[%s]->[%s]"%(exp, user["skill"][i]["ensurePoint"]+user["skill"][i]["defaultPoint"]+user["skill"][i]["workPoint"]+user["skill"][i]["interPoint"], result+user["skill"][i]["workPoint"]+user["skill"][i]["interPoint"]+user["skill"][i]["defaultPoint"])
                                    user["skill"][i]["ensurePoint"] = result
                                else:
                                    errorskill += "【%s】"%exp
                                break
                        if not find:
                            errornotfound += "【%s】"%exp
                if errorskill:
                    res += "\n 不支持直接给技能赋值，请使用+-调整成长值，车卡请使用.pc：%s"%errorskill
                if errornotfound:
                    res += "\n 以下属性/技能未找到：%s"%errornotfound
                self._update_card(user)
                return res  
        else:
            return self._nouser_error(cmd, wxid)
        return self._cmd_error(cmd, wxid)

    def coc_sc(self, **kwargs):
        group, wxid = kwargs["group"], kwargs["wxid"]
        cmd = kwargs["cmd"]
        pattern = re.compile(r'\.sc\s*(?P<sucess>[0-9dD\s]+)\/(?P<fail>[0-9dD\s]+)')
        match = pattern.match(cmd)
        if match:
            user = self._get_user_data(group, wxid)
            if user:
                gold = user["attex"]["SAN"]
                result = self.evaluate_expression("1d100")[0]
                nandu = self._roll_nandu(result, gold, self.data[group]["config"])
                if "成功" in nandu:
                    if "大成功" in nandu:
                        sucess_result = 0
                    else:
                        sucess = match.group("sucess").strip()
                        sucess_result = self.evaluate_expression(sucess)[0]
                    if type(sucess_result) == int:
                        r = gold - sucess_result
                        r = (r if r>0 else 0) if r<user["attex"]["SAN_MAX"] else user["attex"]["SAN_MAX"]
                        user["attex"]["SAN"] = r
                        self._update_card(user)
                        return "%s理智检定【%s:%s/%s】,SAN值扣除[%s],【%s->%s】" % (user['name'],nandu, result, gold, sucess_result, gold, r)
                    else:
                        return "表达式错误：【%s】" % sucess
                else:
                    fail = match.group("fail").strip()
                    if "大失败" in nandu:
                        fail_result = max(self.evaluate_expression("100#" + fail)[0])
                    else:
                        fail_result = self.evaluate_expression(fail)[0]
                    if type(fail_result) == int:
                        r = gold - fail_result
                        r = (r if r > 0 else 0) if r < user["attex"]["SAN_MAX"] else user["attex"]["SAN_MAX"]
                        user["attex"]["SAN"] = r
                        self._update_card(user)
                        return "%s理智检定【%s:%s/%s】,SAN值扣除[%s],【%s->%s】" % (user['name'],nandu, result, gold, fail_result, gold, r)
                    else:
                        return self._cmd_error(cmd, wxid)
            else:
                return self._nouser_error(cmd,wxid)
        else:
            return self._cmd_error(cmd, wxid)

    def coc_en(self, **kwargs):
        group, wxid = kwargs["group"], kwargs["wxid"]
        cmd = kwargs["cmd"]
        user = self._get_user_data(group, wxid)
        if not user:
            return self._nouser_error(cmd,wxid)
        if self.data[group]["Gaming"] != "end":
            return "[%s]游戏尚未结束，无法进行幕间成长！"%(self._get_name(wxid))
        sl = []
        sanity_point = 0
        text = ""
        for skill in user["skill"]:
            if skill["ensure"] and skill["levelup"]:
                skill["ensure"] = False
                result = self.evaluate_expression('1d100')[0]
                skillnumber = skill["defaultPoint"] + skill["workPoint"] +skill["interPoint"] +skill["ensurePoint"]
                if result > skillnumber or result > 95:
                    skillup = self.evaluate_expression('1d10')[0]
                    text += "\n[%s]成长[%s->%s]" % (skill["showName"], skillnumber, skillup+skillnumber)
                    if (skillup+skillnumber >= 90) and (skillnumber < 90):
                        sanity_point += 1
                    skill["ensurePoint"] = skill["ensurePoint"] + skillup
                else:
                    text += "\n[%s：%s]成长失败" % (skill["showName"], skillnumber)
            sl.append(skill)
        user["skill"] = sl
        if sanity_point>0:
            sanity_up = []
            for i in range(sanity_point):
                sanity_up.append(self.evaluate_expression('2d6')[0])
            san_origin = user["attex"]['SAN']
            user["attex"]['SAN'] = san_origin + sum(sanity_up) if san_origin + sum(sanity_up)<100 else 99
            text += "\n因为技能成长，获得%s理智：[%s->%s]"%(sanity_up, san_origin, user["attex"]['SAN'])
        self._update_card(user)
        return '[%s] 进行幕间成长：%s'%(user['name'], text if text else "\n没有可成长技能")

    def coc_stshow(self, **kwargs):
        group, wxid = kwargs["group"], kwargs["wxid"]
        cmd = kwargs["cmd"]
        user = self._get_user_data(group, wxid)
        if user.keys():
            return "[%s]HP:%s/%s,MP:%s/%s,SAN:%s/%s,敏捷%s" % (user["name"], user["attex"]["HP"], user["attex"]["HP_MAX"], user["attex"]["MP"],
                                                             user["attex"]["MP_MAX"], user["attex"]["SAN"], user["attex"]["SAN_MAX"], user["attribute"]["敏捷"])
        else:
            return self._nouser_error(cmd, wxid)

    def coc_find(self, **kwargs):
        group, wxid = kwargs["group"], kwargs["wxid"]
        cmd = kwargs["cmd"]
        pattern = re.compile(r'\.find\s*(?P<value>.*)')
        match = pattern.match(cmd)
        if match:
            user = self._get_user_data(group, wxid)
            if user.keys():
                key = match.group("value")
                if key:
                    if key in ["年龄", "年纪", "age", "AGE"]:
                        return "[%s]今年【%s】岁" % (user["name"], user["info"]["age"])
                    elif key in ["物品", "item", "ITEAM", "随身物品"]:
                        return "[%s]带着以下物品：\n%s" % (user["name"], user["item"])
                    elif key in ["性别", "sex", "SEX"]:
                        return "[%s]性别为【%s】" % (user["name"], user["info"]["sex"])
                    elif key in ["时代", "time", "TIME", "年代"]:
                        return "[%s]是【%s】时期角色" % (user["name"], user["info"]["time"])
                    elif key in ["故乡", "出身地", "born", "BORN"]:
                        return "[%s]出身地在【%s】" % (user["name"], user["info"]["whereborn"])
                    elif key in ["居住地", "家乡", "live", "LIVE"]:
                        return "[%s]居住地在【%s】" % (user["name"], user["info"]["wherelive"])
                    elif key in ["状态", "信息"]:
                        result = "[%s]的状态\n"%(user["name"],)
                        result += "【HP】%s/%s\n" % (user["attex"]["HP"], user["attex"]["HP_MAX"])
                        result += "【MP】%s/%s\n" % (user["attex"]["MP"], user["attex"]["MP_MAX"])
                        result += "【SAN】%s/%s\n" % (user["attex"]["SAN"], user["attex"]["SAN_MAX"])
                        result += "【DB】%s 【体格】%s 【MOV】%s\n" % (
                            user["attex"]["DB"], user["attex"]["体格"], user["attex"]["MOV"])
                        return result
                    elif key.upper() in user["attex"].keys():
                        return "[%s]的[%s]为【%s】" % (user["name"], key, user["attex"][key.upper()])
                    elif key in ["职业", "工作", "work", "WORK"]:
                        return "[%s]职业为【%s】" % (user["name"], user["职业"])
                    elif key in user["attribute"].keys():
                        return "[%s]的%s为【%s】" % (user["name"], key, user["attribute"][key])
                    elif key in ["背景", "故事", "背景故事"]:
                        return "[%s]的背景故事：\n%s" % (user["name"], "\n".join(["【%s】%s"%(k, user["story"][k]) for k in user["story"].keys()]))
                    elif key in user["story"].keys():
                        return "[%s]的【%s】\n%s" % (user["name"], key, user["story"][key])
                    elif key in user["CR"].keys():
                        return "[%s]的[%s]为【%s】" % (user["name"], key, user["CR"][key])
                    elif key in ["生活水平", "财产", "CR", "富有"]:
                        return "[%s]生活水平为【%s】" % (user["name"], user["CR"]["CR"])
                    elif key in ["武器", "weapon", "WEAPON"]:
                        return "[%s]的武器有:\n%s" % (user["name"], "\n".join(["【%s】%s"%(user["weapon"][k]["名称"], user["weapon"][k]["伤害"]) for k in range(len(user["weapon"]))]))
                    elif key in [user["weapon"][k]["名称"] for k in range(len(user["weapon"]))]:
                        for k in range(len(user["weapon"])):
                            if user["weapon"][k]["名称"]==key:
                                return "[%s]的武器【%s】伤害为【%s】" % (user["name"], key, user["weapon"][k]["伤害"])
                    elif key in [user["skill"][k]["showName"] for k in range(len(user["skill"]))]:
                        for k in range(len(user["skill"])):
                            if user["skill"][k]["showName"]==key:
                                sk = user["skill"][k]
                                return "[%s]的技能【%s】为【%s】" % (user["name"], key, sk["defaultPoint"] + sk["interPoint"] + sk["workPoint"] + sk["ensurePoint"])                 
                    elif key in ["技能", "skill", "SKILL"]:
                        r = []
                        for sk in user["skill"]:
                            if sk["interPoint"] + sk["workPoint"] > 0:
                                r.append("[%s]%s"%(sk["showName"],  sk["defaultPoint"] + sk["interPoint"] + sk["workPoint"] + sk["ensurePoint"]))
                        return "[%s]的技能有:\n%s" % (user["name"], "\n".join(r))

                    return "【%s】未能理解您想查什么"%(key)
                else:
                    result = "【%s】查看完整信息：\n%s\n" % (user["name"], self.api + "/show?pcid=" + user["_id"])
                    result += "【信息】%s-%s岁-%s\n" % (user["info"]["sex"], user["info"]["age"], user["职业"])
                    result += "【HP】%s/%s\n" % (user["attex"]["HP"], user["attex"]["HP_MAX"])
                    result += "【MP】%s/%s\n" % (user["attex"]["MP"], user["attex"]["MP_MAX"])
                    result += "【SAN】%s/%s\n" % (user["attex"]["SAN"], user["attex"]["SAN_MAX"])
                    result += "【DB】%s 【体格】%s 【MOV】%s\n" % (
                    user["attex"]["DB"], user["attex"]["体格"], user["attex"]["MOV"])
                    result += "【属性】" + ",".join(
                        ["%s%s" % (k, user["attribute"][k]) for k in user["attribute"].keys()]) + "\n"
                    result += "【技能】"
                    for k in user["skill"]:
                        if k["workPoint"] > 0 or k["interPoint"] > 0:
                            result += k["showName"] + str(
                                k["workPoint"] + k["interPoint"] + k["ensurePoint"] + k["defaultPoint"])
                    result += "\n【武器】\n"
                    for w in user["weapon"]:
                        result += "%s: %s\n" % (w["名称"], w["伤害"])
                    result += "【物品】%s\n" % user["item"]
                    result += "【个人介绍】%s\n" % user["story"]["个人介绍"]
                    result += "【特质】%s\n" % user["story"]["特质"]

                    return result
            else:
                return self._nouser_error(cmd, wxid)

    def coc_ti(self, **kwargs):
        group, wxid = kwargs["group"], kwargs["wxid"]
        cmd = kwargs["cmd"]
        user = self._get_user_data(group, wxid)
        if user.keys():
            return self._get_fk(user, True)
        else:
            return self._nouser_error(cmd, wxid)

    def coc_li(self, **kwargs):
        group, wxid = kwargs["group"], kwargs["wxid"]
        cmd = kwargs["cmd"]
        user = self._get_user_data(group, wxid)
        if user.keys():
            return self._get_fk(user, False)
        else:
            return self._nouser_error(cmd, wxid)

    def coc_group(self, **kwargs):
        group, wxid = kwargs["group"], kwargs["wxid"]
        cmd = kwargs["cmd"]
        pattern = re.compile(r'\.group\s*(?P<gd>gd(?P<gdnum>\d+))?\s*(?P<time>time(?P<timenum>\d+))?\s*(?P<s>s(?P<snum>\d+))?\s*(?P<f>f(?P<fnum>\d+))?')
        match = pattern.match(cmd)
        if match:
            config = self.data[group]["config"]
            if not match.group("gd") and not match.group("time") and not match.group("s") and not match.group("f"):
                return "当前房规为:\n车卡:天命[%s]或购点[%s]\n检定:大成功[%s];大失败[%s]"\
                    %(config["dicetime"], config["point"], config["succnum"] if "succnum" in config.keys() else "默认", config["failnum"] if "failnum" in config.keys() else "默认",)
            if match.group("gd"):
                gdnum = int(match.group("gdnum"))
                config["point"] = gdnum
            if match.group("time"):
                dicetime = int(match.group("timenum"))
                config["dicetime"] = dicetime
            if match.group("s"):
                snum = int(match.group("snum"))
                config["succnum"] = snum
            if match.group("f"):
                fnum = int(match.group("fnum"))
                config["failnum"] = fnum
            self.data[group]["config"] = config
            self._update_group_config(group, config)
            return "房规已更新！\n" + "当前房规为:\n车卡:天命[%s]或购点[%s]\n检定:大成功[%s];大失败[%s]"\
                    %(config["dicetime"], config["point"], config["succnum"] if "succnum" in config.keys() else "默认", config["failnum"] if "failnum" in config.keys() else "默认",)
        return self._cmd_error(cmd, wxid)

    def _get_fk(self, user, now):
        r = [
                ["失忆", "这是哪儿？怎么回事？该怎么办？", "你对过去一段时间内发生的事情完全没有印象。你无法解释自己怎么来的这里，为什么要来这里。", ""],
                ["极端信念驱使", "再听唔到我继续讲！", "刚刚发生的事情有如晴天霹雳，你突然顿悟了，你的信仰或者信念得到了极大的加强。这次顿悟会将你的思想信念或信仰变得极端、狂热，达到远超正常水准的疯狂状态。立即根据背景进行相应的扮演。", "KP应当查看调查员背景当中的思想信念条目。调查员痴迷于其中最恰当的一项，会表现得非常乖张。如果这个条目里什么都没写，KP可选取任何适合的内容。"],
                ["昏厥", "我受不了了！", "事情超出了常人的承受能力，你的头脑过载，晕倒在地，坠入遗忘和无知的黑暗之中。你立刻倒地并失去意识。", ""],
                ["仓皇逃窜", "跑啊！逃命啊！！", "你会强迫性地远离当前位置。你可以不择手段，即使要推倒前面的人、甩下后面的人，你也会做。", "持续逃窜，直到累倒在地。进行一次困难难度的CON检定，失败表示你昏过去了。"],
                ["歇斯底里", "那角度！那声音！它要来了！", "你看到、听到、理解到的东西，人类有限的头脑实在无法承受。", "选择一项歇斯底里症状"],
                ["偏执", "我知道！你们都针对我！", "突然，你觉得只有自己值得相信。其他人全都不能信。\n每个人都试图逮住你——即便是所谓那些盟友和伙伴也不例外！你经受严重的偏执，不会听从别人的解释。你正在被监视，正在被背叛，你看见的一切东西都是欺骗你的高明伎俩。你会强迫性地同你的朋友和盟友，“真正的敌人”，变得敌对。", ""],
                ["假性残疾", "我这是怎么了？", "你身体的某个部位突然罢工了。", "选择一个部位"],
                ["暴力行为", "唔唔唔呀呀呀啊啊啊！", "你怒火中烧，疯狂的怒火烧遍你全身。你突然爆发，行动失去控制，对你周围的物品、朋友、敌人无差别地造成暴力和破坏。", "每轮选择一次疯狂进攻的目标[周围的实物、敌人、朋友]，结束后力竭倒地，CON检定是否昏过去。"],
                ["认错人", "噢，我的天啊！是你！！", "你突然发现，有个对你来说很重要的人出现在了这里——他为什么会在这里并不重要，重要的是他已经来了。根据你和此人之间的关系种类，立即开始相应的扮演。", "KP应当查看调查员背景当中的重要之人条目。调查员会将场景中的其他人错认成自己的重要之人。如果这个条目里什么都没写，KP可以选取任何适合的内容。"],
                ["恐惧症"],
                ["躁狂症"]
        ]
        rz = [
            ["失忆症","我是谁？","你醒来以后发现自己已经身处陌生的地点。你不记得这段时间发生了什么。你也无法回忆起自己是怎样来到这里的。更可怕的是，你似乎记不起自己是谁了！你只知道你现在身上满是伤痕和瘀青，衣服上还有干涸的血迹。"],
            ["遍体鳞伤", "啊哟！", "你醒转过来，发现自己躺在排水沟或下水道里。你的身体疼痛难忍，如同被一个专业拳击手连续痛打五场一样。你缓缓站起身来，看到自己遍体鳞伤，全身是淤青——有人把你好好地“教训”了一通。你的嘴唇肿成香肠嘴，眼眶黑成熊猫眼。\n更要命的是，你身上所有的物品和钱财都不见了，肯定是被神秘袭击者偷走了，但你想不起来他是谁。如果你身上带着宝贵之物（按照角色背景），必须进行一次幸运检定，决定它是否被盗。\n你的当前HP减少一半（但不会造成重伤）"],
            ["寻找重要之人", "你在哪里？", "你为什么在这里？为什么在喊着你认识的人的名字？人们盯着你看；你弄不明白你怎么来到的这里，又为什么不顾一切地要找到这个人。如果这个人住得很远，你可能也会走很远……", " KP应当查看调查员背景当中的重要之人条目并选择一项。如果这个条目里什么都没写，KP可以选取任何适合的内容。"],
            ["被收容", "放我出去！", "你醒来时发现自己手腕上戴着镣铐。你看起来是独自被关在一间屋子里了。屋子里没有窗户。门上有个带结实铁栅栏的小窗口。“放我出去！”你大呼道，如同疯子一般狂叫。慢慢地，你平静了下来，回想起了刚才让你被关起来的事情。这时响起了门打开的声音，有人说道：“现在我们能正常说话了吗？”", "根据调查员疯狂发作的诱因，KP应当决定调查员醒来时身处位置是拘留所、医院病房还是疯人院看护室。"],
            ["被劫", "不见了！我被抢了！", "你聚拢意识，发现自己只身一人。很明显已经过去了一段时间，或者更多。你感觉晕头转向，检查一下自己的口袋，却沮丧地发现自己被人打劫了。\n你印象里携带的所有装备、武器和现金都不见了——实际上，所有值钱的东西都完全找不到了。\n如果你携带着宝贵之物（按照角色背景），必须进行一次幸运检定，决定它是否被盗。"],
            ["暴力事件", "这是我做的吗？", "你突然恢复理智，环顾四周。你的周围是一片残破：人们倒在地上呻吟，有些人在处理伤口，还有些人浑身鲜血。有些人已经一动不动了。\n你突然产生了一个突兀的想法：难道这是我做的？你看看自己的手，手上沾满鲜血。你发现这不是你的血。你什么也记不得了，更无法想象你为何要煽动这场暴力和破坏的嗜血狂欢。在警笛声逐渐接近的时候，你看见了人们惊恐的神情。\n你减少自己1D6点耐久值——这不会对你造成重伤。"],
            ["恐惧症"],
            ["躁狂症"]
        ]
        xsdl = [
            ["真有趣", "仿佛被开了一个大玩笑，你会狂笑不止。"],
            ["真失败", "一切都化作泡影，你会痛哭不止。"],
            ["真可怕", "没有一点点防备，你会尖叫不止。"],
            ["它进去了！", "有“东西”寄生了你，你必须把它从身体里弄出来（切掉有毛病的肢体、立即进行手术、酗酒、漂白，任何能用来清洁你身体内部的方法）"]
        ]
        jxcj = [
            ["目盲", "你的眼前突然一黑，什么也看不见了！"],
            ["耳聋", "你听不到声音了，你只能辨认出低语和呻吟。"],
            ["失声", "你张开嘴，却什么也说不出！"],
            ["触觉失灵", "你没有任何触觉，包括痛觉（你受到的伤害全部由KP秘密投掷）。"],
            ["手指失灵", "你手拿的东西掉到地上，你的手不受控制，不能再拿取任何东西。"],
            ["腿脚失灵", "你摔倒在地。你不能站立，只能用手支撑身体，在地上拖行（你的MOV下降到1）。"]
        ]
        kjz = [
            ["蜘蛛恐惧症", "蜘蛛网……！到处都是蜘蛛网！", "你会无端地对蜘蛛产生恐惧。这种八条腿噩梦的藏身之处会令你非常不安。仅仅看见蜘蛛网都会让你冷汗直流、心跳加速。如果有蜘蛛突然碰到了你或者离你过近，你可能惊慌大叫，呼吸困难，害怕蜘蛛会杀死你。\n极端的时候，甚至看到蜘蛛的图片都会吓到你。\n附近有蜘蛛或蜘蛛存在的迹象将导致你无法抗拒的应激反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。\n成功使用精神分析技能可以让你暂时缓解紧张，能够在蜘蛛（或蜘蛛存在的迹象）附近停留一段时间。"],
            ["书籍恐惧症", "把它从我眼前拿开！", "你害怕书籍。强迫你拿着或阅读书籍会令你发抖、出汗、大哭。\n你最害怕的可能是书籍本身（发脆的纸张、皮革封面）或者它们的内容。也可能是阅读本身、学习新事物、令人恐惧的知识，让你精神崩溃。\n你会避免阅读，图书馆变成了你的禁区。虽然你能够进入有书架的房间（你马上就会离开！），但你一想到别人要你拿起一本书甚至去阅读，就会心跳加速，内心充满恐惧。\n附近有书籍将导致你无法抗拒的应激反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。\n成功使用精神分析技能可以让你暂时缓解紧张，能浏览书籍、阅读其中的一篇短文，或者将这本书交给他人。"],
            ["幽闭恐惧症", "求你了，我不要进到那种可怕的地窖里……", "你害怕封闭空间。这可能是想象自己被关进狭小空间，逃生希望渺茫；也可能是想象自己有可能落入陷阱——也许你会窒息，或者被什么黑暗可怕的东西当作美餐？\n你会拒绝进入地窖、洞穴或电梯等狭小空间。如果你发现自己身处封闭空间，比如一间没有窗户的小屋或者上锁的车厢，你会开始恐慌、出汗，感觉有什么东西让你透不过气。严重的时候，你甚至会强迫性地脱衣服以求得一点虚假的自由感。\n身处封闭空间将导致你无法抗拒的应激反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。\n成功使用精神分析技能可以让你暂时缓解紧张，能穿过这一地区或者平静下来走出去。"],
            ["人群恐惧症", "他们全都在看着我……", "你害怕人群。你会躲避大群的人，不论这些人是在举办运动会、在热闹的大街穿行还是在教堂集会。你可能是害怕被困住，或者你觉得所有人都是你的敌人，等着你自投罗网——他们知晓你的秘密，有一点点机会就会群起而攻之。\n你仅仅想到自己会进入充满人的热闹场所，就会动弹不得。转过一个街角进入人群的话，你会出汗、颤抖，嘴唇发干。你身上的每一个细胞都在告诉你要逃离，如果你不逃的话，你会崩溃倒地，剧烈地抖动。\n身处人群中将导致你无法抗拒的应激反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。\n成功使用精神分析技能可以让你暂时缓解紧张，能快速穿越人群。"],
            ["窥镜恐惧症", "不要照镜子！你的灵魂会被偷走的！", "你异常害怕镜子。也许是银白的镜面里隐藏着残忍的恶魔，它知道你的秘密，唆使你去做坏事？也许是看到你在镜子里的影像会让你想起你做过的种种恐怖事件？又或者是镜子里潜藏着什么东西在等着你……\n镜子常常和厄运联系在一起——如果你接近镜子，你可以打破镜子并将所有厄运归到自己头上。如果你走过镜子附近，你会注意到有什么东西在看着你。\n你会避免携带镜子，还会尽最大努力不去看任何镜子。但如果你被强迫照了镜子，你会被纯粹的恐惧侵袭，心率增加，身体颤抖，直到你突然昏厥并倒地。\n附近有镜子将导致你无法抗拒的应激反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。\n成功使用精神分析技能可以让你暂时缓解紧张，能携带镜子或者快速向镜子里瞥一眼。"],
            ["噪音恐惧症", "天！你听见那个了吗？", "你害怕巨大的声响。警报声、火警笛声、爆炸声之类急遽的巨响会让你紧张失色。\n其他症状还包括：换气过度、肌肉痉挛、口干舌燥、头晕目眩、心悸震颤等。\n你会十分小心乐器，特别是鼓；也会躲避游行、嘉年华和焰火表演。你会尽量让收音机、音乐播放器和电视的音量调到最低。\n看到别人吹气球会让你十分恐惧，感觉自己失去控制，你无法集中精力到噪音源以外的任何东西上。\n身处噪音之中将导致你无法抗拒的应激反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。注意如果你身边有枪声，惩罚仍要生效。\n成功使用精神分析技能可以让你暂时缓解紧张，能平静下来克服严重不良反应。"],
            ["孤独恐惧症", "不要离开我！", "你极其害怕独处。如果你独处一地，周围又没有朋友，你会开始恐惧。你会因独处的想法而紧张，即使独处时间并不长。\n症状包括：失去斗志、极度自卑、恐慌等。你的心率会增加，吐字不清，情绪剧烈波动。只要落单，你就只能乞求陌生人的怜悯了。\n你可能会难以完成某些事，如穿越人群（你可能会落单）、进入电梯或者黑暗的地方、乘坐公共交通工具等。\n独处将导致你无法抗拒的恐惧反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。注意如果你身边有枪声，惩罚仍要生效。\n成功使用精神分析技能可以让你暂时缓解紧张，能平静下来克服严重不良反应。和朋友通电话也能让你缓解症状。"],
            ["牙齿恐惧症", "啊啊啊！牙！", "你害怕牙齿，尤其害怕那种磨得格格响、咬得喀喀响、嚼得嘎吱响的尖牙利齿。狗、猫或者更可怕的动物，舔着牙齿，盯着你看。你知道它们在想什么。它们想吃你！\n即使是人类，如果他们露出了或白或黄的牙齿，他们也可能是食人族——他们唯一的想法就是用你的肉大快朵颐，把你的骨头咬碎磨烂。\n你对陌生人十分紧张，对长着尖牙的动物十分恐惧。当诱捕动物、其他的打招呼露出牙齿、甚至面对怪物时，你会产生无法抗拒的应激反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。\n成功使用精神分析技能可以让你暂时缓解紧张，能平静下来克服严重不良反应。"],
            ["魔术棒恐惧症", "啊啊啊！他要把我们变成蛤蟆了！", "你害怕魔术。任何和魔术有关的东西，包括卡片戏法、舞台魔术到声称拥有真正魔力的远古典籍，都可能把你变成抖成一团的废人。\n魔术会改变物体，也能改变你。它是神秘学，是通向黑暗邪恶世界的大门。小心魔术师。你知道他们的真相和他们造成的危险。\n当你身处魔术表演、魔术道具和魔术师附近时，你会紧张、极度恐惧、汗流不止、恶心、口齿不清。如果你发现自己成为了神话魔法的目标，你的反应会极其严重，会暂时产生紧张症（理智检定成功可以回避此效果）。\n周围有魔术时，你会产生无法抗拒的应激反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。\n成功使用精神分析技能可以让你暂时缓解紧张，能平静下来克服严重不良反应。"],
            ["暗影恐惧症", "灯呢？光呢？！", "你大致上极其害怕黑暗或夜晚，症状顽固。\n黑暗隐藏了很多东西，它们意图伤害你。如果你走进黑暗，你会被它们带走。黑暗中发生着各种各样的恶行——谋杀、偷盗、甚至更糟。你会躲避一切黑暗的地点：空房间、黑暗的地窖、茂密的森林；夜晚出门会让你产生深深的恐惧。\n如果你身处黑暗当中，你会呼吸困难、虚汗直冒、浑身发抖、充满恐惧。如果在黑暗中停留时间过久，你会经历强烈的焦虑发作，无法清楚地说话，更可能暂时产生紧张症（理智检定成功可以回避此效果）。\n身处黑暗之中将导致你产生无法抗拒的应激反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。\n成功使用精神分析技能可以让你暂时缓解紧张，能短时间维持自己的精神不致崩溃。"],
            ["活埋恐惧症", "到处都是死人！", "你害怕被活埋，也害怕墓地。你可能是害怕自己被宣布死亡，醒来时已经被深埋地下，无从逃脱，只能慢慢窒息。也可能是害怕坟地的死人，生者不应惊扰死者。\n墓地是坏地方。死者可以感受到生者，对生命产生嫉妒。有时对生命的渴求过于强烈，会让它们化作捕食生者的僵尸。\n附近有任何能让你联想到死亡的物品（葬礼、太平间、棺材等）将导致你产生无法抗拒的应激反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。\n成功使用精神分析技能可以让你暂时缓解紧张，能短时间维持自己的精神不致崩溃。"],
            ["排外症", "他们想抓我！", "你害怕陌生人和外国人。任何你认为不同（异）或不熟悉（怪）的人都是潜在的威胁，会让你的心脏恐惧地加快速度。\n陌生人不可相信，他们的动机和目标完全是不可知的。怪人隐藏着不可告人的秘密，他们可能是杀人犯，也可能是想偷走你的个人信息，好收走你的身家性命。\n你在面对不同于你的人时，会经历极端的情绪波动，愤怒、挑衅、纯粹的恐怖都有可能。如果你身处异国他乡或者周围全是陌生人、异族人的时候，任何环境都会让你紧张或愤怒。\n附近有这些人将导致你产生无法抗拒的应激反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。\n成功使用精神分析技能可以让你暂时缓解紧张，能短时间维持自己的精神不致崩溃。"],
            ["恐高症", "别往下看！", "你害怕高处。让你身处高处会令你恐慌。通常的反应包括心悸、颤抖、焦虑等。\n当你身处高处时，你将激动过度以致无法自行安全降落，可能需要别人帮助。甚至仅仅对高处的预想，如想象自己将登上高楼，都会令你变成语无伦次的废人。\n身处高处将导致你无法抗拒的应激反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。\n成功使用精神分析技能可以让你暂时缓解紧张，正常应对眼下的情况。"],
            ["恐血症", "血！到处都是血！", "你害怕血。看到血会令你心跳加速、血压升高。你的嘴唇发干，头晕目眩。\n如果血很多（事故、搏斗或目睹手术等），你很可能恶心反胃甚至昏厥。你会对你或他人的小伤口过度反应，难以帮助别人而可能会逃跑。\n你会抗拒观察手术、进入灾难现场；如果可能看见血，你会拒绝进入医院。\n附近有血将导致你无法抗拒的应激反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。\n成功使用精神分析技能可以让你暂时缓解紧张，能正视血、采集带血的样本或者施行急救。"],
            ["恐雾症", "关上窗帘！雾里的东西会看见你的！", "你异常害怕雾气和潮气。雾气是世间最凶恶歹徒的最佳掩护（想想开膛手杰克），它掩盖了一切，哪怕有人离你不过几寸远，正打算攻击你，你却无法察觉他是谁。\n你恐怕会永远迷失在雾里，找不到回家的路；或者什么潮湿怪异的手会无端出现，偷走你的生命。\n呆在充满光线的室内比出门走进迷雾要好得多。如果强迫你走出去，你会变得焦虑、气短、恶心、流汗。如果独自或强迫呆在有雾的地方一很长一段时间，你很可能会颤抖、吐字不清，甚至可能昏厥。\n身处雾气或潮气当中将导致你无法抗拒的应激反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。\n成功使用精神分析技能可以让你暂时缓解紧张，能快速通过一团雾气。"],
            ["恐水症", "让我从这个水地狱解脱吧！", "你异常害怕水。不论是海洋、河流，甚至是一浴缸的水，只是想一想沉没在这种光滑、冒泡又不断流动的液体里，都会让你充满恐惧。\n你会抗拒游泳，如果被突然推进水里，你会经历强烈的身体反应——颤抖、战栗、乱扑腾。你越恐慌，越可能溺水，无法游到安全地带；必须有人帮助。\n在极端情况下，甚至喝水都成为了令你惊恐的行为，你会出汗、心跳增加。\n附近有水将导致你无法抗拒的应激反应，在恐惧状态下，除了逃跑和格斗（若战斗中）以外的所有技能检定都要受到一个惩罚骰。\n成功使用精神分析技能可以让你暂时缓解紧张，能快速通过一片水域、洗澡等等。"]
        ]
        zkz = [
            ["意志缺失狂", "做这个无济于事，而做那个还不如这个！", "你变得犹豫不决，无法制定决策，或者同意明确的行动计划。\n你的精神备受煎熬，害怕你会选择所有坏的选项——可能会对你和朋友造成可怕的后果。这种决策瘫痪①会造成你不论什么事情都会过度分析。\n你会经常变得易怒或走神，影响你正常进行社交的能力。更令人担忧的是，在战斗中你的犹豫不决会让局势变得更加致命。\n当你面临必须做出决断的情况时，你将无法抗拒躁狂反应，所有技能检定受到一个惩罚骰，直到情况解决或你远离刺激为止。KP也可能根据情形改变技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果。"],
            ["亲切狂", "嘿，我来帮你做这个吧。", "你的症状是病态的友好行为。这种躁狂症表现为对进行亲切行为的需要，对象可能是朋友、陌生人甚至是敌人。\n你会强迫性地进行利他行为，表面上显示为需求别人的接受和承认。你的内心感到因为对别人做得不够而自责，或者在别人得到关注、而你的努力无人过问时产生嫉妒。\n这种利他行为会导致不健康的极端行为。对别人做太多会让你筋疲力尽，因为你为他人想太多却想不到自己。\n如果你不能为其他人做出善意行为，你的所有技能检定会受到一个惩罚骰，直到躁狂缓解或你远离刺激为止（战斗中不生效）。KP也可能根据情形或角色的状况改变某些技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果。"],
            ["喜尖狂", "你要给我打针吗？太棒了！", "你痴迷于尖锐锋利的物体。既可能是对尖锐物体的病态喜爱，也可能是恐惧。\n尖锐物体包括小刀、叉子、针头、钉子、别针、图钉等等。\n你可能会强迫性地收集尖锐物体，为了充实自己的收藏甚至会盗窃。或者你在看见尖锐物体时，可能会产生被它刺穿的病态欲望。\n如果你恐惧尖锐物体，你会千方百计远离它们。你吃饭的时候会用钝头筷子，而不用刀叉。甚至被人用手指戳都会引发你的过度反应。当附近有尖锐物体时，你将无法抗拒强迫反应，所有技能检定受到一个惩罚骰，直到躁狂缓解或你远离刺激为止（战斗中不生效）。KP 也可能根据情形或角色的状况改变某些技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果。"],
            ["欣喜狂", "我们都要被吃掉了吗？唉呀，别那么难过！凡事要往好处想！", "你的症状是非理性的愉悦。不管你的身边发生了什么，你都只会感到高兴、乐观、兴高采烈。\n即使是面对必死无疑、极端骇人的情况，或者从外界虚空出现无法想象的怪物，你也会欺骗自己，只能看见好的一面。这种欣喜的幻觉会让你对危险视若无物，草率鲁莽，让你身边的人胆战心惊。\n如果有任何人或事阻止你的愉悦行为，你会极度焦虑，所有技能检定受到一个惩罚骰，直到你远离刺激为止（战斗中不生效）。你若想抵抗幻觉，看到真实的情况，必须通过困难难度的现实检定（困难理智检定）。KP也可能根据情形或角色的状况改变某些技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果。"],
            ["计数狂", "数字！到处都是数字！", "你对数字有痴迷般的执着。你紧张时会强迫性地计数。这可能是特定的动作（掰手指），或者周围的事物（飞机、楼梯、键盘上的按键）。\n你可能会在阅读时强迫性地先清点出字数再开始理解文意。你也可能会记录自己到目的地到底走了多少步。\n你经常会觉得为了防止臆想的灾难，必须按一定的次数进行特定的步骤，比如在使用武器之前必须反复清洁它三次等等。\n如果有任何人或事阻止你的计数行为，你会极度焦虑，所有技能检定受到一个惩罚骰，直到躁狂缓解或你远离刺激为止（战斗中不生效 ）。 KP也可能根据情形或角色的状况改变某些技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果。"],
            ["藏书狂", "小书书真可爱。我全都要！", "你对书籍有着病态的痴迷：表现为强迫行为，你会尽一切可能收集书籍。\n你可能只痴迷于一本书，也可能会收集任何书。有种冲动让你对它们产生强烈的欲望。你收集书籍的行为包括超出财力的购置行为和盗窃等。\n你在紧张时想要被你的书包围，狂乱地阅读或者强迫性地清点你藏书的数量。你的躁狂会影响你同世界和他人的关系。\n如果有任何人或事阻止你收集书籍，或者取走了你的藏书，你会极度焦虑，所有技能检定受到一个惩罚骰，直到躁狂缓解为止（战斗中不生效）。KP也可能根据情形或角色的状况改变某些技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果。"],
            ["色彩狂", "黄色！到处都是黄色！", "你对某一种颜色产生病态痴迷。你可以决定自己对它是病态喜爱还是恐惧。\n人们知道颜色会影响心理状态，比如绿色会使人平静，而红色会让人兴奋。这种症状会让你产生异常的想法和冲动，根据你恐惧或偏爱颜色种类的不同让你激动或平静。\n你会和身穿这种颜色的人时产生交流困难，也会躲避有（或没有）这种颜色的地点。当你遇到自己恐惧的颜色、或附近没有你偏爱的颜色时，你会极度焦虑，所有技能检定受到一个惩罚骰，直到你远离刺激或你（用比如全身涂满颜料等方式）满足了自己为止。KP 也可能根据情形或角色的状况改变某些技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果。"],
            ["学识狂", "我必须学到一切知识！", "你会产生异常的强迫学习行为。这可能有多种表现形式：废寝忘食地阅读书籍、检查你笔记本里的统计数据、对博学的人无休止地提问等等。\n你如果不能学习就会十分悔恨或愤怒。你在找不到重要信息时会激越或抑郁。你会用出格的方式获取知识；偷盗、涉险，只有这样才能满足你的欲望。\n你在紧张时会沉迷于某些知识；你会不停重复某些词语，或者凭记忆写下潦草的笔记才能行动。\n如果有任何人或事阻止你依躁狂症行事，你会极度焦虑，所有技能检定受到一个惩罚骰，直到躁狂缓解或你远离刺激为止（战斗中不生效 ）。 KP也可能根据情形或角色的状况改变某些技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果。"],
            ["偷窃狂", "我非得到它不可。", "你的症状是荒谬的强迫性盗窃行为。这种强迫症意味着你无法克制自己想要东西的冲动，偷盗东西也不为了个人使用或者获利。\n你的强迫行为可能体现在某一类物品上，也可能体现在任何东西上；包括曲别针、笔、花、勺、铅笔甚至烟灰缸。\n你在偷盗之前很可能会产生紧张症状，如不安和焦虑等，偷窃之后压力就能得到释放。但是，接踵而来的是负罪感，你可能会向他人坦白自己的罪行。\n如果有任何人或事阻止你偷盗，你会极度焦虑，所有技能检定受到一个惩罚骰，直到躁狂缓解为止（战斗中不生效）。KP也可能根据情形或角色的状况改变某些技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果。"],
            ["噪音狂", "乓！", "你的症状是无法控制的制造噪音的行为，特别是在不合适的场合，如在大家都保持安静的剧院里，或者潜伏在邪教巢穴里的时候。\n你很可能会偏爱一两种特殊的噪音，也可能会在紧张的时候发出种种奇怪的声响。见到气球时，你会自然产生弄破它的想法。\n你在噪音环境下，比如用最大音量播放音乐的地方，症状可能会减轻很多。这可能来自对安静的恐惧，使你只能在吵闹的地方才能保持正常思考。\n如果有任何人或事阻止你制造噪音，你会极度焦虑，所有技能检定受到一个惩罚骰，直到躁狂缓解为止（战斗中不生效）。KP也可能根据情形或角色的状况改变某些技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果。"],
            ["说谎狂", "不是我。", "你会强迫性地说谎，或是说话时异常夸张。即便你的话会决定自己的生死，你也无法讲出真话。\n谎言如同铠甲，保护你不受伤害。夸大隐藏了真实的情况，助长了你的自私倾向。你用精妙的谎言把事情讲得天花乱坠，好让人觉得自己非常重要。\n随着你症状的加重，你的谎言越来越多。你必须记得自己说过的一切谎言，将它抄录下来帮助记忆。你越紧张，谎言和夸大就越荒诞无稽。如果你的谎言被人怀疑对质，你会极度焦虑，所有技能检定受到一个惩罚骰，直到你逃脱或者编造出让人信服的新谎言为止（战斗中不生效）。KP也可能根据情形或角色的状况改变某些技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果，可能让你暂时承认事情的真相。"],
            ["疑病狂", "不净！不净！", "你产生了严重的幻觉，认为自己患上了臆想的疾病，或者健康状况极差。\n你可能在头脑里放大自己已有的症状，也可以臆想出一种疾病。你会证明自己的病情：一瘸一拐地走路、全身缠满绷带等等。你可能相信自己的腿已经瘸了，要让别人用轮椅推着你走；你也可能对自己进行小手术。\n你会纠缠医生治疗自己；如果医生不听你的话，你甚至会强迫性地盗取药物。\n如果别人怀疑你的身体状况，你会十分激动且不友善，所有技能检定受到一个惩罚骰，直到离开此地为止（战斗中不生效）。KP也可能根据情形或角色的状况改变某些技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果。"],
            ["称名狂", "F'tagn! F'tagn! F'tagn!", "你无法抗拒自己反复说出某个词的欲望。这个词可能是让你精神崩溃的事件当中最有代表性的一个词。另外，这个词可能没有什么意义，甚至是胡言乱语。你也可能会强迫性地重复别人最近对你说过的话。\n你只有重复说这些词才能感到安心，也可能会强迫性地重复写这个词。\n对不理解你、或无意中说了你说的词的人，你会感到非常沮丧或恼怒。\n如果不能说出这个词，你会极度焦虑，所有技能检定受到一个惩罚骰，直到躁狂缓解为止（战斗中不生效）。KP也可能根据情形或角色的状况改变某些技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果。"],
            ["纵火狂", "烧光它！", "你对火焰特别着迷，还会强迫性地点火。火焰会净化一切，而你是它的工具，净化这个黑暗的世界。你的能力是用救赎和赦免的赤红火舌，改变这个世界。你的着迷可能来源于地狱之火的信仰——火焰会将原罪焚烧成灰。或者你可能认为混沌才是万物的主宰，你放出火焰会令混沌得以自由。\n只要附近有火焰你就会被吸引，你盯着它燃烧的焰心，忘记时间的流逝。如果可能的话，你会随身携带生火工具。\n你紧张的时候会想点燃物品，如果做不到，你会极度焦虑，所有技能检定受到一个惩罚骰，直到强迫行为得到满足或你离开为止（战斗中不生效）。你可以通过一次困难难度的理智检定抑制自己的冲动。KP也可能根据情形或角色的状况改变某些技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果。"],
            ["提问狂", "这是什么？", "你有强迫自己提问的冲动。不论何时何地，你都无法控制自己问问题。\n大多数问题都是直接对别人发问；不过有时你也会自问自答。你见到权威会发问，见到店主会发问，见到教团首脑也会发问，不一而足。\n你会对重要的事情特别关心，更可能对毫无疑问的显明事实一遍遍地发问。如果没有人回答出你想要的答案，你会大哭或发怒。\n如果有人或事阻止你提问，你会极度焦虑，所有技能检定受到一个惩罚骰，直到你满足欲望为止（战斗中不生效）。KP也可能根据情形或角色的状况改变某些技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果。"],
            ["搔痒狂", "该死的疹子，出去！出去！", "你的症状是病态的搔痒行为。你感觉必须反复抓挠自己的皮肤，甚至会因此受到伤害。你最可能感觉你的皮肤上有什么东西或者得了什么奇怪的病。\n在紧张时或你独处思考时，情绪会突然爆发。虽然全身上下的皮肤都可能成为你抓挠的目标，但最常见的目标是面部（根据KP裁定，长期抓搔会降低你角色的APP）。\n如果有人或事阻止你搔痒，你会极度焦虑，所有技能检定受到一个惩罚骰，直到你满足欲望为止（战斗中不生效）。KP也可能根据情形或角色的状况改变某些技能检定的难度等级。\n成功使用精神分析技能可以让你暂时克服躁狂和它的严重不良效果。"],
        ]
        r_time = c
        time_text = "[1D10]=【%s】"%r_time
        name = user["name"]
        if now:
            result = self.roll_dice("1d%s" % (len(r)))[-1] - 1
            if r[result][0] == "恐惧症":
                kjzinfo = kjz[self.roll_dice("1d%s"%(len(kjz)))[-1] - 1]
                insert = "【恐惧症: %s】\n%s"%(kjzinfo[0], kjzinfo[2])
                user["story"]["精神状况"] = user["story"]["精神状况"] + "\n" + insert
                self._update_card(user)
                res = "[%s]因疯狂患上了【恐惧症】\n" \
                      "在%s轮的时间内，即便恐惧源头可能并不在这里，但你仍会想象那些东西就在那里。\n" \
                      "[%s]的恐惧症为【%s】\n" \
                      "“%s”\n%s"%(name, time_text, name, kjzinfo[0], kjzinfo[1], kjzinfo[2])
                return res
            elif r[result][0] == "躁狂症":
                khzinfo = zkz[self.roll_dice("1d%s"%(len(zkz)))[-1] - 1]
                insert = "【躁狂症: %s】\n%s"%(khzinfo[0], khzinfo[2])
                user["story"]["精神状况"] = user["story"]["精神状况"] + "\n" + insert
                self._update_card(user)
                res = "[%s]因疯狂患上了【躁狂症】\n" \
                      "在%s轮的时间内，你将沉浸在你的躁狂症之中。\n" \
                      "[%s]的躁狂症为【%s】\n" \
                      "“%s”\n%s"%(name, time_text, name, khzinfo[0], khzinfo[1], khzinfo[2])
                return res
            elif r[result][0] == "歇斯底里":
                xsdlinfo = xsdl[self.roll_dice("1d%s"%(len(xsdl)))[-1] - 1]
                res = "[%s]因疯狂陷入了暂时的\n【歇斯底里】\n持续%s轮\n" \
                      "”%s“\n%s\n" \
                      "[%s]的歇斯底里为【%s】\n" \
                      "%s"%(name, time_text, r[result][1], r[result][2], name, xsdlinfo[0], xsdlinfo[1])
                return res
            elif r[result][0] == "假性残疾":
                jxcjinfo = jxcj[self.roll_dice("1d%s"%(len(jxcj)))[-1] - 1]
                res = "[%s]因疯狂陷入了暂时的\n【假性残疾】\n持续%s轮\n" \
                      "”%s“\n%s\n" \
                      "[%s]的假性残疾症状为【%s】\n" \
                      "%s"%(name, time_text, r[result][1], r[result][2], name, jxcjinfo[0], jxcjinfo[1])
                return res
            else:
                res = "[%s]因疯狂陷入了暂时的\n【%s】\n持续%s轮\n" \
                      "”%s“\n%s%s"%(name, r[result][0], time_text, r[result][1], r[result][2], "\n(%s)"%r[result][3] if len(r[result])>3 and r[result][3] else "")
                return res
        else:
            result = self.roll_dice("1d%s" % (len(rz)-1))[-1] - 1
            if rz[result][0] == "恐惧症":
                kjzinfo = kjz[self.roll_dice("1d%s"%(len(kjz)))[-1] - 1]
                insert = "【恐惧症: %s】"%(kjzinfo[0])
                user["story"]["精神状况"] = user["story"]["精神状况"] + "\n" + insert
                res = "[%s]陷入疯狂，并患上了【恐惧症】\n" \
                      "[%s]的恐惧症为【%s】\n" \
                      "“%s”\n%s"%(name, name, kjzinfo[0], kjzinfo[1], kjzinfo[2])
                return res
            elif rz[result][0] == "躁狂症":
                khzinfo = zkz[self.roll_dice("1d%s"%(len(zkz)))[-1] - 1]
                insert = "【躁狂症: %s】"%(khzinfo[0])
                user["story"]["精神状况"] = user["story"]["精神状况"] + "\n" + insert
                res = "[%s]陷入疯狂，并患上了【躁狂症】\n" \
                      "[%s]的躁狂症为【%s】\n" \
                      "“%s”\n%s"%(name, name, khzinfo[0], khzinfo[1], khzinfo[2])
                return res
            else:
                res = "[%s]陷入了疯狂，症状为【%s】\n" \
                      "”%s“\n%s%s"%(name, rz[result][0], rz[result][1], rz[result][2], "\n(%s)"%rz[result][3] if len(rz[result])>3 and rz[result][3] else "")
                return res

    def _roll_weapon(self, exp, user):
        pt = re.compile(r'(?P<times>\d+#)?((?P<other>.+))?')
        mt = pt.match(exp)
        other = mt.group("other")
        times = mt.group("times")
        times = int(times[:-1]) if times else 1
        weapon = False
        if not other:
            return False
        for wea in user["weapon"]:
            if wea["名称"].strip() == other.strip():
                weapon = wea
                break
        if weapon:
            expre = "%s#"%times + weapon["伤害"]
            expre = expre.replace("db", user["attex"]["DB"]).replace("DB", user["attex"]["DB"]).replace("++", "+").replace("+-", "-")
            result = self.evaluate_expression(expre)
            if result:
                return self._clear_dice(user["name"], result, weapon["名称"])
            else:
                return "武器[%s]的表达式有误" % weapon["名称"]
        else:
            return False

    def _clear_cmd(self, cmd):
        cmd = cmd.strip()
        if cmd[0] in ["。", "`", "·", ",", "-"]:
            cmd = "." + cmd[1:] if len(cmd)>1 else ""
        return cmd

    def _send_hidden(self, group, wxid, result):
        groupname = self._get_name(group)
        selftext = "您在群[%s]中暗骰的结果为:%s"%(groupname, result)
        self.wcf.send_text(f"{selftext}", wxid)

    def _roll_nandu(self, result, value, config={}):
        bigsucc = int(config["succnum"])if "succnum" in config.keys() and config["succnum"]>0  else 1
        bigfail = int(config["failnum"])if "failnum" in config.keys() else -1
        if result <= bigsucc:
            nandu = "大成功！"
        elif bigfail<=0:
            if result == 100:
                nandu = "大失败!"
            elif result <= value // 5:
                nandu = "极难成功"
            elif result <= value // 2:
                nandu = "困难成功"
            elif result <= value:
                nandu = "成功"
            elif result > value and (value < 50 and result > 95):
                nandu = "大失败!"
            elif result > value and (value >= 50 and result == 100):
                nandu = "大失败!"
            else:
                nandu = "失败"
        else:
            if result >= bigfail:
                nandu = "大失败!"
            elif result <= value // 5:
                nandu = "极难成功"
            elif result <= value // 2:
                nandu = "困难成功"
            elif result <= value:
                nandu = "成功"
            else:
                nandu = "失败"

        return nandu

    def _cmd_error(self, cmd, wxid):
        name = self._get_name(wxid)
        return "[%s]的指令[%s]无法识别"%(name, cmd)

    def _nouser_error(self, cmd, wxid):
        name = self._get_name(wxid)
        return "[%s]没有角色卡"%(name)

    def _hidden_result(self, cmd, wxid):
        name = self._get_name(wxid)
        return "[%s]偷偷地投骰[%s]，结果已私发"%(name, cmd)

    def _clear_check(self, name, resultlist, config, forwhat, value, times=1):
        if times == 1:
            result = resultlist[-1]
            nandu = self._roll_nandu(result, value, config)
            exp = "%s%s%s" % (resultlist[0], " b%s" % resultlist[1] if len(resultlist[1]) > 0 else "",
                              " p%s" % resultlist[2] if len(resultlist[2]) > 0 else "")
            r = "[%s]进行%s检定，骰出了%s=【%s/%s】【%s】" % (
            name, "%s" % forwhat if forwhat else "", exp, result, value, nandu)
            return r
        else:
            resultlist1 = resultlist
            exp = []
            for resultlist in resultlist1:
                result = resultlist[-1]
                nandu = self._roll_nandu(result, value, config)
                exp.append(
                    "%s%s%s=【%s/%s】【%s】" % (resultlist[0], " b%s" % resultlist[1] if len(resultlist[1]) > 0 else "",
                                            " p%s" % resultlist[2] if len(resultlist[2]) > 0 else "", result, value,
                                            nandu))
            r = "[%s]进行了[%s]次%s检定，骰出了:\n %s" % (
                name, times, "%s" % forwhat if forwhat else "", "\n".join(exp))
            return r

    def _clear_dice(self, name, resultlist, forwhat):
        times = resultlist[-2]
        if times==1:
            result = resultlist[0]
            resultlist = resultlist[2]
            exp = ""
            for rl in resultlist:
                exp += "%s%s%s" % (rl[0], " b%s" % rl[1] if len(rl[1]) > 0 else "",
                              " p%s" % rl[2] if len(rl[2]) > 0 else "")
            r = "[%s]骰%s，骰出了%s=【%s】" % (name, "%s" % forwhat, exp, result)
            return r
        else:
            result = resultlist[0]
            resultlist = resultlist[2]
            exp = ""
            for rl in resultlist:
                exp += "%s%s%s" % (rl[0], " b%s" % rl[1] if len(rl[1]) > 0 else "",
                                       " p%s" % rl[2] if len(rl[2]) > 0 else "")
            r = "[%s]骰%s，骰出了%s=>【%s】" % (name, "%s" % forwhat, exp, ",".join([str(i) for i in result]))
            return r

    def _sign_skill_ensure(self, user, skillindex):
        user["skill"][skillindex]["ensure"] = True
        self._update_card(user)

    def _update_card(self, data):
        res = requests.post(self.api+"/api/coc_self_update", data=json.dumps({"card_id": data["_id"], "data": data}))
        res = res.json()
        return res["ok"]

    def _get_user_data(self, group, wxid):
        res = requests.post(self.api+"/api/coc_group_get_one", data=json.dumps({"group": group, "user": wxid}))
        res = res.json()
        return res["data"]

    def _get_users_data(self, group):
        res = requests.post(self.api+"/api/coc_group_get_all", data=json.dumps({"group": group}))
        res = res.json()
        return res["data"]

    def _bot_on_or_off(self, group, status):
        # 群组机器人状态设置
        group_status = "status" in self.data[group].keys() and self.data[group]["status"]
        if status:
            if group_status:
                return "骰娘已在运行中！"
            else:
                result = self._post_group_status(group, True, self.data[group]["Gaming"])
                self.data[group]["status"] = True
                if result:
                    return "骰娘已启动!"
                else:
                    return "启动失败!"
        else:
            if group_status:
                result = self._post_group_status(group, False, self.data[group]["Gaming"])
                self.data[group] = self._get_group_status(group)
                self.data[group]["status"] = False
                if result:
                    return "骰娘已关闭！"
                else:
                    return "关闭失败！"
            else:
                return "骰娘未启动！"

    def _game_start_or_end(self, group, game):
        group_status = self.data[group]["status"]
        if self._post_group_status(group, group_status, game):
            self.data[group]["Gaming"] = game
            if game == "start":
                return "游戏已启动，开始记录log"
            if game == "end":
                return "游戏结束，可进行幕间成长，可获取游戏日志"
            if game == "pause":
                return "游戏暂停"
        return "设置失败"

    def _init_group(self, group):
        # 初始化群状态
        if group not in self.data.keys():
            result = self._get_group_status(group)
            if result:
                self.data[group] = result
            else:
                self._update_group_config(group, {"point":500, "dicetime": 5})
                self._init_group(group)
        self.data[group]["users"] = list(self.wcf.get_chatroom_members(group))
        return True

    def _get_group_status(self, group):
        # 获取群组状态
        res = requests.get(self.api+"/api/coc_group_status?group=%s"%group)
        res = res.json()
        return res["data"]

    def _post_group_status(self, group, status, Gaming):
        # 修改群组状态
        res = requests.post(self.api+"/api/coc_group_status", data=json.dumps({"group": group, "status": status, "Gaming":Gaming}))
        res = res.json()
        return res["ok"]

    def _update_group_config(self, group, config):
        # 更新设置
        res = requests.post(self.api + "/api/coc_group_config", data=json.dumps({"group": group, "config": config}))
        return res

    def _get_id_from_wxid(self, wxid):
        # 更新设置
        res = requests.post(self.api + "/api/coc_self_get_id", data=json.dumps({"user": wxid}))
        return res.json()["data"]



if __name__ == "__main__":
    from configuration import Config
    config = Config()
    a = Network(config.Myself, None)
    result = a.get_group_answer(".rc 50", "aaa", "1234")
    print(result)