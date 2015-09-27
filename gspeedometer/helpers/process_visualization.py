# Copyright 2014 University of Michigan
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

"""Utility functions for the Mobiperf service."""

__author__ = 'sanae@umich.edu (Sanae Rosen)'

import logging
import datetime



def add_to_dict(key_from, key_to, data_from, data_to, target, d=False):
    if key_from in data_from:
        val = float(data_from[key_from])
        data_to[target][key_to].append(val)
        if not d:    
            data_to["all"][key_to].append(val)

def initialize(mdict, item, name, labels):
    if not (name  in mdict):
        mdict[name] = {}
    try:  
        target = item.parameters.target
    except:
        target = "default" 

    tempdict=dict()
    for k in labels:
        tempdict[k]=[]
        
    if target not in mdict[name]:
        mdict[name][target] = tempdict
    if "all" not in mdict[name]:
        mdict[name]["all"] = tempdict

    return (mdict, target, item)

def add_ping(mdict, item):
    labels = ["mean", "max", "stdev", "packetloss"]
#     logging.debug(">>>>>1:"+str(mdict))
    (mdict, target, item) = initialize(mdict, item, "ping", labels)
#     logging.debug(">>>>>2:"+str(mdict)+" "+str(item.Values()))
    add_to_dict("mean_rtt_ms", "mean", item.Values(), mdict["ping"], target)
    add_to_dict("max_rtt_ms", "max", item.Values(), mdict["ping"], target)
    add_to_dict("stddev_rtt_ms", "stdev", item.Values(), mdict["ping"], target)
    add_to_dict("packet_loss", "packetloss", item.Values(), mdict["ping"], target)
#     logging.debug(">>>>>3:"+str(mdict))
    return mdict

def add_dns(mdict, item):
    labels = ["time"]
    (mdict, target, item) = initialize(mdict, item, "dns", labels)

    add_to_dict("time_ms", "time", item.Values(), mdict["dns"], target)
    return mdict

def add_http(mdict, item):
    labels = ["time", "avg_throughput"]
    (mdict, target, item) = initialize(mdict, item, "http", labels)
    add_to_dict("time_ms", "time", item.Values(), mdict["http"], target)

    if "time_ms" in item.Values() and "body_len" in item.Values():
        bodylen = float(item.Values()["body_len"])
        timelen = float(item.Values()["time_ms"])
        if timelen > 0:    
            mdict["http"]["all"]["avg_throughput"].append(bodylen/timelen)
            mdict["http"][target]["avg_throughput"].append(bodylen/timelen)
    return mdict

def add_traceroute(mdict, item):
    labels = ["num_hops", "avg_rtt", "first_hop"]
    (mdict, target, item) = initialize(mdict, item, "traceroute", labels)
#     logging.error("%%%%%%"+str(mdict))
    rtts = []
    failure = False
    for i in range(30):
        index = "hop_" + str(i) + "_rtt_ms"
        if index not in item.Values():
            break
        else:
            try:
                rtts.append(float(item.Values()[index].strip('"')))
            except:
                failure = True
                break
    if failure:
#         logging.debug("%%%%%% failure")
        return mdict

    mdict["traceroute"]["all"]["num_hops"].append(len(rtts))
    mdict["traceroute"][target]["num_hops"].append(len(rtts))

    if len(rtts) > 0:
        first_hop = float(item.Values()["hop_1_rtt_ms"].strip('"'))
        mdict["traceroute"]["all"]["first_hop"].append(first_hop)
        mdict["traceroute"][target]["first_hop"].append(first_hop)
        mdict["traceroute"]["all"]["avg_rtt"].append(sum(rtts)/len(rtts))
        mdict["traceroute"][target]["avg_rtt"].append(sum(rtts)/len(rtts))
    return mdict

def add_tcp(mdict, item):
    if "tcp" not in mdict:
        mdict["tcp"] = {}
#     if item["parameters"]["dir_up"] == True:
    if item.Params()["dir_up"] == True:
        dir_up = "Uplink"
    else:
        dir_up = "Downlink"
    if dir_up not in mdict["tcp"]:
        mdict["tcp"][dir_up] = {"throughput": []}
    if "tcp_speed_results" in item.Values():
        speed =  item.Values()["tcp_speed_results"]
        speed = speed[1:-1]
        speed = speed.split(",")
        if len(speed) > 0 and speed[0]:
            speed = [float(x) for x in speed]
            mdict["tcp"][dir_up]["throughput"].append(sum(speed)/len(speed))
    return mdict

def add_udp(mdict, item):
    if "udp" not in mdict:
        mdict["udp"] = {}
#     if item["parameters"]["dir_up"] == True:
    if item.Params()["dir_up"] == True:
        dir_up = "Uplink"
    else:
        dir_up = "Downlink"

    if dir_up not in mdict["udp"]:
        mdict["udp"][dir_up] = {"jitter": [], "outoforder": [], "loss_rate":[]}

    add_to_dict("jitter", "jitter", item.Values(), mdict["udp"], dir_up, True)
    add_to_dict("inversion_number", "outoforder", item.Values(), mdict["udp"], dir_up, True)
    add_to_dict("loss_rate", "loss_rate", item.Values(), mdict["udp"], dir_up, True)
    return mdict


