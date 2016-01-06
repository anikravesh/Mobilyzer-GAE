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

"""Controller to manage manipulation of measurement schedules."""

__author__ = ('mdw@google.com (Matt Welsh), '
              'drchoffnes@gmail.com (David Choffnes)')

import datetime
import logging

from django import forms
from django.utils.datastructures import SortedDict
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from gspeedometer import model
from gspeedometer.controllers import measurement
from gspeedometer.controllers.measurement import MeasurementType
from gspeedometer.helpers import acl

class Schedule(webapp.RequestHandler):
  """Measurement request handler."""

  def Add(self, **unused_args):
    """Add a task to the schedule."""

    if not acl.UserIsScheduleAdmin():
      self.error(404)
      return

    # new request or type changed, so show a blank form
    if (not self.request.POST.has_key('selectedType') or
        self.request.POST['type'] != self.request.POST['selectedType']):

      # assume new request, update type if otherwise      
      try:
        if self.request.POST.has_key('type'):
          thetype = self.request.POST['type']
          measurement = MeasurementType.GetMeasurement(thetype)
        else:
          measurement = MeasurementType.GetDefaultMeasurement()
      except RuntimeError, error:
        # occurs if someone specifies an invalid measurement type
        logging.warning('Type in POST is invalid: %s', error)
        self.error(501)
        return
      
      # dynamically creates a form based on the specified fields
      add_to_schedule_form = type(
          'AddToScheduleForm', (forms.BaseForm,),
          {'base_fields': self._BuildFields(measurement)})()

    else:
      # data was submitted for a new measurement schedule item
      try:
        thetype = self.request.POST['type']
        measurement = MeasurementType.GetMeasurement(thetype)
      except:
        # occurs if someone specifies an invalid measurement type
        logging.warning('Type in POST is invalid: %s', error)
        self.error(501)
        return

      # build completed form dynamically from POST and fields
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
          value = add_to_schedule_form.cleaned_data[field]
          if value:
            params[field] = value
        tag = add_to_schedule_form.cleaned_data['tag']
        thefilter = add_to_schedule_form.cleaned_data['filter']
        count = add_to_schedule_form.cleaned_data['count'] or -1
        interval = add_to_schedule_form.cleaned_data['interval']
        priority = add_to_schedule_form.cleaned_data['priority']
        p1 = add_to_schedule_form.cleaned_data['profile_1_freq']
        p2 = add_to_schedule_form.cleaned_data['profile_2_freq']
        p3 = add_to_schedule_form.cleaned_data['profile_3_freq']
        p4 = add_to_schedule_form.cleaned_data['profile_4_freq']

        logging.info('Got TYPE: ' + thetype)

        task = model.Task()
        task.created = datetime.datetime.utcnow()
        task.user = users.get_current_user()
        task.type = thetype
        if tag:
          task.tag = tag
        if thefilter:
          task.filter = thefilter
        task.count = count
        task.interval_sec = float(interval)
        task.priority = priority

        # Set up correct type-specific measurement parameters        
        for name, value in params.items():
          setattr(task, 'mparam_' + name, value)
        task.put()

    schedule = model.Task.all()
    schedule.order('-created')

    template_args = {
        'user_schedule_admin': acl.UserIsScheduleAdmin(),
        'add_form': add_to_schedule_form,
        'schedule': schedule,
        'user': users.get_current_user().email(),
        'logout_link': users.create_logout_url('/')
    }
    self.response.out.write(template.render(
        'templates/schedule.html', template_args))

  def Delete(self, **unused_args):
    """Delete a task from the schedule."""
    if not acl.UserIsScheduleAdmin():
      self.error(404)
      return

    errormsg = None
    message = None
    add_to_schedule_form = type('AddToScheduleForm', (forms.BaseForm,),
                                {'base_fields': self._BuildFields()})()

    task_id = self.request.get('id')
    task = model.Task.get_by_id(int(task_id))
    if not task:
      errormsg = 'Task %s does not exist' % task_id
    else:
      # TODO(mdw): Do we need to wrap the following in a transaction?
      # First DeviceTasks that refer to this one
      device_tasks = model.DeviceTask.all()
      device_tasks.filter('task =', task)
      for dt in device_tasks:
        dt.delete()

      # Now delete the task itself
      task.delete()
      message = 'Task %s deleted' % task_id

    schedule = model.Task.all()
    schedule.order('-created')

    template_args = {
        'user_schedule_admin': acl.UserIsScheduleAdmin(),
        'add_form': add_to_schedule_form,
        'message': message,
        'error': errormsg,
        'schedule': schedule,
        'user': users.get_current_user().email(),
        'logout_link': users.create_logout_url('/')
    }
    self.response.out.write(template.render(
        'templates/schedule.html', template_args))

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
      fields[field] = forms.CharField(required=False, label=text)

    fields['count'] = forms.IntegerField(
       required=False, initial= -1, min_value= -1, max_value=1000)
    fields['interval'] = forms.IntegerField(
        required=True, label='Interval (sec)', min_value=1, initial=600)
    fields['tag'] = forms.CharField(required=False)
    fields['filter'] = forms.CharField(required=False)
    fields['priority'] = forms.IntegerField(
        required=False, label='Priority (larger is higher)', min_value=1)
    fields['selectedType'] = forms.CharField(
        initial=mymeasurement.kind, widget=forms.widgets.HiddenInput())
    return fields


  def UploadTasks(self, **unused_args):
    user = users.get_current_user()
    logging.error("user: "+str(user))
    if not str(user) in ['ashnik@umich.edu','ashkannikravesh', 'shahifaqeer', 'zmao@umich.edu', 'morley', 'xsc@umich.edu', 'feamster', 'drchoffnes', 'glex.qsd']:
        self.error(404)
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write("Not Authenticated!")
        return

    errormsg=None;
    message=None;
    try:
        if self.request.method.lower()=='post' and self.request.get('tasks_file'):
            f = self.request.POST.get('tasks_file')
            content=f.file.read()
            filename=f.filename
            tasks=content.split('\n')
            tasks=filter(lambda x: x != '', tasks)
            logging.debug(str(len(tasks))+" "+str(tasks))
            if len(tasks)==0:
                raise ValueError('Error parsing file')
            new_tasks=[]
            for task in tasks:
                items=task.strip().split(',')
                logging.debug(str(len(items))+" "+str(items))
                if len(items)!=8:
                    raise ValueError('Error parsing file')
                measurement_type=items[0].strip()
