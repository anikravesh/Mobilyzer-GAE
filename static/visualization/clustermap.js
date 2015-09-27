/*!
 * Clustermap v1.0.1
 *
 * Copyright 2010, Jean-Yves Delort
 * Licensed under the MIT license.
 *
 */

var clustermap = function() {
  var _map;
  var _vectors;
  var _elements;
  var _tree;
  var _minDistance; // expressed in PIXELS
  var _selectedNodes;
  var _linkageType;
  var _displayedMarkers;
  var _infowindow;
  function HCMap(params) {
    this._map = params.map;
    this._elements = params.elements;
    this._infowindow = new google.maps.InfoWindow();

    if (typeof params.minDistance !== 'undefined')
      this._minDistance = params.minDistance;
    else
      this._minDistance = 140;

    if (typeof params.linkageType !== 'undefined')
      this._linkageType = params.linkageType;
    else
      this._linkageType = figue.COMPLETE_LINKAGE;
    var thishcmap = this;

    this._vectors = new Array();
    var labels = new Array();
    if (this._elements.length > 0) {
      var projection = this._map.getProjection();
      if (projection === 'undefined') {
        alert('Projection undefined. You need to wait for "bounds_changed" event before creating the clustermap');
      }

      // extract the points and convert the lat/lng coordinates to map coordinates
      for (var i = 0; i < this._elements.length; i++) {
        var element = this._elements[i];
        element.latlng = new google.maps.LatLng(element.coordinates.lat, element.coordinates.lng);
        var projcoord = projection.fromLatLngToPoint(element.latlng);
        var vector = [projcoord.x, projcoord.y];

        this._vectors.push(vector);
        labels.push(i);
      }
      // cluster the map coordinates
      this._tree = figue.agglomerate(labels,
                                     this._vectors,
                                     figue.EUCLIDIAN_DISTANCE,
                                     this._linkageType);

      this._zoom_changed_listener = google.maps.event.addListener(this._map,"zoom_changed",
            function() { updateNodes(thishcmap); }
          );

      this._bounds_changed_listener = google.maps.event.addListener(this._map, "bounds_changed",
                  function() { updateMarkers(thishcmap); });
      updateNodes(thishcmap);
      updateMarkers(thishcmap);
    }
  }

  // Node Selection Algorithm as described in:
  // Hierarchical Cluster Visualization in Web Mapping Systems, Proc. of the 19th ACM International WWW Conference (WWW'10)
  function selectNodes(node, MCD) {
    var selectedNodes;
    if (node.isLeaf())
      return [node];
    else if (node.dist < MCD)
      return [];
    else {
      selectedNodes = new Array();
      if (node.left != null) {
        if (node.left.isLeaf())
          selectedNodes.push(node.left);
        else {
          if (node.left.dist < MCD)
            selectedNodes.push(node.left);
          else
            selectedNodes = selectedNodes.concat(selectNodes(node.left, MCD));
        }
      }
      if (node.right != null) {
        if (node.right.isLeaf())
          selectedNodes.push(node.right);
        else {
          if (node.right.dist < MCD)
            selectedNodes.push(node.right);
          else
            selectedNodes = selectedNodes.concat(selectNodes(node.right, MCD));
        }
      }
    }
    return selectedNodes;
  }

  function updateMarkers(hcmap) {
    if (!hcmap._selectedNodes)
      return;

    // remove visible markers
    hcmap.removeMarkers();
    // display nodes as markers
    var viewport = hcmap._map.getBounds();
    if (viewport === 'undefined') {
      alert('Viewport undefined. You need to wait for "bounds_changed" event before creating the clustermap');
    }


    var selectedNodes = hcmap._selectedNodes;

    // TODO(jydelort): clean this hack to fix unshown markers at zoom level 1 or 2
    var current_zoom_level = hcmap._map.getZoom();

    for (var i = 0; i < selectedNodes.length; i++) {
      var element;
      var position;
      var description;

      var count = calculateCount(hcmap, selectedNodes[i]);
      var color = calculateColor(hcmap, selectedNodes[i]);
      if (selectedNodes[i].isLeaf()) {
        element = hcmap._elements[ selectedNodes[i].label ];
        position = element.latlng;
        description = element.description;
      } else {
        //description = "Only leaf nodes contain information";
        if (!color.red) color.red=0;
        if (!color.orange) color.orange=0;
        if (!color.yellow) color.yellow=0;
        if (!color.green) color.green=0;
        description = 
		"<table cellspacing=\"0\" cellpadding=\"0\" style=\"width:20px; font-size:13px; border-collapse: collapse; border-spacing: 0;\">"+
		"<tr>"+
  		  "<td>Green:</font></td>"+
  		  "<td>"+color.green+"</td>"+ 
		"</tr>"+
		"<tr>"+
  		  "<td>Yellow:</td>"+
  		  "<td>"+color.yellow+"</td>"+
		"</tr>"+
                "<tr>"+
                  "<td>Orange:</td>"+
                  "<td>"+color.orange+"</td>"+
                "</tr>"+
                "<tr>"+
                  "<td>Red:</td>"+
                  "<td>"+color.red+"</td>"+
                "</tr>"+
		"</table>" 
        //description = ("<p>"+"Green:&nbsp&nbsp&nbsp&nbsp"+color.green+"</br>"+"Yellow:&nbsp&nbsp&nbsp"+color.yellow+"</br>"+"Orange:&nbsp&nbsp"+color.orange+"</br>"+"Red:&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp"+color.red+"</p>");
        // Convert pixel coordinates to world coordinates
        var projcoord = new google.maps.Point(selectedNodes[i].centroid[0],
                                              selectedNodes[i].centroid[1]);
        position = hcmap._map.getProjection().fromPointToLatLng(projcoord);
      }
      if ((current_zoom_level > 2) && (!viewport.contains(position)))
        continue;

      var clusterSize = selectedNodes[i].size;
      var width = calculateCircleWidth(clusterSize);
      //var color = calculateColor(hcmap, selectedNodes[i]);

      var marker = new ClusterMarker({'latlng': position,
                                      'size': clusterSize,
                                      'color': color,
                                      'count': count,
                                      'description': description,
                                      'hcmap': hcmap,
                                      'width': width});
      // Makes the info window go away when clicking anywhere on the Map.
      google.maps.event.addListener(marker, 'click', function() {});

      marker.setMap(hcmap._map);
      hcmap._displayedMarkers.push(marker);
    }
  }

  function updateNodes(hcmap) {
    var MCD = hcmap._minDistance/Math.pow(2, hcmap._map.getZoom());

    var selectedNodes = selectNodes (hcmap._tree , MCD);
    if (selectedNodes.length == 0)
      selectedNodes.push(hcmap._tree);
    hcmap._selectedNodes = selectedNodes;
  }

  function childrenCounts(hcmap, node) {
    if (node.isLeaf()){
      return hcmap._elements[node.label].count;
    }

    var count = 0

    if (node.left != null) {
      var ccounts = childrenCounts(hcmap, node.left);
      count = count + ccounts;
    }
    if (node.right != null) {
      var ccounts = childrenCounts(hcmap, node.right);
      count = count + ccounts;
    }
    return count;
  }

  function calculateCount(hcmap, node) {
    var count = childrenCounts(hcmap, node);
    return count;
  }

  function childrenColors(hcmap, node) {
    if (node.isLeaf()){
      return hcmap._elements[node.label].color;
    }

    var colors = {}
    
    if (node.left != null) {
      var ccolors = childrenColors(hcmap, node.left);
      for (var key in ccolors){
        if (key in colors) colors[key]=colors[key]+ccolors[key];
        else colors[key]=ccolors[key];
      }
    }
    if (node.right != null) {
      var ccolors = childrenColors(hcmap, node.right);
      for (var key in ccolors){
        if (key in colors) colors[key]=colors[key]+ccolors[key];
        else colors[key]=ccolors[key];
      }
    }
    return colors;
  }

  function calculateColor(hcmap, node) {
    var colors = childrenColors(hcmap, node);
    return colors;
  }

  function calculateCircleWidth(cSize) {
    var sizes = [27, 36, 45, 58];
    // edit this if I want to make the cirlce size more directly proportional
    // to the number of its element (currently it can be one of 4 values)
    var i = 0;
    while (i < sizes.length && Math.round(cSize / 10) > 1) {
      cSize =  Math.round(cSize / 10);
      i++;
    }
    //return sizes[i];
    return 60;
  }

  function ClusterMarker(params) {
    this._latlng = params.latlng;
    this._size = params.size;
    this._count = params.count;
    this._width = params.width;
    this._color = params.color;
    this._description = params.description;
    this._hcmap = params.hcmap;

    this._div = null;
  }

  return {
    HCMap: HCMap,
    ClusterMarker: ClusterMarker
  }

}();


