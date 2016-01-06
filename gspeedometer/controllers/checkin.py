# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#!/usr/bin/python2.4
#

"""Service to collect and visualize mobile network performance data."""

__author__ = 'mdw@google.com (Matt Welsh)'

import logging

from django.utils import simplejson as json
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp

from gspeedometer import model
from gspeedometer.helpers import error
from gspeedometer.helpers import util

from datetime import datetime, timedelta
import time, math
import random

CDN_TARGETS = ['ec-media.soundcloud.com' , #EdgeCast
               'video-http.media-imdb.com' , #Amazon CloudFront
               'cdn2.nflximg.net', #Akamai
               'img.delvenetworks.com' , # Limelight
               'www.google.com',
               'fbcdn-profile-a.akamaihd.net']


class Checkin(webapp.RequestHandler):
  """Checkin request handler."""

  def Checkin(self, **unused_args):
    """Handler for checkin requests."""
    
    if self.request.method.lower() != 'post':
      raise error.BadRequest('Not a POST request.')

    checkin = json.loads(self.request.body)
    logging.info('Got checkin: %s', self.request.body)
    

    try:
      # Change device id such that it is anonymized, but preserve TAC.
      checkin['tac'] = util.GetTypeAllocationCode(checkin['id'])
      checkin['id'] = util.HashDeviceId(checkin['id'])
      # Extract DeviceInfo.
      device_id = checkin['id']
      logging.info('Checkin from device %s', device_id)
      device_info = model.DeviceInfo.get_or_insert(device_id)
 
      device_info.user = users.get_current_user()
      # Don't want the embedded properties in the device_info structure.
      device_info_dict = dict(checkin)
      del device_info_dict['properties']
      util.ConvertFromDict(device_info, device_info_dict)
      device_info.put()
 
      # Extract DeviceProperties.
      device_properties = model.DeviceProperties(parent=device_info)
      device_properties.device_info = device_info
      util.ConvertFromDict(device_properties, checkin['properties'])
      device_properties.put()
      logging.debug("Request App: "+device_properties.request_app)
 
      device_schedule = GetDeviceSchedule(device_properties)
      
      device_schedule_json = EncodeScheduleAsJson(device_schedule)
      logging.debug('Sending checkin response: %s', device_schedule_json)
      self.response.headers['Content-Type'] = 'application/json'
      self.response.out.write(device_schedule_json)
 
    except Exception, e:
      logging.error('Got exception during checkin: %s', e)
      self.response.headers['Content-Type'] = 'application/json'
      self.response.out.write(json.dumps([]))

  

def GetDeviceSchedule(device_properties):
  """Return entries from the global schedule that match this device."""

  matched = set()
#   its_devices=['UMnCBXxGBAhbbu.q4sqq7w', '6PjKR4Xo1.MyRAE28t.8YQ' , 'kmjRoKLPkokshmjn8OlUwA'] 
  
  
  if not device_properties.device_info:
    return matched
  
  schedule = model.Task.all()
  for task in schedule:
    if task.GetContext('appname')!=None and device_properties.country_code!=None:
        if task.GetContext('appname')==device_properties.request_app:
            if task.GetContext('country_code')==device_properties.country_code.lower() or task.GetContext('country_code')==None:
                matched.add(task)
        continue
    if device_properties.request_app=="MySpeedTest":
      continue
    if device_properties.request_app=="MPTCPController" or device_properties.request_app.replace(" ","")=="handovertracker":
      continue
    if not task.filter:
      try:
        app_version = float(device_properties.app_version[1:])
        if task.type != "tcpthroughput" or app_version > 2.0:
          matched.add(task)
      except:
        matched.add(task)
    else:
      # Does the filter match this device?
      devices = []
      # Match against DeviceProperties
      try:
        matching_device_properties = model.DeviceProperties.gql(
            'WHERE ' + task.filter)
        devices += [dp.device_info for dp in matching_device_properties]
      except db.BadQueryError:
        logging.warn('Bad filter expression %s', task.filter)

      # Match against DeviceInfo
      try:
        matching_device_info = model.DeviceInfo.gql(
            'WHERE ' + task.filter)
        devices += matching_device_info
      except db.BadQueryError:
        logging.warn('Bad filter expression %s', task.filter)

      for dev in devices:
        if dev and dev.id == device_properties.device_info.id:
          matched.add(task)

  # Un-assign all current tasks from this device
  for dt in device_properties.device_info.devicetask_set:
    dt.delete()

  if device_properties.request_app=="MPTCPController":
    return matched

  # Assign matched tasks to this device
  for task in matched:
    device_task = model.DeviceTask()
    device_task.task = task
    device_task.device_info = device_properties.device_info
    device_task.put()
  
#   app_version_num=0
#   if str(device_properties.app_version)[0].isdigit():
#       app_version_num=int(device_properties.app_version.replace('.',''))


#   for cdn_target in CDN_TARGETS:
#       ping_task=model.Task()
#       ping_task.user=users.get_current_user()
#       ping_task.created = datetime.utcnow()
#       ping_task.count=-1
#       ping_task.interval_sec=3600.0
#       ping_task.type="ping"
#       setattr(ping_task, 'mparam_target', cdn_target)
#       matched.add(ping_task)
  
   
  logging.debug(str(len(matched)))
  return matched



def EncodeScheduleAsJson(schedule):
  """Given a list of Tasks, return a JSON string encoding the schedule."""
  output = []
  for task in schedule:
    # Don't send the user, tag, or filter fields with the schedule
    output_task = util.ConvertToDict(
        task, exclude_fields=['user', 'tag', 'filter'])
    # Need to add the parameters and key fields
    output_task['parameters'] = task.Params()
    try:
        output_task['key'] = str(task.key().id_or_name())
    except db.NotSavedError:
        output_task['key'] = None
        
    output.append(output_task)

  return json.dumps(output)
