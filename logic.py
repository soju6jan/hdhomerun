# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
import time
import re
import urllib
from datetime import datetime
import threading

# third-party
from flask import Blueprint, request, Response, send_file, render_template, redirect, jsonify

# sjva 공용
from framework import app, db, scheduler, path_data
from framework.job import Job
from framework.util import Util

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting
#########################################################
        
class Logic(object):
    db_default = {
        'data_filename' : os.path.join(path_data, 'db', 'hdhomerun.txt'),
        'group_sort' : u'TOP, 지상파, 종합편성, 뉴스/경제, 스포츠, 영화, 연예/오락, 드라마, 다큐, 교양, 음악, 레저, 만화, 어린이, 교육, 여성/패션, 공공, 종교, 홈쇼핑, 해외위성, 라디오, 기타',
        'deviceid' : '', 
        'trans_option' : '-c:v copy -c:a aac -b:a 128k -f mpegts -tune zerolatency pipe:stdout',
        'attach_mpeg_ext' : 'True',
        'tuner_name' : 'auto',
    }
    

    @staticmethod
    def db_init():
        try:
            for key, value in Logic.db_default.items():
                if db.session.query(ModelSetting).filter_by(key=key).count() == 0:
                    db.session.add(ModelSetting(key, value))
            db.session.commit()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def plugin_load():
        try:
            logger.debug('%s plugin_load', package_name)
            # DB 초기화
            Logic.db_init()

            # 편의를 위해 json 파일 생성
            from .plugin import plugin_info
            Util.save_from_dict_to_json(plugin_info, os.path.join(os.path.dirname(__file__), 'info.json'))
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def plugin_unload():
        try:
            logger.debug('%s plugin_unload', package_name)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
 
    # 기본 구조 End
    ##################################################################