clustermap.HCMap.prototype.reset = function () {
  if (this._bounds_changed_listener) {
    google.maps.event.removeListener(this._bounds_changed_listener);
    this._bounds_changed_listener = null;
  }

  if (this._zoom_changed_listener) {
    google.maps.event.removeListener(this._zoom_changed_listener);
    this._zoom_changed_listener = null;
  }

  this._map = null;
  this._positions = new Array ();
  this._elements = new Array ();
  this._vectors = new Array ();
  this._selectedNodes = new Array ();
  this._tree = null;
  this.removeMarkers();
  }

clustermap.HCMap.prototype.removeMarkers = function () {
  if (this._displayedMarkers) {
    for (var i = 0; i < this._displayedMarkers.length; i++) {
      this._displayedMarkers[i].setMap(null);
    }
  }

  this._displayedMarkers = new Array ();
}

clustermap.ClusterMarker.prototype = new google.maps.OverlayView();

clustermap.ClusterMarker.prototype.onAdd = function () {
    // create the div
    var div = document.createElement('DIV');

    // set its style
    div.className = "baseMarker";
    
    // set its color
    colors = this._color
    //if (this._color.indexOf(",") > -1)
    if (Object.keys(colors).length > 1)
    {
      //colors = this._color.split(",");
      //var nbColors = colors.length;
      //var stepSize = 100 / nbColors;
      //var currentStep = 0;
      //var new_style = "(right bottom,";
      //var new_style = "(right,";
      //var new_style = "(";
      //for (var i = 0; i < nbColors; i++) {
      //  new_style += colors[i] + " " + stepSize + "%";
      //  if (i < nbColors - 1) { new_style += ",";}
      //}
      //new_style += ")";

      var total=0;
      for (var key in colors)
        total = total + colors[key];
      var c_labels = ['red', 'orange', 'yellow', 'green']
      fractions = []
      for (var i=0; i<c_labels.length; i++){
        if (c_labels[i] in colors)
          fractions[i]=(100*colors[c_labels[i]]/total);
        else
          fractions[i]=0;
      }
      var borders = []
      borders[0] = fractions[0];
      for (var i=1; i<fractions.length; i++)
        borders[i] = fractions[i]+borders[i-1];
      var smoothness = 5;
       
      var grad_size = this._width/2+'px '+this._width/2+'px'; 
      var str = "";
      str = c_labels[0]+' 0%, '
      for (var i=0; i<borders.length-1; i++)
        str = str + c_labels[i]+' '+(borders[i]-smoothness)+'%, '+c_labels[i+1]+' '+(borders[i]+smoothness)+'%, ';
      str = str + c_labels[c_labels.length-1]+' 100%'
      new_style = "(center, "+grad_size+", "+str+")";

      var ua = navigator.userAgent.toLowerCase();
      if (ua.indexOf('chrome') > -1)
        prefix = "-webkit-radial-gradient";
      else if (ua.indexOf('safari') > -1)
        prefix = "-webkit-radial-gradient";
      else if (ua.indexOf('mozilla') > -1){ 
        new_style = grad_size+", "+str+")";
        prefix = "radial-gradient(";
      }
      else if (ua.indexOf('explorer') > -1)
        prefix = "-ms-radial-gradient" + new_style;
      else if (ua.indexOf('opera') > -1)
        prefix = "-o-radial-gradient" + new_style;
      else
        prefix = "radial-gradient" + new_style;
      var bgImage = prefix+new_style;
      //console.log(bgImage);
      div.style.backgroundImage = bgImage;
    }
    else
      div.style.background = Object.keys(this._color)[0];

    // set opacity
    div.style.opacity = 0.80;

    // set its dimension
    div.style.width = this._width  + 'px';
    div.style.height = this._width  + 'px';

    // set the size of the cluster
    div.innerHTML = '<p style="font-weight:bold; color: black; margin: 0px; padding:0px; line-height:' + this._width + 'px">' + this._count + '</p>';

  this._div = div;
  this.getPanes().overlayImage.appendChild(div);

  // Register listeners to open up an info window when clicked.
  var me = this;
  google.maps.event.addDomListener(div, 'click', function() {
    var iw = me._hcmap._infowindow;
    iw.setContent(me._description);
    iw.setPosition(me._latlng);
    iw.open(me._hcmap._map);
  });
};

clustermap.ClusterMarker.prototype.onRemove = function() {
    this._div.parentNode.removeChild(this._div);
    this._div = null;
  }

clustermap.ClusterMarker.prototype.draw = function() {
    var overlayProjection = this.getProjection();
    // Retrieve the southwest and northeast coordinates of this overlay
    // in latlngs and convert them to pixels coordinates.
    var loc = overlayProjection.fromLatLngToDivPixel(this._latlng);

    // Set the marker at the right position.
    this._div.style.left = (loc.x - this._width / 2) + 'px';
    this._div.style.top = (loc.y - this._width / 2)+ 'px';
  }

