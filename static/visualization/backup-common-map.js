
var map;
var heatmap;
var hcmap;
var clustermapelements = [];

var uniq_carr;
var uniq_net;
var maxrtt = 0;
var def_radius = 15;

var dropdownsinitialized = false;

// TODO real values
var green_thres = {
    "rtt": 100,
    "rtt_packetloss": 0.005,
    "throughput":10000,
    "ping_mean":100,
    "ping_worst":100,
    "ping_stdev":30,
    "ping_loss":0.005,
    "trace_first":50,
    "trace_avg":100,
    "trace_num":7,
    "dns_rtt":100,
    "http_time":300,
    "http_throughput":500,
    "tcp_throughput":10000,
    "udp_jitter":1,
    "udp_outoforder":1,
    "udp_lossrate":0.005
}

var yellow_thres = {
    "rtt": 200,
    "rtt_packetloss": 0.01,
    "throughput":5000,
    "ping_mean":200,
    "ping_worst":200,
    "ping_stdev":70,
    "ping_loss":0.01,
    "trace_first":100,
    "trace_avg":200,
    "trace_num":15,
    "dns_rtt":200,
    "http_time":800,
    "http_throughput":250,
    "tcp_throughput":5000,
    "udp_jitter":5,
    "udp_outoforder":3,
    "udp_lossrate":0.01
}

var orange_thres = {
    "rtt": 300,
    "rtt_packetloss": 0.05,
    "throughput":500,
    "ping_mean":300,
    "ping_worst":400,
    "ping_stdev":100,
    "ping_loss":0.05,
    "trace_first":150,
    "trace_avg":300,
    "trace_num":30,
    "dns_rtt":300,
    "http_time":1000,
    "http_throughput":100,
    "tcp_throughput":500,
    "udp_jitter":10,
    "udp_outoforder":7,
    "udp_lossrate":0.05
}

function toggleAdvanced() {
    var simple = document.getElementById("simplechooserform");
    var complex = document.getElementById("complexchooserform");
    if (simple.style.display === 'none') {
        complex.style.display = 'none';
        simple.style.display = '';
    } else {
        simple.style.display = 'none';
        complex.style.display = '';
    }
}

function toggleAdvancedPane(itemname) {
    var item = document.getElementById(itemname);
    var panes = ["advanced_ping", "advanced_tr", "advanced_dns", "advanced_tcp", "advanced_udp", "advanced_http"];
    if (item.style.display === 'none') {
        for (var i=0; i < panes.length; i++) {
                pane = document.getElementById(panes[i]);
                pane.style.display = 'none';
        }
        item.style.display = '';
    } else {
        item.style.display = "none";
    }
}

var dropdowns = {"pingdropdown":"ping", "trdropdown":"traceroute", "dnsdropdown":"dns" , "httpdropdown":"http", "tcpdropdown":"tcp", "udpdropdown":"udp"}
var dropdownreverse = {"ping":"pingdropdown", "traceroute":"trdropdown", "dns":"dnsdropdown" , "http":"httpdropdown", "tcp":"tcpdropdown", "udp":"udpdropdown"}

var network_lte = ["lte"]
var network_4g = ["mobile: 4g", "hspa+", "ehrpd", "lte"]
var network_3g = ["mobile: 3g", "1xrtt", "hsdpa", "hspa", "evdo_a", "evdo_b", "umts"];
var network_2g = ["mobile: 2g", "edge", "gprs"]

// TODO
// Toggle all carriers
// Sort carriers alphabetically

Date.prototype.getWeek = function() {
    var onejan = new Date(this.getFullYear(),0,1);
    return Math.ceil((((this - onejan) / 86400000) + onejan.getDay()+1)/7);
}

