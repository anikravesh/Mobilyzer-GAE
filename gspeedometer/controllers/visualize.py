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

"""Anonymized data visualization"""

__author__ = 'sanae@umich.edu (Sanae Rosen)' 

import logging
import datetime

from django.utils import simplejson as json
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from gspeedometer.helpers import process_visualization 
from gspeedometer import model
from gspeedometer import config
from gspeedometer.helpers import acl
from django.utils import simplejson as json
from StringIO import StringIO
from time import sleep
# from google.appengine.api import memcache
# from django.utils import simplejson as json
# import pickle

class Visualize(webapp.RequestHandler):

    def Visualize(self, **unused_args):
        template_args = {"data": str(self.get_data()).replace("u'","'")}
        self.response.out.write(template.render(
                'templates/visualization.html', template_args))

    def UpdateVisualizationData(self, **unused_args):

        now=datetime.datetime.now()
#         query=model.Measurement.all()
#         query.filter('timestamp >=', now - datetime.timedelta(hours=48))
#         query.filter('type IN', ['ping', 'tcpthroughput'])
#         measurements=query.fetch(5000)#16000
#         



        measurement_list=[]
        batch_size = 1000
        start_cursor = None
        while True:
            query = self._make_query(now,start_cursor)
            results_fetched = 0
            exit_flag=True
            for m in query:
                results_fetched=results_fetched+1
                measurement_list.append(m)
                if results_fetched == batch_size:
                    logging.debug(str(len(measurement_list)))
                    if len(measurement_list)==14000:
                        exit_flag=True
                        break
                    start_cursor = query.cursor()
                    exit_flag=False
                    break
            if exit_flag:
                break
            sleep(5)


        location_precision = config.ANONYMIZE_LOCATION_PRECISION * 10
        results_dict=process_visualization.MeasurementListToVisualization(measurement_list, location_precision)
        results_json=json.dumps(results_dict)
        
        
        db.delete(model.RecentMeasurement.all())
        recent_measurement=model.RecentMeasurement()
        recent_measurement.data=results_json
        recent_measurement.put()
        
    def _make_query(self, now, start_cursor):
        query=model.Measurement.all()
        query.filter('timestamp >=', now - datetime.timedelta(hours=48))
        query.fetch(18000)
#         query.filter('type IN', ["ping","tcpthroughput"])
        if start_cursor:
            query.with_cursor(start_cursor)
        return query
    
    def get_data(self):
        result_obj=model.RecentMeasurement.all().get()
        if result_obj!=None:
            io = StringIO(result_obj.data)
            data=json.load(io)
#             logging.debug(">>> "+str(type(data))+" "+str(data))
            return data
#         start = datetime.datetime.now() - datetime.timedelta(hours=5)
#         end = datetime.datetime.now()

#         q = model.RecentMeasurement.all()
#         measurements=[]
#         for rm in q.run():
#             measurements.append(rm.measurement)
        
        #measurement_q.filter('timestamp <', end)

#         location_precision = config.ANONYMIZE_LOCATION_PRECISION * 10
        
#         return process_visualization.MeasurementListToVisualization(measurements, location_precision)
        
        
    
    

