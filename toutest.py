import re
import random
from collections import Counter
from fractions import Fraction


def roll_dice(expression):
    # 匹配掷骰表达式的正则表达式
    pattern = re.compile(r'(?P<times>\d*#)?(?P<count>\d+)d(?P<sides>\d+)(b(?P<bonus>\d+))?(p(?P<penalty>\d+))?')
    match = pattern.match(expression)

    if not match:
        raise ValueError("Invalid dice rolling expression: {}".format(expression))

    # 提取掷骰相关参数
    times = int(match.group('times')[:-1]) if match.group('times') else 1
    count = int(match.group('count'))
    sides = int(match.group('sides'))
    bonus = int(match.group('bonus')) if match.group('bonus') else 0
    penalty = int(match.group('penalty')) if match.group('penalty') else 0

    # 投掷骰子
    results = [random.randint(1, sides) for _ in range(times)]

    # 计算奖励骰和惩罚骰
    if bonus:
        results.extend([random.randint(1, sides) for _ in range(bonus)])
    if penalty:
        results.extend([-random.randint(1, sides) for _ in range(penalty)])

    return results


def evaluate_expression(expression):
    # 替换表达式中的掷骰子部分为其结果
    def repl(match):
        return str(sum(roll_dice(match.group(0))))

    # 使用正则表达式匹配掷骰子表达式，替换后计算表达式的值
    return eval(re.sub(r'\d*#?\d+d\d+(b\d+)?(p\d+)?', repl, expression))


def extract_non_chinese_prefix(input_string):
    # 提取非汉字部分作为表达式
    pattern = re.compile(r'([0-9a-zA-Z\.\+\-\*\/]+)')
    match = pattern.match(input_string)
    if match:
        return match.group(1)
    return ""

def main():
    while True:
        try:
            user_input = input("请输入掷骰表达式和掷骰原因（可选），例如：1d6+2 [掷骰原因]：")
            if not user_input:
                break
            user_input.replace(" ", "")
            expression = extract_non_chinese_prefix(user_input)
            reason = user_input[len(expression):].strip()

            result = evaluate_expression(expression)
            print("投掷结果为:", result)
            if reason:
                print("掷骰原因:", reason)
        except Exception as e:
            print("发生错误:", e)


if __name__ == "__main__":
    main()
