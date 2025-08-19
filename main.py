#! /usr/bin/env python3
# -*- coding: utf-8 -*-
from robot.wxauto_robot import Robot
from configuration import Config

if __name__ == "__main__":
    config = Config()
    robot = Robot(config)
