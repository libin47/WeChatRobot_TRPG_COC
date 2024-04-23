import re
import random
import os
import datetime
import sys
import json
import time

from base.jrrp import Jrrp
from PIL import Image, ImageFont, ImageDraw
import numpy as np

class DiceBase(object):
    def __init__(self, config, wcf):
        self.config = config
        self.logfile = config['file_path']
        if not os.path.exists(self.logfile):
            os.mkdir(self.logfile)
        self.wcf = wcf

    def log_input(self, group, input, name):
        with open(os.path.join(self.logfile, "%s.txt"%group), "a", encoding="utf8") as f:
            f.write('【%s】%s\n%s\n' % (name, datetime.datetime.now().strftime("%Y年%m月%d日%H:%M:%S"), input))

    def log_get(self, group):
        dirname, filename = os.path.split(os.path.abspath(sys.argv[0]))
        self.wcf.send_file(os.path.join(dirname, self.logfile, "%s.txt"%group), group)
        return

    def _get_name(self, wxid):
        name = self.wcf.get_info_by_wxid(wxid)
        return name['name']
        # return wxid

    def _dice_jrrp(self, group,  wxid):
        r = self.roll_dice("1d100")
        name = self._get_name(wxid)
        return "【%s】今日人品值为：%s"%(name, r[-1])

    def _dice_yijing(self, group, wxid):
        return self._yijing(group, wxid)

    def _dice_taluo(self, group, wxid):
        return self._taluo(group, wxid)

    def roll_dice(self, expression):
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


    def evaluate_expression(self, expression):
        pattern = re.compile(r'^(?P<times>\d+#)?(\d+)([dD](\d+)(b\d+)?(p\d+)?)?([\+-x*\/÷](\d+)([dD](\d+)(b\d+)?(p\d+)?)?)*$')
        match = pattern.match(expression)
        expression = re.sub(r'\d+#', '', expression)

        if not match:
            return False
        else:
            if match.group("times"):
                times = int(match.group('times')[:-1])
            else:
                times = 1

        roll_result = []

        def repl(match):
            r = self.roll_dice(match.group(0))
            roll_result.append(r[:3])
            return str(int(r[3]))
        # 使用正则表达式匹配掷骰子表达式，替换后计算表达式的值
        # print(expression)
        if times == 1:
            return eval(re.sub(r'\d+[dD]\d+(b\d+)?(p\d+)?', repl, expression)), times, roll_result
        else:
            return [eval(re.sub(r'\d+[dD]\d+(b\d+)?(p\d+)?', repl, expression)) for _ in range(times)], times, roll_result


    def _yijing(self, group, wxid):
        yjdata = Jrrp().yijing()
        result = random.randint(0, len(list(yjdata.keys()))-1)
        key = list(yjdata.keys())[result]
        data = yjdata[key]
        # 发送图片
        dirname, filename = os.path.split(os.path.abspath(sys.argv[0]))
        self.wcf.send_image(os.path.join(dirname, data["url"][0]), group if group else wxid)
        self.wcf.send_image(os.path.join(dirname, data["url"][1]), group if group else wxid)
        # 发送结果
        res = "[%s]您抽中了【%s】卦。\n【原文】%s\n\n%s\n%s"%(self._get_name(wxid), key, data["原文"], data["彖曰"], data["象曰"])
        if len(data["文言曰"])>0:
            res += "\n" + "\n".join(data["文言曰"])

        return res

    def _taluo(self, group, wxid):
        tldata = Jrrp().taluo()
        keylist = list(tldata.keys())
        result = random.sample(keylist, 3)
        zn = random.choices([1,-1], k=3)
        # 文字结果
        res = "[%s]您以塔罗牌【时间序列】进行占卜，抽中结果为【%s】"%(self._get_name(wxid), ",".join([result[i] + ("" if zn[i]>0 else "(逆位)") for i in range(3)]))
        # 图片结果1
        img1 = Image.open(tldata[result[0]]["image"])

        img2 = Image.open(tldata[result[1]]["image"])
        img3 = Image.open(tldata[result[2]]["image"])
        if zn[0]<0:
            img1 = img1.transpose(Image.ROTATE_180)
        if zn[1]<0:
            img2 = img2.transpose(Image.ROTATE_180)
        if zn[1]<0:
            img3 = img3.transpose(Image.ROTATE_180)
        img = np.concatenate((img1, img2, img3), axis=1)
        img = Image.fromarray(img)
        fname = "data/%s.jpg"%wxid
        img.save(fname)
        dirname, filename = os.path.split(os.path.abspath(sys.argv[0]))
        self.wcf.send_image(os.path.join(dirname, fname), group if group else wxid)
        self.wcf.send_text(res, group if group else wxid)
        time.sleep(0.5)
        # 解析
        for i in range(3):
            d = tldata[result[i]]
            r = "【%s%s】\n画面内容：%s\n 释义：%s"%(result[i], "" if zn[i]>0 else "(逆位)", d["画面内容"], d["正位牌释义"] if zn[i]>0 else d["逆位牌释义"])
            self.wcf.send_text(r, group if group else wxid)
            time.sleep(0.5)
        return ""
