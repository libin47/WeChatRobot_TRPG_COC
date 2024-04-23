import re

def extract_data(text):
    weapon_data = {}

    # 武器名称
    weapon_name_match = re.search(r'【(.+?)】', text)
    if weapon_name_match:
        weapon_data["名称"] = weapon_name_match.group(1)

    # 技能类型
    skill_match = re.search(r'技能：(.+)', text)
    if skill_match:
        weapon_data["技能"] = skill_match.group(1)

    # 伤害
    damage_match = re.search(r'伤害：(.+)', text)
    if damage_match:
        weapon_data["伤害"] = damage_match.group(1)

    # 次数
    times_match = re.search(r'次数：(\d+)', text)
    if times_match:
        weapon_data["次数"] = int(times_match.group(1))

    # 贯穿
    penetration_match = re.search(r'非贯穿', text)
    weapon_data["贯穿"] = bool(not penetration_match)

    # 射程
    range_match = re.search(r'射程：(.+)', text)
    if range_match:
        weapon_data["射程"] = range_match.group(1)

    # 装弹量
    ammo_match = re.search(r'装弹量：(.+)', text)
    if ammo_match and ammo_match.group(1) != "N/A":
        try:
            weapon_data["装弹量"] = int(ammo_match.group(1))
        except:
            try:
                weapon_data["装弹量"] = int(ammo_match.group(1).split("/")[-1])
            except:
                weapon_data["装弹量"] = -1
    else:
        weapon_data["装弹量"] = -1

    # 故障率
    failure_rate_match = re.search(r'故障率：(.+)', text)
    if failure_rate_match and failure_rate_match.group(1) != "N/A":
        weapon_data["故障率"] = int(failure_rate_match.group(1))
    else:
        weapon_data["故障率"] = -1

    return weapon_data

def number2num(s):
    # print(s)
    s=s.strip()
    if s=="一":
        return 1
    elif s=="二":
        return 2
    elif s=="三":
        return 3
    elif s=="四":
        return 4
    elif s=="五":
        return 5



def extract_work(text):
    weapon_data = {}

    # 武器名称
    weapon_name_match = re.search(r'\n(.+?)\n信用评级', text)
    if weapon_name_match:
        weapon_data["name"] = weapon_name_match.group(1)

    # 技能类型
    skill_match = re.search(r'信用评级：(.+)\n', text)
    if skill_match:
        weapon_data["信用评级"] = [int(x) for x in skill_match.group(1).split("~")]

    # 伤害
    damage_match = re.search(r'本职技能：(.+)', text)
    if damage_match:
        weapon_data["describe"] = damage_match.group(1)

    # 技能
    skilllist = weapon_data["describe"].split("、")
    result = []
    for text in skilllist:
        # if "射击(" in text:
        #     print(text)
        if text=="格斗(斗殴)":
            result.append({"name": text})
            continue
        select_match = re.search(r'选(.+)\((.+)\)', text)
        if select_match:
            number = number2num(select_match.group(1))
            sklist = select_match.group(2).split(",")
            sklistresult = []
            for sk in sklist:
                if len(sk.split(":"))>1:
                    n, sn = sk.split(":")
                    if sn == "任一":
                        sklistresult.append({"name": n})
                    else:
                        sklistresult.append({"name": n, "sub_name": sn})
                else:
                    sklistresult.append({"name": sk})
            result.append({"number": number, "area": "list", "list": sklistresult})
            continue
        select_match = re.search(r'(.+)\(任(.+)\)', text)
        if select_match:
            number = number2num(select_match.group(2))
            name = select_match.group(1)
            if "其他" in name:
                result.append({"number": number, "area": "all"})
            else:
                for i in range(number):
                    result.append({"name": name})
            continue
        select_match = re.search(r'(.+)\((.+)\)', text)
        if select_match:
            subname = select_match.group(2)
            name = select_match.group(1)
            result.append({"name": name, "sub_name": subname})
            continue
        result.append({"name": text})
    result.append({ "name": "信用评级" })
    weapon_data["skill"] = result
    return weapon_data
# 测试
textgroup = ["""
军官
信用评级：20~70
使用
职业点数：教育×2 + (力量×2 或 敏捷×2)
本职技能：四选二(取悦,话术,恐吓,说服)、会计、射击(任一)、导航、急救、心理学、其他个人或时代特长(任一)""","""
海军
信用评级：9~30
使用
职业点数：教育×4
本职技能：二选一(电气维修,机械维修)、格斗(任一)、射击(任一)、急救、导航、驾驶(船)、生存(海上)、游泳""","""
间谍
信用评级：20~60
使用
职业点数：教育×2 + (敏捷×2 或 外貌×2)
本职技能：二选一(技艺:表演,乔装)、四选一(取悦,话术,恐吓,说服)、射击(任一)、聆听、外语(任一)、心理学、妙手、潜行""","""
士兵
信用评级：9~30
使用
职业点数：教育×2 + (力量×2 或 敏捷×2)
本职技能：二选一(攀爬,游泳)、二选一(机械维修,外语:任一)、闪避、格斗(任一)、射击(任一)、潜行、生存(任一)、急救""","""
警探(原作向)
信用评级：20~50
使用
职业点数：教育×2 + (力量×2 或 敏捷×2)
本职技能：二选一(技艺:表演,乔装)、四选一(取悦,话术,恐吓,说服)、射击(任一)、法律、聆听、心理学、侦查、其他个人或时代特长(任一)""","""
巡警(原作向)
信用评级：9~30
使用
职业点数：教育×2 + (力量×2 或 敏捷×2)
本职技能：二选一(汽车驾驶,骑术)、四选一(取悦,话术,恐吓,说服)、格斗(斗殴)、射击(任一)、急救、法律、心理学、侦查""","""
消防员
信用评级：9~30
使用
职业点数：教育×2 + (力量×2 或 敏捷×2)
本职技能：攀爬、闪避、汽车驾驶、急救、跳跃、机械维修、操作重型机械、投掷""","""
法官
信用评级：50~80
使用
职业点数：教育×4
本职技能：历史、恐吓、法律、图书馆使用、聆听、母语(任一)、说服、心理学""","""
司法人员
信用评级：20~40
使用
职业点数：教育×4
本职技能：汽车驾驶、格斗(斗殴)、射击(任一)、法律、说服、潜行、侦查、其他个人或时代特长(任一)""","""
政府官员
信用评级：50~90
使用
职业点数：教育×2 + 外貌×2
本职技能：取悦、历史、恐吓、话术、聆听、母语(任一)、说服、心理学""","""
工会活动家
信用评级：5~50
使用
职业点数：教育×4
本职技能：四选二(取悦,话术,恐吓,说服)、会计、格斗(斗殴)、法律、聆听、操作重型机械、心理学"""]

for text in textgroup:
    result = extract_work(text)
    print("\"%s\":"%result["name"],result,",")
    # print("{label: \"%s\", value: \"%s\"},"%(result['名称'],result['名称']))

for text in textgroup:
    result = extract_work(text)
    print("{label: \"%s\", value: \"%s\"},"%(result['name'],result['name']))