# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
import json
from datetime import datetime

# third-party

# sjva 공용
from framework import db, app, path_app_root

# 패키지
from .plugin import logger, package_name


db_file = os.path.join(path_app_root, 'data', 'db', '%s.db' % package_name)
app.config['SQLALCHEMY_BINDS'][package_name] = 'sqlite:///%s' % (db_file)

class ModelSetting(db.Model):
    __tablename__ = 'plugin_%s_setting' % package_name
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = package_name

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String, nullable=False)
 
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return repr(self.as_dict())

    def as_dict(self):
        return {x.name: getattr(self, x.name) for x in self.__table__.columns}

    @staticmethod
    def get(key):
        try:
            return db.session.query(ModelSetting).filter_by(key=key).first().value.strip()
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())
    
    @staticmethod
    def get_int(key):
        try:
            return int(ModelSetting.get(key))
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())
    
    @staticmethod
    def get_bool(key):
        try:
            return (ModelSetting.get(key) == 'True')
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())

    @staticmethod
    def set(key, value):
        try:
            item = db.session.query(ModelSetting).filter_by(key=key).with_for_update().first()
            if item is not None:
                item.value = value.strip()
                db.session.commit()
            else:
                db.session.add(ModelSetting(key, value.strip()))
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())

    @staticmethod
    def to_dict():
        try:
            from framework.util import Util
            return Util.db_list_to_dict(db.session.query(ModelSetting).all())
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())


    @staticmethod
    def setting_save(req):
        try:
            for key, value in req.form.items():
                logger.debug('Key:%s Value:%s', key, value)
                entity = db.session.query(ModelSetting).filter_by(key=key).with_for_update().first()
                entity.value = value
            db.session.commit()
            return True                  
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            logger.debug('Error Key:%s Value:%s', key, value)
            return False

#########################################################


class ModelHDHomerunChannel(db.Model):
    __tablename__ = 'plugin_%s_hdhomerun_channel' % package_name
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = package_name

    id = db.Column(db.Integer, primary_key=True)
    json = db.Column(db.JSON)
    created_time = db.Column(db.DateTime)

    ch_type = db.Column(db.String) # hdhomerun, custom

    # scan 정보
    scan_vid = db.Column(db.String)
    scan_name = db.Column(db.String)
    scan_frequency = db.Column(db.String) 
    scan_program = db.Column(db.String)
    scan_ch = db.Column(db.String)

    # m3u & epg
    for_epg_name = db.Column(db.String)
    group_name = db.Column(db.String)

    use_vid = db.Column(db.Boolean) 
    use = db.Column(db.Boolean)
    ch_number = db.Column(db.Integer)
    # custom url 
    url = db.Column(db.String) 

    match_epg_name = db.Column(db.String)
    def __init__(self):
        # for ui
        # match_epg_name
        self.match_epg_name = ''
        self.created_time = datetime.now()
        self.ch_number = 0
        self.group_name = ''

    def init_data(self, data):
        self.ch_type = 'hdhomerun'
        self.use_vid = False
        tmp = data.split('|')
        self.scan_vid = tmp[0].strip()
        #self.ch_number = tmp[0]
        self.scan_name = tmp[1].strip()
        self.for_epg_name = tmp[1].strip()
        self.scan_frequency = tmp[2].strip()
        self.scan_program = tmp[3].strip()
        self.scan_ch = tmp[4].strip()
        self.scan_modulation = tmp[5].strip()
        self.use = True
        if self.scan_vid == '0' or self.scan_name == '':
            self.use = False
        
        tmp = ['encrypted', 'no data', '데이터 방송', 'control']
        for t in tmp:
            if self.scan_name.find(t) != -1:
                self.use = False
                break
        self.match_epg()

    def set_url(self, deviceid):
        if self.use_vid:
            self.url = 'http://%s:5004/auto/v%s' % (deviceid, self.scan_vid)
        else:
            self.url = 'http://%s:5004/auto/ch%s-%s.mpeg' % (deviceid, self.scan_frequency, self.scan_program)



    def as_dict(self):
        ret = {x.name: getattr(self, x.name) for x in self.__table__.columns}
        ret['created_time'] = self.created_time.strftime('%m-%d %H:%M:%S') if ret['created_time'] is not None else None
        if self.json is not None:
            ret['json'] = json.loads(ret['json'])
        else:
            ret['json'] = {}
        return ret

    def match_epg(self):
        try:
            import epg
            ret = epg.Logic.get_match_name(self.for_epg_name)
            if ret is not None:
                self.match_epg_name = ret[0]
                self.group_name = ret[1]
                return True
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False
