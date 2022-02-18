# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
import json

# third-party
from flask import Blueprint, request, Response, send_file, render_template, redirect, jsonify

# sjva 공용
from framework import app, db, scheduler, path_data, celery, SystemModelSetting, py_urllib

# 패키지
from .plugin import package_name, logger
from .model import ModelSetting, ModelHDHomerunChannel
from .logic import Logic


# 로그
#########################################################
class LogicHDHomerun(object):
    
    @staticmethod
    def load_data():
        try:
            import framework.common.util as CommonUtil
            data = CommonUtil.read_file(ModelSetting.get('data_filename'))
            ret = {}
            if data is not None:
                data = data.split('\n')
                deviceid = data[0].strip()
                tmp = deviceid.find('192')
                deviceid = deviceid[tmp:]
                
                ModelSetting.set('deviceid', deviceid)
                logger.debug('deviceid:%s', deviceid)
                logger.debug('deviceid:%s', len(deviceid))

                ModelHDHomerunChannel.query.delete()
                channel_list = []
                for item in data[1:]:
                    if item.strip() == '':
                        continue
                    m = ModelHDHomerunChannel()
                    m.init_data(item)
                    db.session.add(m)
                    m.set_url(deviceid, ModelSetting.get_bool('attach_mpeg_ext'), ModelSetting.get('tuner_name'))
                    channel_list.append(m)
                no = 1
                for m in channel_list:
                    if m.use:
                        m.ch_number = no
                        no += 1
                for m in channel_list:
                    if not m.use:
                        m.ch_number = no
                        no += 1
                
                db.session.commit()
                lists =  db.session.query(ModelHDHomerunChannel).all()
                tmp = LogicHDHomerun.channel_list()
                ret['data'] = [item.as_dict() for item in tmp]
            else:
                ret['ret'] = 'fail'
                ret['log'] = 'load data fail!!'

        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['log'] = str(e)
        return ret

    @staticmethod
    def channel_list(only_use=False):
        try:
            query = db.session.query(ModelHDHomerunChannel)
            if only_use:
                query = query.filter_by(use=True)
            query = query.order_by(ModelHDHomerunChannel.ch_number)
            query = query.order_by(ModelHDHomerunChannel.id)

            return  query.all()
            #return [item.as_dict() for item in lists]
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def group_sort():
        try:
            items = LogicHDHomerun.channel_list()
            orders = [x.strip() for x in ModelSetting.get('group_sort').split(',')]
            orders.append('except')
            data = {}
            for o in orders:
                data[o] = []

            for channel in items:
                if channel.group_name in data:
                    data[channel.group_name].append(channel)
                else:
                    data['except'].append(channel)

            ret = []
            for o in orders:
                for t in data[o]:
                    ret.append(t.as_dict())

            #return [item.as_dict() for item in ret]
            return ret
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def save(req):
        try:
            ret = {}
            count = 0
            deviceid = ModelSetting.get('deviceid')
            for key, value in req.form.items():
                tmp = key.split('|')
                value = value.strip()
                mc = db.session.query(ModelHDHomerunChannel).filter(ModelHDHomerunChannel.id == tmp[1]).with_for_update().first()
                if mc is not None:
                    if tmp[0] == 'use_checkbox':
                        mc.use = True if value == 'True' else False
                    if tmp[0] == 'use_vid_checkbox':
                        mc.use_vid = True if value == 'True' else False
                        mc.set_url(deviceid, ModelSetting.get_bool('attach_mpeg_ext'), ModelSetting.get('tuner_name'))
                    if tmp[0] == 'ch_number':
                        mc.ch_number = int(value)
                    if tmp[0] == 'scan_name':
                        mc.scan_name = value
                    if tmp[0] == 'for_epg_name':
                        mc.for_epg_name = value
                    if tmp[0] == 'group_name':
                        mc.group_name = value
            db.session.commit()
            return True
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False


    @staticmethod
    def match_for_epg_name(channel_id, for_epg_name):
        try:
            ret = {}
            count = 0
            
            model = db.session.query(ModelHDHomerunChannel).filter(ModelHDHomerunChannel.id == channel_id).with_for_update().first()

            if model is not None:
                model.for_epg_name = for_epg_name
                if model.match_epg():
                    db.session.commit()
                    ret['ret'] = "success"
                    ret['match_epg_name'] = model.match_epg_name
                    ret['group_name'] = model.group_name
                else:
                    ret['ret'] = 'no_match'
            else:
                ret['ret'] = 'no_channel'
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
        return ret
    
    @staticmethod
    def delete(channel_id):
        try:
            count = db.session.query(ModelHDHomerunChannel).filter(ModelHDHomerunChannel.id == channel_id).delete()
            db.session.commit()
            #logger.debug(count)
            if count == 1:
                return 'success'
            else:
                return 'no_channel'
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return 'fail'


    @staticmethod
    def get_m3u(trans=False):
        try:
            M3U_FORMAT = '#EXTINF:-1 tvg-id=\"%s\" tvg-name=\"%s\" tvg-chno=\"%s\" tvg-logo=\"%s\" group-title=\"%s\",%s\n%s\n'

            m3u = '#EXTM3U\n'
            data = LogicHDHomerun.channel_list(only_use=True)
            ddns = SystemModelSetting.get('ddns')
            for c in data:
                try:
                    import epg2
                    ins = epg2.ModelEpg2Channel.get_by_name(c.match_epg_name)
                except:
                    ins = None
                #m3u += M3U_FORMAT % (c.source+'|' + c.source_id, c.title, c.epg_entity.icon, c.source, c.title, url)
                url = c.url
                if trans:
                    url = ddns + '/hdhomerun/trans.ts?source=' + py_urllib.quote_plus(url)
                m3u += M3U_FORMAT % (c.id, c.scan_name, c.ch_number, (ins.icon if ins is not None else ""), c.group_name, c.scan_name, url)
            
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return m3u

    
    @staticmethod
    def ip_fix(deviceid):
        try:
            data = LogicHDHomerun.channel_list()
            for c in data:
                c.set_url(deviceid, ModelSetting.get_bool('attach_mpeg_ext'), ModelSetting.get('tuner_name'))
            db.session.commit()
            return True
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False
