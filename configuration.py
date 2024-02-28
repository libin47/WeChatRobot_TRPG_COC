#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging.config
import os
import shutil
import sys

import yaml


class Config(object):
    def __init__(self) -> None:
        self.reload()

    def _load_config(self) -> dict:
        # pwd = os.path.dirname(os.path.abspath(__file__))
        # try:
        #     with open(f"{pwd}/config.yaml", "rb") as fp:
        #         yconfig = yaml.safe_load(fp)
        # except FileNotFoundError:
        #     shutil.copyfile(f"{pwd}/config.yaml.template", f"{pwd}/config.yaml")
        #     with open(f"{pwd}/config.yaml", "rb") as fp:
        #         yconfig = yaml.safe_load(fp)

        if getattr(sys, 'frozen', None):
            basedir = sys._MEIPASS
        else:
            basedir = os.path.dirname(__file__)
        config_file = os.path.join(basedir, "config.yaml")
        config_temp = os.path.join(basedir, "config.yaml.template")
        try:
            with open(config_file, "rb") as fp:
                yconfig = yaml.safe_load(fp)
        except FileNotFoundError:
            shutil.copyfile(config_temp, config_file)
            with open(config_file, "rb") as fp:
                yconfig = yaml.safe_load(fp)
        return yconfig

    def reload(self) -> None:
        yconfig = self._load_config()
        logging.config.dictConfig(yconfig["logging"])
        self.GROUPS = yconfig["groups"]["enable"]
        self.Myself = yconfig.get("myself", {})