function filter()
{
    $('#loading').show();

        //Reset current clustermap
        hcmap.reset();

    var dateValues = $("#dateslider").dateRangeSlider("values");
    var minwk = dateValues.min.getWeek();
    var maxwk = dateValues.max.getWeek();

    filtered_data1 = jQuery.grep(data, function(elem, idx){
        if(elem.clu == null || elem.car == "" || elem.car == "roamingindicatoroff" || elem.car == "searchingforservice") {
            return false;
        }
        //for (aelem in uniq_area) {
                for (var i=0; i<uniq_area.length; i++) {
            //if((!($('#cb_ar_'+uniq_area[aelem]).is(':checked'))) && (elem.ar == uniq_area[aelem]))
            if((!($('#cb_ar_'+uniq_area[i]).is(':checked'))) && (elem.ar == uniq_area[i]))
                return false;
        }
        //for (aelem in uniq_carr) {
                for (var i=0; i<uniq_carr.length; i++) {
            //if((!($('#cb_car_'+uniq_carr[aelem]).is(':checked'))) && (elem.car == uniq_carr[aelem]))
            if((!($('#cb_car_'+uniq_carr[i]).is(':checked'))) && (elem.car == uniq_carr[i]))
                return false;
        }
        //for (aelem in uniq_net) {
                for (var i=0; i<uniq_net.length; i++) {
            //if((!($('#cb_net_'+uniq_net[aelem]).is(':checked'))) && (elem.net == uniq_net[aelem]))
            if((!($('#cb_net_'+uniq_net[i]).is(':checked'))) && (elem.net == uniq_net[i]))
                return false;
        }
        if(elem.wk < minwk || elem.wk > maxwk)
            return false;
        return true;
    });
    filtered_data = jQuery.extend(true, [],  filtered_data1);
    var totalct = 0;

    filtered_data.forEach(function(elem, idx, arr){
                //elem.count = elem.rtt;
                totalct += elem.ct;
                //delete elem.rtt;
                delete elem.clu;
                delete elem.wk;
                delete elem.car;
                delete elem.ar;
                delete elem.net;
                //delete elem.ct;
    })
    $("#stats").html('')
    $("#stats").append(totalct + ' measurements')

    $('#loading').hide();
        clustermapelements = [];
        //console.log("Filtered points:"+filtered_data.length);
        for (var i = 0; i < filtered_data.length; i++) {
            elem = filtered_data[i];
            var count = elem["ct"];
            //var avg_rtt = elem["rtt"];

            var avg_rtt = elem[data_chosen];

            // For clustermap
            var color;
            if (data_chosen.indexOf("throughput") > -1){
                console.log(avg_rtt);
                if (avg_rtt>=green_thres[data_chosen]) {
                    color='green'
                }
                else if (avg_rtt<green_thres[data_chosen] && avg_rtt>=yellow_thres[data_chosen]) {
                    color='yellow'
                }
                else if (avg_rtt<yellow_thres[data_chosen] && avg_rtt>=orange_thres[data_chosen]) {
                    color='orange'
                }
                else{
                    color='red'
                }
            } else {
                if (avg_rtt<=green_thres[data_chosen]) {
                    color='green'
                }
                else if (avg_rtt>green_thres[data_chosen] && avg_rtt<=yellow_thres[data_chosen]) {
                    color='yellow'
                }
                else if (avg_rtt>yellow_thres[data_chosen] && avg_rtt<=orange_thres[data_chosen]) {
                    color='orange'
                }
                else{
                    color='red'
                }
            }
            c = {}
            //c[color]=1
            c[color]=elem.ct;
            clustermapelements.push({
                'label': 'X',
                'coordinates': {'lat': elem["lat"], 'lng': elem["lng"]},
                'description': Math.round(avg_rtt).toString()+"ms", // ("+count.toString()+" measurements)",
                'color': c,
                'count': count
            });
        }
        hcmap = new clustermap.HCMap ({'map': map , 'elements': clustermapelements}) ;
}

function get_unique(array, objname)
{
    var dups={}
    var uniq=[]
    array.forEach(function(elem,idx,arr){
        if(!dups[elem[objname]]) {
            dups[elem[objname]]=true;
            uniq.push(elem[objname])
        }
    });
    return uniq;
}

