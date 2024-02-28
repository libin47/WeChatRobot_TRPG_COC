# -*- coding: utf-8 -*-

import os
import re
import random
import pickle as pk
import sys
from config_user import skill,story,work
import datetime
# TODO:
# 角色数据存储方式
# 数据导入和输出
# 基本功能
# 检定
# 日志存储和导出

def roll_dice(expression):
    # 匹配掷骰表达式的正则表达式
    pattern = re.compile(r'(?P<count>\d+)[dD](?P<sides>\d+)(b(?P<bonus>\d+))?(p(?P<penalty>\d+))?')
    match = pattern.match(expression)

    if not match:
        raise ValueError("Invalid dice rolling expression: {}".format(expression))

    # 提取掷骰相关参数
    count = int(match.group('count'))
    sides = int(match.group('sides'))
    bonus = int(match.group('bonus')) if match.group('bonus') else 0
    penalty = int(match.group('penalty')) if match.group('penalty') else 0

    # 投掷骰子
    result = [random.randint(1, sides) for _ in range(count)]
    results = [result]
    # 计算奖励骰和惩罚骰
    bonus = bonus - penalty
    if bonus > 0:
        rbs = [random.randint(1, sides) for _ in range(bonus)]
        results.append(rbs)
        results.append([])
        results.append(min(sum(result), min(rbs)))
    elif bonus < 0:
        rbs = [random.randint(1, sides) for _ in range(-bonus)]
        results.append([])
        results.append(rbs)
        results.append(max(sum(result), max(rbs)))
    else:
        results.append([])
        results.append([])
        results.append(sum(result))

    return results


def evaluate_expression(expression):
    # 替换表达式中的掷骰子部分为其结果
    roll_result = []
    def repl(match):
        print(match.group(0))
        r = roll_dice(match.group(0))
        roll_result.append(r[:3])
        return str(int(r[3]))

    pattern = re.compile(r'(?P<times>\d+#)')
    match = pattern.match(expression)
    expression = re.sub(r'\d+#', '', expression)

    if not match:
        times = 1
    else:
        times = int(match.group('times')[:-1])
    # 使用正则表达式匹配掷骰子表达式，替换后计算表达式的值
    print(expression)
    if times == 1:
        return eval(re.sub(r'\d+[dD]\d+(b\d+)?(p\d+)?', repl, expression)), times, roll_result
    else:
        return [eval(re.sub(r'\d+[dD]\d+(b\d+)?(p\d+)?', repl, expression)) for _ in range(times)], times, roll_result


def extract_non_chinese_prefix(input_string):
    # 提取非汉字部分作为表达式
    pattern = re.compile(r'([0-9a-zA-Z\.\+\-\*\/#]+)')
    match = pattern.match(input_string)
    if match:
        return match.group(1)
    return ""