def get_metadata(device_properties, location_precision, clusters):
    mdict = {}
    #device_properties = item["device_properties"].device_info
    latitude = (device_properties.location.lat * \
            location_precision)/ float(location_precision)
    longitude = (device_properties.location.lon * \
            location_precision)/ float(location_precision)

    mdict["lat"] = latitude
    mdict["lng"] = longitude

    cluster_key = str(latitude).split(".")[0] + str(longitude).split(".")[0]
    if cluster_key not in clusters:
        cluster_index = len(clusters.keys()) + 1
        clusters[cluster_key] = cluster_index
    mdict["clu"] = clusters[cluster_key]

    if latitude== 0 and longitude == 0:
       return None 
    mdict["wk"] = 1 
    mdict["car"] = str(device_properties.carrier.lower().strip())
    if len(mdict["car"]) == 0:
       return None 
    mdict["ct"] = 0
    mdict["net"] = str(device_properties.network_type.lower())
    if (mdict["net"] == "wifi" or mdict["net"] == "unknown") and False: # XXX
       return None 
    if "unrecognized" in mdict["net"]:
        mdict["net"] = "hspa+"
    return mdict

def finalize_datatype(v, labels, name):
    if not (name in v and len(v[name]) > 0):
        return
#     logging.debug(str(v.keys())+" "+str(labels)+" "+str(name))
#     logging.error(str(v[name].keys()))
    for target, value in v[name].iteritems():
        data = v[name][target]
#         logging.error("-----"+str(target)+"-----"+str(data.keys()))
#         logging.debug(">>>>>"+str(v[name][target])+" "+str(labels[0]))
#         logging.debug("<<<<<"+str(labels))
#         for label in labels:
#             if type(data[label]) is int:
#                 l=[]
#                 l.append(data[label])
#                 data[label]=l
        
        if labels[0] in data.keys():
#             logging.debug(str(data[labels[0]]))
#             logging.debug(str(type(data[labels[0]])))
            if not (type(data[labels[0]]) is list):
                data["ct"]=1
            else:
                data["ct"] = len(data[labels[0]])
        for label in labels:
            if not (label in data.keys()):
                continue
#             logging.debug(">>> "+label+" " +str(data[label]))
            if type(data[label]) is list:
                if len(data[label]) > 0:
                    data[label] = sum(data[label])/len(data[label])
                else:
                    del data[label]
    v[name] = dict((k, v2) for k, v2 in v[name].iteritems() if "ct" in v2 and v2["ct"] != 0)
    if len(v[name]) == 0:
        del v[name]


def MeasurementListToVisualization(cursor, location_precision):
    logging.getLogger().setLevel(logging.DEBUG)
#     logging.error("MeasurementListToVisualization: "+str(len(cursor)))
    cluster_index = 0
    clusters = {}
    final_data = {}
    for measurement in cursor:
        if measurement.GetParam('ping')!=None and measurement.GetParam('ping').replace('"','')=='information':
            continue
        if measurement.success==False:
            continue

        """ First, get the keys """
        item = measurement.device_properties
        mdict = get_metadata(item, location_precision, clusters)
        if mdict == None:
            continue

        dict_key = [str(x) for x in mdict.values()]
        dict_key = "_".join(dict_key)

#         logging.debug("dict_key: "+str(dict_key))
#         logging.debug("mdict: "+str(mdict))

        if not (dict_key  in final_data.keys()):
            final_data[dict_key] = mdict
#             logging.debug("**** mdict: "+str(final_data[dict_key])) 
        else:
            mdict = final_data[dict_key]
#             logging.debug("#### mdict: "+str(mdict))

        data_type = measurement.type 

#         logging.error(data_type + "!!!!!!!!!!!!!!!!!!!!")
        

        if data_type == "ping":
            mdict = add_ping(mdict, measurement)
        elif data_type == "dns_lookup":
            mdict = add_dns(mdict, measurement)
        elif data_type == "tcpthroughput":
            mdict = add_tcp(mdict, measurement)
        elif data_type == "udp_burst":
            mdict = add_udp(mdict, measurement)
        elif data_type == "http":
            mdict = add_http(mdict, measurement)
        elif data_type == "traceroute":
            mdict = add_traceroute(mdict, measurement)
        else:
            continue
        
#         logging.debug("!!!!!!!!!!!!!!!!!!!! "+str(mdict))

        final_data[dict_key] = mdict
#         logging.error("??????? "+str(mdict) )
#         logging.error(">>>>>>>>>> "+str(final_data) )

    retval = []
    for k, v in final_data.iteritems():
        labels = ["mean", "max", "stdev", "packetloss"]
        finalize_datatype(v, labels, "ping")
        labels = ["time"]
        finalize_datatype(v, labels, "dns")
        labels = ["time", "avg_throughput"]
        finalize_datatype(v, labels, "http")
        labels = ["num_hops", "avg_rtt", "first_hop"]
        finalize_datatype(v, labels, "traceroute")
        labels = ["throughput"]
        finalize_datatype(v, labels, "throughput")
        labels = ["jitter", "outoforder", "loss_rate"]
        finalize_datatype(v, labels, "udp")
        retval.append(v)
#     logging.error("final data: "+str(retval))
    return retval 

