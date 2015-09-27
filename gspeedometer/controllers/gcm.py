from gspeedometer.model import DeviceInfo
__author__ = 'mdw@google.com (Matt Welsh)'

import logging

from django.utils import simplejson as json
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template
from gspeedometer import config
from gspeedometer.helpers import acl
from gspeedometer import model
from gspeedometer.helpers import error
from gspeedometer.helpers import util
from gspeedometer.controllers import measurement
from gspeedometer.controllers.measurement import MeasurementType
from django import forms
from django.utils.datastructures import SortedDict
from google.appengine.runtime import DeadlineExceededError
from google.appengine.api import memcache



from datetime import datetime, timedelta
import time

import urllib



GCM_SERVER = "https://android.googleapis.com/gcm/send"
API_KEY="AIzaSyAyTVKfc6AwrPd6RKY18r4eNWJy3LHpz7Q"



class GCM(webapp.RequestHandler):
  """GCM request handler."""

  def ActiveDevices(self, **unused_args):
#     if not acl.UserIsScheduleAdmin():
#         self.error(404)
#         return
#     devices=set()
#     query= model.DeviceProperties.all()
#     delta=datetime.utcnow() - timedelta(hours=24*30)
#     query.filter('timestamp >', delta)
#     temp_cursor = memcache.get('dev_cursor')
#     if temp_cursor:
#         query.with_cursor(start_cursor=temp_cursor)
#     result=""
#     try:
#         for m in query.run():
#             device_id=m.device_info.id
#             result=result+str(device_id)+'\n'
# #             devices.add(device_id) 
#     except DeadlineExceededError:
#         temp_cursor = query.cursor()
#         memcache.set('dev_cursor', temp_cursor)
#     
# #     result=""
# #     for d in devices:
# #         if d!=None:
# #             result=result+str(d)+'\n'
# #         
#     self.response.headers['Content-Type'] = 'text/plain'
#     self.response.out.write("ashkan "+result)

    q = db.GqlQuery("SELECT DISTINCT id FROM Measurement")
    num=q.count(limit=None)
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write(str(num))      
      
    
  
  def ListDevices(self, **unused_args):
    """Handler for gcm dashboard."""
    if not acl.UserIsScheduleAdmin():
        self.error(404)
        return
    
    devices=self._GetDeviceListByLastUpdateTime()
    result_str=""
    devices_list=list(devices)
    device_info_list=[]
    device_id_set=set()
    for device_property in devices_list:
        if not(device_property.device_info.id in device_id_set):
            device_id_set.add(device_property.device_info.id)
            device_info_list.append(device_property.device_info)
    
    
    device_info_list.sort(key=lambda dev: dev.LastUpdateTime())
    device_info_list.reverse()
    
    if (not self.request.POST.has_key('selectedType') or self.request.POST['type'] != self.request.POST['selectedType']):
        try:
            if self.request.POST.has_key('type'):
                thetype = self.request.POST['type']
                default_measurement = MeasurementType.GetMeasurement(thetype)
            else:
                default_measurement = MeasurementType.GetDefaultMeasurement()
        except RuntimeError, error:
            # occurs if someone specifies an invalid measurement type
            logging.warning('Type in POST is invalid: %s', error)
            self.error(501)
            return
        
        add_to_schedule_form = type('AddToScheduleForm', (forms.BaseForm,),
          {'base_fields': self._BuildFields(default_measurement)})()

    else:
        try:
            thetype = self.request.POST['type']
            measurement = MeasurementType.GetMeasurement(thetype)
        except:
            # occurs if someone specifies an invalid measurement type
            logging.warning('Type in POST is invalid: %s', error)
            self.error(501)
            return

        add_to_schedule_form = type(
            'AddToScheduleForm',
            (forms.BaseForm,),
            {'base_fields': self._BuildFields(measurement)})(self.request.POST)
        
        add_to_schedule_form.full_clean()
        if add_to_schedule_form.is_valid():
            params = dict()
            thetype = add_to_schedule_form.cleaned_data['type']
            # extract supported fields
            for field in measurement.field_to_description.keys():
              if ('location' in field) or ('profile' in field):
                continue  
              value = add_to_schedule_form.cleaned_data[field]
              if value:
                params[field] = value
            interval = add_to_schedule_form.cleaned_data['interval']
            gcm_devices=[]
            for k, v in self.request.POST.iteritems():
                if k=="selected_device" and v!='None':
                    gcm_devices.append(v)

            task = model.Task()            
            # logging.debug(str(add_to_schedule_form.cleaned_data))
            if  'tag' in add_to_schedule_form.cleaned_data:
                task.tag = add_to_schedule_form.cleaned_data['tag']
                
            if  'filter' in add_to_schedule_form.cleaned_data:
                task.filter = add_to_schedule_form.cleaned_data['filter']
                
            if  'count' in add_to_schedule_form.cleaned_data:
                task.count = add_to_schedule_form.cleaned_data['count']
                
            if  'interval' in add_to_schedule_form.cleaned_data:
                task.interval_sec = float(add_to_schedule_form.cleaned_data['interval'])

            if  'priority' in add_to_schedule_form.cleaned_data:
                task.priority = add_to_schedule_form.cleaned_data['priority']

            
            # interval = add_to_schedule_form.cleaned_data['interval'] or 3600
            # priority = add_to_schedule_form.cleaned_data['priority'] or None
            # p1 = add_to_schedule_form.cleaned_data['profile_1_freq']
            # p2 = add_to_schedule_form.cleaned_data['profile_2_freq']
            # p3 = add_to_schedule_form.cleaned_data['profile_3_freq']
            # p4 = add_to_schedule_form.cleaned_data['profile_4_freq']
        

            task.created = datetime.utcnow()
            task.user = users.get_current_user()
            task.type = thetype
            # if tag:
            #     task.tag = tag
            # if thefilter:
            #     task.filter = thefilter
            # task.count = count
            # task.interval_sec = float(interval)
            # task.priority = priority

            # Set up correct type-specific measurement parameters        
            for name, value in params.items():
                setattr(task, 'mparam_' + name, value)
            
            self._SendMessage(gcm_devices,task)
        
    template_args = {
        'devices': device_info_list,
        'user': users.get_current_user().email(),
        'logout_link': users.create_logout_url('/'),
        'add_form': add_to_schedule_form}
        
    self.response.out.write(template.render(
            'templates/gcm.html', template_args))

  def PostGCMMeasurement(self, **unused_args):
    """Handler used to post a measurement from a device."""
    if self.request.method.lower() != 'post':
      raise error.BadRequest('Not a POST request.')

    try:
      measurement_dict= json.loads(self.request.body)
      logging.debug('PostMeasurement: Got this GCM measurement:'+str(measurement_dict) )
      
      # for measurement_dict in measurement_list:
      # Change device id such that it is anonymized, but preserve the TAC.
      measurement_dict['tac'] = util.GetTypeAllocationCode(measurement_dict['device_id'])
      measurement_dict['device_id'] = util.HashDeviceId(measurement_dict['device_id'])
      
      device_info = model.DeviceInfo.get_or_insert(measurement_dict['device_id'])
      
      # Write new device properties, if present
      if 'properties' in measurement_dict:
        device_properties = model.DeviceProperties(parent=device_info)
        device_properties.device_info = device_info
        properties_dict = measurement_dict['properties']
        util.ConvertFromDict(device_properties, properties_dict)
        # Don't want the embedded properties in the Measurement object
        del measurement_dict['properties']
      else:
        # Get most recent device properties
        device_properties = device.GetLatestDeviceProperties(device_info, create_new_if_none=True)
      device_properties.put()
        
      if 'context_results' in measurement_dict:
        del measurement_dict['context_results']

      if ('parameters' in measurement_dict) and ('parameters' in measurement_dict['parameters']):
        del measurement_dict['parameters']['parameters']
      measurement = model.Measurement(parent=device_info)
      util.ConvertFromDict(measurement, measurement_dict)
      measurement.device_properties = device_properties
      measurement.put()
      
      gcm_measurement = model.GCMMeasurement()
      gcm_measurement.measurement=measurement
      gcm_measurement.device_id=device_info.id
      gcm_measurement.put()
            
    except Exception, e:
      logging.exception('Got exception posting measurements')

    logging.info('PostMeasurement: Done processing measurements')
    response = {'success': True}
    self.response.headers['Content-Type'] = 'application/json'
    self.response.out.write(json.dumps(response))

  def GetGCMResults(self, **unused_args):
    device_id = self.request.get('device_id')
    logging.debug(str(device_id))
    query= model.GCMMeasurement.all()
    query.filter("timestamp >", datetime.now() - timedelta(minutes=30))
    query.filter("device_id =", device_id)
    gcm_list=[]
    for gcm_measurement in query.run():
        mdict={}
        mdict['timestamp']=util.TimeToString(gcm_measurement.timestamp)
        mdict['type']=gcm_measurement.measurement.type
        mdict['success']=gcm_measurement.measurement.success
        mdict['values']=gcm_measurement.measurement.Values()
        mdict['params']=gcm_measurement.measurement.Params()
        if 'context_results' in mdict['values']:
            del mdict['values']['context_results']
        gcm_list.append(mdict)
    self.response.out.write(json.dumps(gcm_list))
    self.response.headers['Content-Type'] = 'application/json' 
    # self.response.headers['Content-Type'] = 'text/plain'

  def _SendMessage(self, devices_list, task):
      
    # Don't send the user, tag, or filter fields with the schedule
    output_task = util.ConvertToDict(task, exclude_fields=['user', 'tag', 'filter'])
    # Need to add the parameters and key fields
    output_task['parameters'] = task.Params()
    try:
        output_task['key'] = str(task.key().id_or_name())
    except db.NotSavedError:
        output_task['key'] = None
        
    logging.debug(str(json.dumps(output_task)))
    
    form_fields = {
      'registration_ids': devices_list,
      'data': {
      "task": json.dumps(output_task)
      }
    }
    
    # logging.debug(str(form_fields))
    result = urlfetch.fetch(url=GCM_SERVER,
    payload=json.dumps(form_fields),
    method=urlfetch.POST,
    headers={'Content-Type': 'application/json', 'Authorization': "key="+API_KEY})
    logging.warning(str(result.content))
    # self.response.headers['Content-Type'] = 'text/plain'
    # self.response.out.write(str(result.content))

    
    
  def _GetDeviceListByLastUpdateTime(self, cursor=None):
    version = self.request.get('version')  
    query = model.DeviceProperties.all()
    query.filter("app_version =", str(version) )#TODO
    delta=datetime.utcnow() - timedelta(hours=4)
    query.filter('timestamp >', delta)
    result=query.run()#TODO with more number of users, run() does not work
    return result

  def _BuildFields(self, mymeasurement=
                   MeasurementType.GetDefaultMeasurement()):
    """Builds the ordered set of fields to display in the form for the 
    specified measurement type.
       
    Args:
      measurement: A MeasurementType object.
      
    Returns:
      A sorted dict of field name to form field.
    """
    fields = SortedDict()
    fields['type'] = forms.ChoiceField(
        measurement.MEASUREMENT_TYPES,
        initial=mymeasurement.kind,
        widget=forms.Select(attrs={'onchange': 'this.form.submit();'}))

    for field, text in mymeasurement.field_to_description.iteritems():
      if (not ('profile' in str(field))) and  (not ('location' in str(field))):
          fields[field] = forms.CharField(required=False, label=text)

    fields['count'] = forms.IntegerField(
       required=False, initial= -1, min_value= -1, max_value=1000)
    fields['interval'] = forms.IntegerField(
        required=True, label='Interval (sec)', min_value=1, initial=600)
#    fields['tag'] = forms.CharField(required=False)
    fields['selectedType'] = forms.CharField(
        initial=mymeasurement.kind, widget=forms.widgets.HiddenInput())
    return fields

    