window.onload = createVisualization;


function createVisualization(){

    var data_chosen;
    var radio;
    var target;

    // Find the data type we are analyzing
    if (document.getElementById("complexchooserform").style.display === '') { 
        var panes = ["advanced_ping", "advanced_tr", "advanced_dns", "advanced_tcp", "advanced_udp", "advanced_http"];
        var pane_mapping = {"advanced_ping": "datatype_ping", "advanced_tr": "datatype_tr", "advanced_dns": "datatype_dns", "advanced_tcp": "datatype_tcp", "advanced_udp": "datatype_udp", "advanced_http":"datatype_http"};
        for (var i=0; i < panes.length; i++) {
            pane = document.getElementById(panes[i])
            if (pane != null && pane.style.display === '') {
                radio = document.getElementsByName(pane_mapping[panes[i]]);
                break;
            }
        }
    }

    if (typeof radio === 'undefined') {
        
        radio = document.getElementsByName("datatype");
    }

    for (var val in radio) {
        if (radio[val].checked) {
            data_chosen = radio[val].value;
            if (data_chosen === "throughput") {
                target = "Downlink";
            } else if (data_chosen ==="rtt" || data_chosen ==="rtt_packetloss") {
                target = "all";
            }

        }
    }

    var string_to_category = {"rtt":"ping", "rtt_packetloss":"ping", "throughput":"tcp", "ping_mean":"ping", "ping_worst":"ping", "ping_stdev":"ping", "ping_loss":"ping", "trace_first":"traceroute", "trace_avg":"traceroute", "trace_num":"traceroute", "dns_rtt":"dns", "http_time":"http", "http_throughput":"http", "tcp_throughput":"tcp", "udp_jitter":"udp", "udp_outoforder":"udp", "udp_lossrate":"udp"}
    var string_to_datatype= {"rtt":"mean", "rtt_packetloss":"packetloss", "throughput":"throughput", "ping_mean":"mean", "ping_worst":"max", "ping_stdev":"stdev", "ping_loss":"packetloss", "trace_first":"first_hop", "trace_avg":"avg_rtt", "trace_num":"num_hops", "dns_rtt":"time", "http_time":"time", "http_throughput":"avg_throughput", "tcp_throughput":"throughput", "udp_jitter":"jitter", "udp_outoforder":"outoforder", "udp_lossrate":"loss_rate"}

    var category = string_to_category[data_chosen];
    var data_chosen_type = string_to_datatype[data_chosen];

    if (typeof target === 'undefined') {
        var dropdownname = dropdownreverse[category];
        var e = document.getElementById(dropdownname);
        target = e.options[e.selectedIndex].value;
    }
    //Clean up data
    filtered_data1 = jQuery.grep(data, function(elem, idx){
        return(elem.clu != null && elem.car != "" && elem.car != "roamingindicatoroff" && elem.car != "searchingforservice");
    });
    filtered_data = jQuery.extend(true, [],  filtered_data1);

  /**********************************************************************
        Generate form fields
     *********************************************************************/

    // TODO break carriers down by region
    // TODO set all parameters for targets

    //List all carriers
    $("#carrier").html('')
    uniq_carr = get_unique(filtered_data, "car")
    uniq_carr.sort();
    uniq_carr.forEach(function(elem,idx,arr){
        $("#carrier").append('<input type="checkbox" onchange="filter()" name="cb_car" id="cb_car_' + elem+'" checked>'+ elem + '</input><br/>')
    });
    
    //List all network types
    $("#network").html('')
    uniq_net = get_unique(filtered_data, "net")
    uniq_net.forEach(function(elem,idx,arr){
        $("#network").append('<input type="checkbox" onchange="filter()" id="cb_net_' + elem+'" checked>'+ elem + '</input><br/>')
    });

    //Set defaults
    $("#cb_net_wifi").attr('checked', false);
    filtered_data = jQuery.grep(filtered_data, function(elem, idx){
        return(elem.net != "wifi---");// XXX
    });
    // Fill in the drop-down menus
    if (!dropdownsinitialized) {
        var dropdownelements = {"ping":{}, "traceroute":{}, "dns":{}, "http":{}, "tcp":{}, "udp":{}}
        for (var i = 0; i < filtered_data.length; i++) {
            elem = filtered_data[i];
            for (var key in elem) {
                if (key in dropdownelements){
                    for (var key2 in elem[key]) {
                        if (!(key2 in dropdownelements[key])) {
                            dropdownelements[key][key2] = true;
                        }
                    }
                }
            }
        }

        for (var key in dropdowns) {
            var dropdown = document.getElementById(key);
            for (var key2 in dropdownelements[dropdowns[key]]) {
                var option = document.createElement("option");
                option.text = key2;
                option.value = key2;
                if (key2 == "all") {
                    option.defaultSelected = true;
                }
                if (key2 == "Downlink") {
                    option.defaultSelected = true;
                }
                dropdown.appendChild(option);
            }
        }
        dropdownsinitialized = true;
    }


  generateMap(filtered_data, data_chosen_type, category, data_chosen, target)
};