class Myself(object):
    def __init__(self, config, wcf) -> None:
        # root = os.path.dirname(os.path.abspath(__file__))
        try:
            os.mkdir(config['file_path'])
        except:
            pass
        self.config = config
        self.data = pk.load(open(config['file_path'] + self.config['file_name'], 'rb')) if os.path.isfile(config['file_path'] + self.config['file_name']) else {}
        self.wcf = wcf


    @staticmethod
    def value_check(conf: dict) -> bool:
        if conf:
            if conf.get("file_path"):
                return True
        return False

    def update_data(self):
        pk.dump(self.data, open(self.config['file_path'] + self.config['file_name'], 'wb'))

    def get_name(self, wxid):
        # 获取昵称
        name = self.wcf.get_info_by_wxid(wxid)
        return name['name']

    def save_log(self, wxid, msg_origin, msg, name="pc"):
        if name == "roll":
            user_name = "骰娘"
        else:
            user_name = self.data[wxid][msg_origin.sender]['name'] if msg_origin.sender in self.data[wxid].keys() else self.get_name(msg_origin.sender)
        with open(self.config['file_path'] + '%s.txt'%wxid, 'a', encoding='utf8') as f:
            f.write('【%s】%s\n%s\n'%(user_name, datetime.datetime.now().strftime("%Y年%m月%d日%H:%M:%S"), msg))

    def get_answer(self, question: str, wxid: str, msg_origin=None) -> str:
        # 记录log
        savelog = msg_origin.from_group() and wxid in self.data.keys() and \
                self.data[wxid]['status'] and self.data[wxid]['Gaming']=='start'
        if savelog:
            self.save_log(wxid, msg_origin, question)
        result = self.get_answer_main(question, wxid, msg_origin)
        if savelog and result:
            self.save_log(wxid, None, result, 'roll')
        return result

    def get_answer_main(self, question: str, wxid: str, msg_origin=None) -> str:
        # 再次检查输入格式
        if question[0] != '.':
            return ''
        if msg_origin.from_self():
            return ''
        # 群里机器人启动
        if question == '.boton' and msg_origin.from_group():
            return self.bot_start(wxid)

        # 群里机器人关闭
        if question == '.botoff' and msg_origin.from_group():
            return self.bot_end(wxid)
        # 只能群里用的
        if msg_origin.from_group() and self.data[wxid]['status']:
            if question == '.start':
                return self.game_start(wxid)
            if question == '.pause' or question == '.save':
                return self.game_pause(wxid)
            if question == '.end':
                return self.game_end(wxid)
            if question == '.log':
                return self.send_log(wxid)
            if question == '.en':
                return self.ensure_skill(wxid, msg_origin)
            if question[:6] == '.pcnew':
                return self.new_pc(question[6:], wxid, msg_origin)
            if question[:4] == '.del':
                return self.delete_item(question[4:], wxid, msg_origin)
            if question[:3] == '.st':
                return self.set_attribute(question[3:], wxid, msg_origin)
            if question[:5] == '.find':
                return self.find(question[5:], wxid, msg_origin)
            if question[:3] == '.ra':
                return self.check_attribute(question[3:], wxid, msg_origin)
            if question[:3] == '.rc':
                return self.check_attribute_with_value(question[3:], wxid, msg_origin)
            if question[:3] == '.sc':
                return self.sanity_check(question[3:], wxid, msg_origin)
            if question == '.hpc':
                return self.help_pc()
        # 群里或私聊
        if (msg_origin.from_group() and self.data[wxid]['status']) or (not msg_origin.from_group()):
            if question == '.help' or question=='.h':
                return self.help()
            if question == '.jrrp':
                return self.jrrp(msg_origin)
            if question[:4] == '.coc':
                return self.coc(question, msg_origin)
            if len(question)>3 and question[:2]=='.r':
                return self.get_roll(question[2:], wxid, msg_origin)

        # self.get_name(wxid)
        # rsp = "%s 无法识别"%question
        return ""

    def help(self):
        text = "【.boton】启动骰子机器人\n" \
               "【.botoff】关闭骰子机器人\n" \
               "【.jrrp】看看今日人品\n" \
               "【.r掷骰表达式】b接奖励骰个数，p接惩罚骰个数，可接四则运算，例如.r1d3+10, .r1d100b2, .r1d100p2 \n" \
               "【.coc[n]】生成n组随机属性值，数字n可以省略\n" \
               "【.pcnew 姓名】新建角色卡\n" \
               "【.st 属性表达式】\n设置角色属性，多个之间用英文逗号分开，例如\n[力量:nn,敏捷:nn,说服:nn]\n" \
               "[.st 特质:高冷][.st 职业:医生]\n" \
               "[.st &沙鹰:1d10+2]之后可以直接[.r沙鹰]进行检定\n" \
               "[.st hp-3]\n" \
               "【.ra 属性或技能】当前角色进行属性或技能检定\n" \
               "【.rc 属性或技能/N】进行属性技能检定，指定通过值\n" \
               "【.sc n/1dn】进行san check,根据成功与否自动扣除对应的值\n" \
               "【.find[表达式]】查看当前角色的指定信息，不填时查看全部\n" \
               "【.del 物品/武器】删除随身物品或武器\n" \
               "【.start】游戏开始，记录log\n" \
               "【.pause】游戏暂停\n" \
               "【.end】游戏结束，可以进行幕间\n" \
               "【.log】获取游戏日志\n" \
               "【.en】成长检定\n" \
               "【.hpc】车卡教程"
        return text

    def help_pc(self):
        text = "1、创建角色卡[.pcnew 名字]\n" \
               "2、使用[.coc]随机属性或与kp确认后自行填写\n" \
               "3、将.coc生成的属性录入,[.st 力量:11,敏捷:……]\n" \
               "4、选定职业并确定加点后，使用[.st 职业:..,会计:..,...]录入所有技能\n" \
               "5、根据需要录入随身物品、武器、背景等，使用[.st &小刀:1d3],[.st 随身物品:...],[.st 形象:...]\n" \
               "6、愉快游戏\n" \
               "7、在游戏结束后，使用[.en]进行技能的成长，SAN值恢复请与KP确认后使用[.st san+n]"
        return text

    # 群里启动机器人
    def bot_start(self, wxid):
        if wxid not in self.data.keys():
            self.data[wxid] = {}
        self.data[wxid]['status'] = True
        self.data[wxid]['Gaming'] = "pause"
        self.update_data()
        return "骰娘已启动！"

    def bot_end(self, wxid):
        self.data[wxid]['status'] = False
        self.data[wxid]['Gaming'] = "pause"
        self.update_data()
        return "骰娘已关闭！"

    def game_start(self, wxid):
        # 游戏开始，记录log
        self.data[wxid]['Gaming'] = "start"
        self.update_data()
        return '游戏开始，开始记录log'

    def game_pause(self, wxid):
        # 游戏暂停，保存log
        self.data[wxid]['Gaming'] = "pause"
        self.update_data()
        return '游戏暂停，停止记录log'

    def game_end(self, wxid):
        # 游戏结束，保存log，可以进行幕间成长
        self.data[wxid]['Gaming'] = "end"
        self.update_data()
        return '游戏结束，停止记录log，可以进行幕间成长'

    def send_log(self, wxid):
        dirname, filename = os.path.split(os.path.abspath(sys.argv[0]))
        self.wcf.send_file(dirname+'/' + self.config['file_path'] + '%s.txt'%wxid, wxid)
        return ''

    def jrrp(self, msg_origin):
        name = self.get_name(msg_origin.sender)
        r = roll_dice('1d100')
        return "【%s】今日人品值为：%s"%(name, r[-1])

    def coc(self, question, msg_origin):
        code = ['3D6*5', '3D6*5', '2D6*5+30', '3D6*5', '3D6*5', '2D6*5+30', '3D6*5', '2D6*5+30', '3D6*5']
        Aname = ['力量', '体质', '体型', '敏捷', '外貌', '智力', '意志', '教育', '幸运']
        question = question.strip()
        if len(question)>4:
            number = int(question[4:])
            x = ""
            for _ in range(number):
                rollresult = []
                for i in range(len(Aname)):
                    rollre = evaluate_expression(code[i])[0]
                    rollresult.append(rollre)
                    x += Aname[i] + ":" + str(rollre) + ","
                x = x[:-1] + "【总%s，不含运%s】\n"%(sum(rollresult), sum(rollresult[:-1]))
        else:
            x = ""
            rollresult = []
            for i in range(len(Aname)):
                rollre = evaluate_expression(code[i])[0]
                rollresult.append(rollre)
                x += Aname[i] + ":" + str(rollre) + ","
            x = x[:-1] + "【总%s，不含运%s】\n"%(sum(rollresult), sum(rollresult[:-1]))
        name = self.get_name(msg_origin.sender)
        return "%s骰出：\n%s"%(name, x)

    def new_pc(self, msg, wxid, msg_origin):
        name = msg.strip()
        self.data[wxid][msg_origin.sender] = {"name": name, "work":"",
                                              "attribute": {}, "skill": {},
                                              "learn_skill": [],
                                              "item": [], "story": {}, "weapon": {}}
        self.update_data()
        return "【%s】已创建角色卡【%s】"%(self.get_name(msg_origin.sender), name)

    def delete_item(self, msg, wxid, msg_origin):
        items = msg.strip()
        item_list = items.split(",")
        for item in item_list:
            if item in self.data[wxid][msg_origin.sender]['item']:
                self.data[wxid][msg_origin.sender]['item'].remove(item)
            if item in self.data[wxid][msg_origin.sender]['weapon'].keys():
                del(self.data[wxid][msg_origin.sender]['weapon'][item])
        self.update_data()
        return "已成功移除%s的%s"%(self.get_name(msg_origin.sender), item_list)

    def set_attribute(self, msg, wxid, msg_origin):
        if msg_origin.sender not in self.data[wxid].keys():
            return "%s角色卡不存在，请先用.pcnew [角色姓名]创建角色卡"%(self.get_name(msg_origin.sender))
        atlist = msg.split(',')
        userdata = self.data[wxid][msg_origin.sender]

        update_keys = []
        error_keys = []
        for at in atlist:
            atsplit = at.split(":")
            # 有可能是hp-1的情况
            if len(atsplit) == 1:
                r = atsplit[0].strip()
                pattern = re.match(r'(?P<thekey>[a-zA-Z]*)', r)
                name = pattern.group('thekey')
                value = re.sub('^[a-zA-Z]*', '', r).strip()
                name = name.upper()
                if name in userdata.keys():
                    oring_value = userdata[name]
                    if value[0] in ["+", "-", "*", "/"]:
                        try:
                            value_delta = int(value[1:])
                        except:
                            value_delta, _, _ = evaluate_expression(value[1:])
                        result = eval(str(oring_value) + value[0] + str(value_delta))
                        userdata[name] = result if result<=userdata[name+'_MAX'] else userdata[name+'_MAX']
                        self.data[wxid][msg_origin.sender] = userdata
                        self.update_data()
                        return "%s角色[%s]已由[%s]更新为[%s]"%(userdata['name'], name, oring_value, userdata[name])
                    elif int(value)>=0:
                        userdata[name] = int(value) if int(value)<=userdata[name+'_MAX'] else userdata[name+'_MAX']
                        self.data[wxid][msg_origin.sender] = userdata
                        self.update_data()
                        return "%s角色[%s]已由[%s]更新为[%s]"%(userdata['name'], name, oring_value, userdata[name])
                    else:
                        return "%s角色[%s]操作无法识别"%(userdata['name'], value)
                else:
                    return "%s角色无[%s]属性可以操作"%(userdata['name'], name)
            # 正常以冒号分割的情况
            if len(atsplit) == 2:
                att, value = atsplit
                att, value = att.strip(), value.strip()
            elif len(atsplit) == 3:
                att = atsplit[0].strip() + ":" + atsplit[1].strip()
                value = atsplit[2].strip()
            else:
                return ""
            # 具体设定
            if att in ['力量', '体质', '体型', '敏捷', '外貌', '智力', '意志', '教育', '幸运']:
                userdata['attribute'][att] = int(value)
            elif att.split(':')[0] in skill.keys():
                userdata['skill'][att] = int(value)
            elif att in story.keys():
                userdata['story'][att] = value
            elif att=="随身物品":
                userdata['item'].append(value)
            elif att=="职业":
                userdata['work'] = value
                if value in work.keys():
                    return  "【%s】已选择职业【%s】%s"%(self.data[wxid][msg_origin.sender]['name'], value, work[value])
                else:
                    return "【%s】已选择未登记职业【%s】" % (self.data[wxid][msg_origin.sender]['name'], value)
            elif att[0] == "&":
                att = att[1:]
                userdata['weapon'][att] = value
            elif att.upper() in ['HP', 'MP', 'SAN']:
                userdata[att.upper()] = int(value)
            else:
                error_keys.append(att)
                continue
            update_keys.append(att)

        if 'HP' not in userdata.keys():
            userdata['HP'] = (userdata['attribute']['体质'] + userdata['attribute']['体型'])//10
            userdata['HP_MAX'] = userdata['HP']
        if 'MP' not in userdata.keys():
            userdata['MP'] = userdata['attribute']['意志']//5
            userdata['MP_MAX'] = userdata['MP']
        if 'SAN' not in userdata.keys():
            userdata['SAN'] = userdata['attribute']['意志']
            userdata['SAN_MAX'] = 99
        if 'MOV' not in userdata.keys():
            if userdata['attribute']['力量']<userdata['attribute']['体型'] and userdata['attribute']['敏捷']<userdata['attribute']['体型']:
                userdata['MOV'] = 7
            elif userdata['attribute']['力量']>=userdata['attribute']['体型'] and userdata['attribute']['敏捷']>=userdata['attribute']['体型']:
                userdata['MOV'] = 9
            else:
                userdata['MOV'] = 8
        if 'DB' not in userdata.keys():
            if userdata['attribute']['力量']+userdata['attribute']['体型']<65:
                userdata['DB'] = '-2'
                userdata['体格'] = -2
            elif userdata['attribute']['力量']+userdata['attribute']['体型']<85:
                userdata['DB'] = '-1'
                userdata['体格'] = -1
            elif userdata['attribute']['力量']+userdata['attribute']['体型']<125:
                userdata['DB'] = '+0'
                userdata['体格'] = 0
            elif userdata['attribute']['力量']+userdata['attribute']['体型']<165:
                userdata['DB'] = '+1D4'
                userdata['体格'] = 1
            elif userdata['attribute']['力量']+userdata['attribute']['体型']<205:
                userdata['DB'] = '+1D6'
                userdata['体格'] = 2
            elif userdata['attribute']['力量']+userdata['attribute']['体型']<285:
                userdata['DB'] = '+2D6'
                userdata['体格'] = 3
            else:
                userdata['DB'] = '+3D6'
                userdata['体格'] = 4
        if "闪避" not in userdata['skill'].keys():
            userdata['skill']["闪避"] = userdata["attribute"]["敏捷"] // 2
        if "母语" not in userdata['skill'].keys():
            userdata['skill']["母语"] = userdata["attribute"]["教育"]
        self.data[wxid][msg_origin.sender] = userdata
        self.update_data()
        return "【%s】已更新【%s】,可用.find[属性/技能等]查看"%(self.data[wxid][msg_origin.sender]['name'], ','.join(update_keys))

    def find(self, msg, wxid, msg_origin):
        if msg_origin.sender not in self.data[wxid].keys():
            return "%s角色卡不存在，请先用.pcnew [角色姓名]创建角色卡"%(self.get_name(msg_origin.sender))
        data = self.data[wxid][msg_origin.sender]
        msg = msg.strip()
        if msg in data.keys() or msg.upper() in data.keys():
            return "%s的%s为%s"%(data['name'], msg.upper(), data[msg.upper()])
        if msg in data['attribute'].keys():
            return "%s的%s为%s" % (data['name'], msg, data['attribute'][msg])
        if msg in data['skill'].keys():
            return "%s的%s为%s" % (data['name'], msg, data['skill'][msg])
        if msg in skill.keys():
            return "%s的%s为%s" % (data['name'], msg, skill[msg])
        if msg in data['weapon'].keys():
            return "%s的武器【%s】伤害公式为%s" % (data['name'], msg, data['weapon'][msg])
        if msg in data['story'].keys():
            return "%s的背景[%s]为%s" % (data['name'], msg, data['story'][msg])
        if msg == "随身物品":
            return "%s的随身物品有%s" % (data['name'], '，'.join(data['item']))
        if msg == "属性":
            x = ""
            for atkey in data['attribute'].keys():
                x += "%s:%s"%(atkey, data['attribute'][atkey])
            return '%s的属性为\n%s'%(data['name'], x)
        if msg == "技能":
            x = ""
            for atkey in data['skill'].keys():
                x += "%s:%s"%(atkey, data['skill'][atkey])
            return '%s的技能为\n%s'%(data['name'], x)
        if msg == "背景":
            x = ""
            for atkey in data['story'].keys():
                x += "%s:%s;"%(atkey, data['story'][atkey])
            return '%s的背景为\n%s'%(data['name'], x)
        if msg == "武器":
            x = ""
            for atkey in data['weapon'].keys():
                x += "[%s]:[%s]\n"%(atkey, data['weapon'][atkey])
            return '%s的武器有\n%s'%(data['name'], x)
        if msg == "":
            x = ""
            for key in ['name', 'HP', 'HP_MAX', 'SAN', 'SAN_MAX', 'MP', 'MP_MAX', 'DB', '体格', 'MOV']:
                x += "【%s】:%s\n" % (key, data[key])
            x += "【属性】\n"
            for atkey in data['attribute'].keys():
                x += "%s:%s"%(atkey, data['attribute'][atkey])
            x += "\n【技能】\n"
            for atkey in data['skill'].keys():
                x += "%s:%s"%(atkey, data['skill'][atkey])
            x += "\n【武器】\n"
            for atkey in data['weapon'].keys():
                x += "[%s]:[%s]\n"%(atkey, data['weapon'][atkey])
            x += '【随身物品】\n' + '，'.join(data['item'])
            x += "【背景】\n"
            for atkey in data['story'].keys():
                x += "%s:%s;"%(atkey, data['story'][atkey])
            return x
        return "未查询到%s关于[%s]的信息！"%(data['name'], msg)

    def sanity_check(self, msg, wxid, msg_origin):
        if msg_origin.sender not in self.data[wxid].keys():
            return "%s角色卡不存在，请先用.pcnew [角色姓名]创建角色卡"%(self.get_name(msg_origin.sender))
        data = self.data[wxid][msg_origin.sender]
        msg = msg.strip()
        sucess_san, failed_san = msg.split('/')
        sanity_now = data['SAN']
        result, _, _ = evaluate_expression('1d100')
        if result <= sanity_now:
            try:
                sucess_san = int(sucess_san)
            except:
                sucess_san, _, _ = evaluate_expression(sucess_san)
            sanity_new = sanity_now - sucess_san
            response = "%s理智检定【成功:%s/%s】,SAN值扣除[%s],【%s->%s】"%(data['name'], result, sanity_now, sucess_san, sanity_now, sanity_new)
        else:
            try:
                failed_san = int(failed_san)
            except:
                failed_san, _, _ = evaluate_expression(failed_san)
            sanity_new = sanity_now - failed_san
            response = "%s理智检定【失败:%s/%s】,SAN值扣除[%s],【%s->%s】" % (data['name'], result, sanity_now, failed_san, sanity_now, sanity_new)
        self.data[wxid][msg_origin.sender]['SAN'] = sanity_new
        self.update_data()
        return response

    def check_attribute_with_value(self, msg, wxid, msg_origin):
        if msg_origin.sender in self.data[wxid].keys():
            user_name = self.data[wxid][msg_origin.sender]['name']
        else:
            user_name = self.get_name(msg_origin.sender)
        msg, value = msg.split("/")
        value = int(value)
        # 表达式计算
        msg = msg.strip()
        name = re.sub(r'[a-z0-9A-Z]*', '', msg)
        pattern = re.compile(r'(?P<times>[a-z0-9A-Z]*)')
        match = pattern.match(msg)
        msg = '1d100'+match.group('times') if match else '1d100'
        result, _, roll_step = evaluate_expression(msg)

        if result==1:
            nandu = "大成功！"
        elif result <= value//5:
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
        roll_step = roll_step[0]
        rss = "%s" % roll_step[0]
        if len(roll_step[1]) > 0:
            rss = rss + "，奖励骰为%s" % roll_step[1]
        if len(roll_step[2]) > 0:
            rss = rss + "，惩罚骰为%s" % roll_step[2]
        response = "%s进行[%s]检定，骰出了%s=【%s/%s】【%s】" % (user_name, name, rss, result, value, nandu)
        return response

    def check_attribute(self, msg, wxid, msg_origin):
        if msg_origin.sender not in self.data[wxid].keys():
            return "%s角色卡不存在，请先用.pcnew [角色姓名]创建角色卡"%(self.get_name(msg_origin.sender))
        data = self.data[wxid][msg_origin.sender]
        msg = msg.strip()
        pattern = re.compile(r'(?P<times>[a-z0-9A-Z]*)')
        match = pattern.match(msg)
        att = re.sub(r'[a-z0-9A-Z]*', '', msg)
        msg = '1d100'+match.group('times') if match else '1d100'
        result, _, roll_step = evaluate_expression(msg)
        if att in data['attribute'].keys():
            value = data['attribute'][att]
        elif att in data['skill'].keys():
            value = data['skill'][att]
        elif att in skill.keys():
            value = skill[att]
        else:
            return "%s角色未找到%s属性/技能" % (data['name'], att)
        if result==1:
            nandu = "大成功！"
        elif result <= value//5:
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
        if result <= value:
            if att in data['skill'] and att not in data['learn_skill']:
                data['learn_skill'].append(att)
        roll_step = roll_step[0]
        rss = "%s" % roll_step[0]
        if len(roll_step[1]) > 0:
            rss = rss + "，奖励骰为%s" % roll_step[1]
        if len(roll_step[2]) > 0:
            rss = rss + "，惩罚骰为%s" % roll_step[2]
        response = "%s进行[%s]检定，骰出了%s=【%s/%s】【%s】" % (data['name'], att, rss, result, value, nandu)
        return response

    def ensure_skill(self, wxid, msg_origin):
        if msg_origin.sender not in self.data[wxid].keys():
            return "%s角色卡不存在，请先用.pcnew [角色姓名]创建角色卡"%(self.get_name(msg_origin.sender))
        if self.data[wxid]['Gaming']!='end':
            return '游戏尚未结束，不能进行幕间成长！'
        data = self.data[wxid][msg_origin.sender]
        sanity_point = 0
        text = ""
        for skill in data['learn_skill']:
            result, _, _ = evaluate_expression('1d100')
            if result > data['skill'][skill] or result>95:
                origin = data['skill'][skill]
                origin += evaluate_expression('1d10')[0]
                text += "\n[%s]成长[%s->%s]"%(skill, data['skill'][skill], origin)
                if (origin >= 90) and (data['skill'][skill] < 90):
                    sanity_point += 1
                data['skill'][skill] = origin
            else:
                text += "\n[%s：%s]成长失败" % (skill, data['skill'][skill])
        if sanity_point>0:
            sanity_up = []
            for i in range(sanity_point):
                sanity_up.append(evaluate_expression('2d6')[0])
            san_origin = data['SAN']
            data['SAN'] = data['SAN'] + sum(sanity_up) if data['SAN'] + sum(sanity_up)<100 else 99
            text += "\n因为技能成长，获得%s理智：[%s->%s]"%(sanity_up, san_origin, data['SAN'])
        data['learn_skill'] = []
        self.data[wxid][msg_origin.sender] = data
        self.data.update()
        return '%s进行幕间成长：%s'%(data['name'], text)


    def get_roll(self, msg, wxid, msg_origin):
        msg = msg.replace(" ", "")
        expression = extract_non_chinese_prefix(msg)
        reason = msg[len(expression):].strip()

        if msg_origin.sender in self.data[wxid].keys():
            name = self.data[wxid][msg_origin.sender]['name']
            # 优先匹配存好的表达式
            if reason in self.data[wxid][msg_origin.sender]['weapon']:
                expression = self.data[wxid][msg_origin.sender]['weapon'][reason]
        else:
            name = self.get_name(msg_origin.sender)

        result, times, roll_step = evaluate_expression(expression)
        if times > 1:
            rsall = []
            for r in roll_step:
                rss = "%s"%r[0]
                if len(r[1]) > 0:
                    rss = rss + "，奖励骰为%s"%r[1]
                if len(r[2]) > 0:
                    rss = rss + "，惩罚骰为%s" % r[2]
                rsall.append(rss)
            response = "[%s]%s骰出了[%s]=%s=【%s】"%(name, reason, expression, ';'.join(rsall), ','.join([str(r) for r in result]))
        else:
            roll_step = roll_step[0]
            rss = "%s"%roll_step[0]
            if len(roll_step[1]) > 0:
                rss = rss + "，奖励骰为%s"%roll_step[1]
            if len(roll_step[2]) > 0:
                rss = rss + "，惩罚骰为%s" % roll_step[2]
            response = "[%s]%s骰出了[%s]=%s=【%s】"%(name, reason, expression, rss, result)
        return response

if __name__ == "__main__":
    aa = Myself({"file_path" : "./mydata.pk"}, None)
    print(aa.get_answer('.r1d100', "", None))