#                 logging.debug("measurement_type: "+measurement_type)
                if not measurement_type in ['ping', 'traceroute', 'dns', 'http']:
                    raise ValueError('Error parsing file: invalid measurement type. Supported measurement types are traceroute, ping, http, and dns')
                if measurement_type=='dns':
                    measurement_type='dns_lookup'
                count=int(items[1].strip())
                interval_sec=float(items[2].strip())
                target=items[3].strip()
                app_name=items[4].strip()
                carrier=items[5].strip()
                country_code=items[6].strip().lower()
                sensitive=items[7].lower()
                t=model.Task()
                t.type=measurement_type
                t.interval_sec=interval_sec
                t.count=count
                t.user=users.get_current_user()
                if measurement_type in ['ping',  'dns', 'traceroute']:
                    setattr(t, 'mparam_target', target)
                elif measurement_type in ['http']:
                    setattr(t, 'mparam_url', target)
                setattr(t, 'mparam_sensitive', sensitive)
                setattr(t, 'mcontext_appname', app_name)
                if carrier!="*":
                    setattr(t, 'mcontext_carrier', carrier)
                if country_code!="*":
                    setattr(t, 'mcontext_country_code', country_code)
                new_tasks.append(t)
            
            all_tasks=model.Task.all()
            for old in all_tasks:
                if str(old.GetContext('appname')).strip()==str("MySpeedTest"):
                    old.delete() 
            for new in new_tasks:
                new.put()
            message="Successfully scheduled %d tasks from %s" % (len(new_tasks),filename) 
        elif self.request.method.lower()=='post':
            raise ValueError('Error uploading file: please choose a file')
    except ValueError ,err:
        errormsg=err.message
    
    template_args = {
        'message': message,
        'error': errormsg,
        'user': users.get_current_user().email(),
        'logout_link': users.create_logout_url('/')
      }
    self.response.out.write(template.render(
          'templates/uploadtasks.html', template_args))

      