import os
import requests
import json
from base.wedice_group import WeDiceGroup
import re
# from wcferry import Wcf, WxMsg
import time
from bs4 import BeautifulSoup

class WeDice(WeDiceGroup):
    def __init__(self, config, send_text=None, send_file=None, send_image=None, get_info_by_wxid=None):
        super(WeDice, self).__init__(config, send_text, send_file, send_image, get_info_by_wxid)



    def get_answer(self, cmd: str, sender=None, group=None, atuser=[], refer="") -> str:
        # 引用？
        # if msg.type == 49:
        #     msgxml = BeautifulSoup(msg.content, 'xml')
        #     cmd = msgxml.find("title").text

        # 获取回答主函数
        wxid = sender
        cmd = self._clear_cmd(cmd)
        if group:
            self._init_group(group)
            atwxids = atuser
            if len(atwxids)>0:
                cmd = re.sub("@.*", "", cmd).strip()
                allresult = ""
                for key in atwxids:
                    result = self.get_group_answer(cmd, key, group, wxid, refer)
                    self.save_log(group=group, wxid=wxid, cmd=cmd, result=result)
                    if result:
                        allresult += result+"\n"
                return allresult
            else:
                result = self.get_group_answer(cmd, wxid, group, wxid, refer)
                self.save_log(group=group, wxid=wxid, cmd=cmd, result=result)
                return result
        else:
            result = self.get_user_answer(cmd, wxid)
            return result

if __name__ == "__main__":
    from configuration import Config
    config = Config()
    a = WeDice(config.Myself)
    result = a.get_answer(".start", "aaa", "1234")
    result = a.get_answer(".rc 50", "aaa", "1234")
    print(result)