function generateMap(filtered_data, data_chosen, category, data_name, target) {

  /**********************************************************************
        Prepare data for loading
     *********************************************************************/

    var totalct = 0;
        //console.log("Filtered points:"+filtered_data.length);
    filtered_data.forEach(function(elem, idx, arr){

        if(elem[data_chosen] > maxrtt)
            maxrtt = elem[data_chosen];
        //elem.count = elem.rtt;
        totalct += elem.ct;
        //delete elem.rtt;
        delete elem.clu;
        delete elem.wk;
        delete elem.car;
        delete elem.ar;
        delete elem.net;
        //delete elem.ct;
    })
    $("#stats").html('')
    $("#stats").append(totalct + ' measurements')

    $("#loading").hide()

  /**********************************************************************
       Generate map 
   *********************************************************************/

    //var myLatlng = new google.maps.LatLng(47.670628,-122.20414);
    //var myLatlng = new google.maps.LatLng(37.538432,-122.05238);
    var myLatlng = new google.maps.LatLng(39.8282, -98.5795);
    var myOptions = {
        zoom: 4,
        center: myLatlng,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        disableDefaultUI: false,
        scrollwheel: true,
        draggable: true,
        navigationControl: true,
        mapTypeControl: true,
        scaleControl: true,
        disableDoubleClickZoom: false
    };
    map = new google.maps.Map(document.getElementById("heatmapArea"), myOptions);

        var legend = document.createElement('div');
        legend.id = 'legend';
        legendContent(legend, data_name);
        legend.index = 1;
        map.controls[google.maps.ControlPosition.RIGHT_BOTTOM].push(legend);



        clustermapelements = [];
        for (var i = 0; i < filtered_data.length; i++) {
            elem = filtered_data[i];

            
            if (!(category in elem)) {
                continue;
            }
            if (!(target in elem[category])) {
                continue;
            }
            var type = "all";
            var count = elem[category][target]["ct"];
            var avg_rtt = elem[category][target][data_chosen]; 
            //var avg_rtt = elem["rtt"];
            // For clustermap
            var color;
            if (data_chosen.indexOf("throughput") > -1){
                if (avg_rtt>=green_thres[data_name]) {
                    color='green'
                }
                else if (avg_rtt<green_thres[data_name] && avg_rtt>=yellow_thres[data_name]) {
                    color='yellow'
                }
                else if (avg_rtt<yellow_thres[data_name] && avg_rtt>=orange_thres[data_name]) {
                    color='orange'
                }
                else{
                    color='red'
                }
            } else {
                if (avg_rtt<=green_thres[data_name]) {
                    color='green'
                }
                else if (avg_rtt>green_thres[data_name] && avg_rtt<=yellow_thres[data_name]) {
                    color='yellow'
                }
                else if (avg_rtt>yellow_thres[data_name] && avg_rtt<=orange_thres[data_name]) {
                    color='orange'
                }
                else{
                    color='red'
                }
            }
            c = {}
            //c[color]=1
            c[color]=count;
            clustermapelements.push({
                'label': 'X',
                'coordinates': {'lat': elem["lat"], 'lng': elem["lng"]},
                'description': Math.round(avg_rtt).toString()+"ms", // ("+count.toString()+" measurements)",
                'color': c,
                'count': count
            });
        }

        hcmap = new clustermap.HCMap ({'map': map , 'elements': []}) ;
        // Draw ClusterMap
        google.maps.event.addListener(map, 'bounds_changed', function() {
            hcmap.reset();
            hcmap = new clustermap.HCMap ({'map': map , 'elements': clustermapelements}) ;
        });

    $("#dateslider").dateRangeSlider({
        step: {days: 7},
        defaultValues: {
            min: new Date(2013, 12, 18),
            max: new Date(2014, 3, 10)},
        bounds: {
            min: new Date(2012, 12, 18),
            max: new Date(2014, 3, 10)}
    });

    $("#dateslider").bind("userValuesChanged", function(e, data){filter()});


    $("#radiusslider" ).slider({
        value:def_radius,
        //min: 5,
        min: 15,
        //max: 25,
        max: 15,
        step: 1,
        create: function(event, ui) {
            $("#radiusslidervalue").text("Radius: "+def_radius);
        },
        change: function(event, ui) {
          // Unimplemented: redraw clustermap with new radius
          $("#radiusslidervalue").text("Radius: "+ui.value);
          //$("#radiusslidervalue").text("Unimplemented. Fixed radius size.");
        }
    });

}

