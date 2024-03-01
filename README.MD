# 微信版骰子机器人
一个基于[WeChatFerry](https://github.com/lich0821/WeChatFerry)的微信机器人。
参考[WeChatRobot](https://github.com/lich0821/WeChatRobot)。

可用于在微信聊天中掷骰子，主要适用于标准COC7版规则下的TRPG，其他规则可能待补充。

如果只用基础投掷功能，也可用于其他TRPG。

## 环境
因为是基于Windows下微信客户端HOOK方式的机器人，所以只能运行在windows环境下，想要部署在linux环境下同学得另寻他路了。

## 使用说明
### 可选1
如果想要对程序进行修改完善，可按照以下说明开始：
1. 安装微信 `3.9.2.23`，下载地址在 [这里](https://github.com/lich0821/WeChatFerry/releases/latest)；也可以从 [WeChatSetup](https://gitee.com/lch0821/WeChatSetup) 找到。
2. 克隆项目，安装环境，需要python>=3.9
3. 登录微信后，运行main.py即可
4. 编译成exe文件方便部署
```shell
pyinstaller -F --add-data "config.yaml;." --add-data "C:\...\Python39\site-packages\wcferry\*;.\wcferry"  main.py 
```
### 可选2
1. 安装微信 `3.9.2.23`，下载地址在 [这里](https://github.com/lich0821/WeChatFerry/releases/latest)；也可以从 [WeChatSetup](https://gitee.com/lch0821/WeChatSetup) 找到。
2. 如果想直接使用可[直接下载打包好的exe文件](https://github.com/libin47/WeChatRobot_TRPG_COC/releases/download/exe/coc_robot.exe)，在启动微信后直接运行即可（未测试，应该是需windows10+系统）

## 目前实现功能
未特别说明的功能仅限群聊可用。

![img.png](pic/show.png)
### 【基础投掷】
#### .r\[投掷表达式]([投掷原因])
[投掷表达式] = ([掷骰次数]#)[骰子个数]d[骰子面数] (b[奖励骰个数])(p[惩罚骰个数])  
私聊可用
- `.r1d100+10`
- `.r1d100b2`
- `.r1d100p2`
- `.r1d6+2 砍刀伤害`    
- `.r3#1d100`
- `.r沙漠之鹰`    录入存在角色卡时，可调用角色卡中保存武器的表达式
- `.r3d6*5`     乘号不能用x
#### .jrrp
看看今日人品如何  
私聊可用
### 【机器人控制】
#### .h/.help  
帮助
#### .hpc      
创建角色卡的使用指引
#### .boton    
在本群启动机器人
#### .botoff   
在本群关闭机器人
#### .start    
开始游戏，开始记录所有聊天记录
#### .pause    
游戏暂停，停止记录log
#### .end      
游戏结束，停止记录log，可进行成长检定
#### .log
获取游戏日志，发送个txt文件到群里
### 【游戏中】
#### .coc([生成组数])
生成指定组数的随机属性值，不填时生成一组。    
私聊可用
#### .pcnew [姓名]
创建指定姓名的角色卡
#### .st [表达式]
录入、修改或操作角色各项属性，多个之间英文逗号分开，例如:
- `.st 力量:50,体质:55,体型:65,敏捷:45,外貌:70,智力:75,意志:35,教育:65,幸运:75`  录入属性时自动补充衍生属性HP/MP/MOV/SAN等
- `.st 会计:70,格斗:斗殴:50,侦查:60`  录入技能
- `.st 特质:喜欢吃面条,形象描述:帅`
- `.st 随身物品:打火机`
- `.st hp-2` 可修改HP/MP/SAN值
- `.st san-1d6` 支持投掷表达式
- `.st &沙漠之鹰:1d10+2` 录入武器及伤害表达式，可通过`.r沙漠之鹰`roll
- `.st 职业:医生` 录入职业时如果是默认职业则返回对应职业说明
#### .ra 属性/技能
进行属性或技能检定
#### .rc [描述]/[通过值]
指定通过值的检定，无需先生成角色卡，例如`.rc 力量/60`
#### .sc [表达式]/[表达式]
进行San Check，例如 `.sc 1/1d6`
#### .find ([项])
查看当前角色指定项目的值，如果不指定则查看全部。例如：
- `.find 力量`
- `.find 属性`
- `.find 会计`
- `.find 技能`
- `.find 随身物品`
- `.find 武器`
- `.find 沙漠之鹰`
- `.find`
#### .del [物品/武器]
删除对应的武器或随身物品
#### .en
进行成长检定，所有记录过成功的技能将会进行成长检定，如果超过90自动获取理智恢复