// Generate the content for the legend
function legendContent(legend, data_chosen) {
    var title_options = {
        "rtt": "Average RTT (ms)",
        "rtt_packetloss": "Fraction of packets lost",
        "throughput": "Average throughput",
        "ping_mean": "Average RTT (ms)",
        "ping_worst": "Worst-case ping (per test)",
        "ping_stdev": "Variation in ping (stddev)",
        "ping_loss": "Packets lost (ping)",
        "trace_first": "First-hop latency",
        "trace_avg": "Avg. latency (traceroute)",
        "trace_num": "Num. hops (traceroute)",
        "dns_rtt": "DNS latency (ms)",
        "http_time": "HTTP load time",
        "http_throughput": "HTTP avg. throughput",
        "tcp_throughput": "Average throughput",
        "udp_jitter": "Jitter",
        "udp_outoforder": "Out of order packets",
        "udp_lossrate": "Packet loss rate"

    }

    // A title for the legend.
    var legendTitle = title_options[data_chosen];
    // The min / max values for each bucket and the associated color.
    var green_min = 0;
    var red_max = 'oo';
    if (data_chosen.indexOf("throughput") > -1) {
        var green_min = 'oo';
        var red_max = 0;
    }
    var styles = [
        {
            'min': green_min,
            'max': green_thres[data_chosen],
            'color': 'green'
        },
        {
            'min': green_thres[data_chosen],
            'max': yellow_thres[data_chosen],
            'color': 'yellow'
        },
        {
            'min': yellow_thres[data_chosen],
            'max': orange_thres[data_chosen],
            'color': 'orange'
        },
        {
            'min': orange_thres[data_chosen],
            'max': red_max,
            'color': 'red'
        }
    ];

    var title = document.createElement('p');
    title.innerHTML = legendTitle;
    legend.appendChild(title);

    for (var i=0; i<styles.length; i++) {
        var bucket = styles[i];

    var legendItem = document.createElement('div');

    var color = document.createElement('span');
    color.setAttribute('class', 'color');
    color.style.backgroundColor = bucket.color;
    legendItem.appendChild(color);

    var minMax = document.createElement('span');
    minMax.innerHTML = bucket.min + ' - ' + bucket.max;
    legendItem.appendChild(minMax);

    legend.appendChild(legendItem);
  }
}

