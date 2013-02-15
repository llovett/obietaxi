/**
 * points.js
 *
 * Works with index.html to send queries for points that lie within a given distance of
 * a given route.
 */

var ObietaxiMapper = ObietaxiMapper || {};
(function() {
    var map, markersArray = [];
    var routeBoxes;
    var directionService, directionsRenderer, routeBoxer;
    var routeBounds;

    // What we do when the page loads
    function initialize() {
	// Map & directions initialization code
	var latLng = new google.maps.LatLng(41.2939, -82.2175);    // Oberlin, OH
	var mapOptions = {
	    center: latLng,
	    zoom: 11,
	    noClear: true,
	    mapTypeId: google.maps.MapTypeId.ROADMAP
	};

	// This should match the id of the map div on points.html
	var map = new google.maps.Map(document.getElementById("map_canvas"), mapOptions);
	ObietaxiMapper.map = map;

	// Setup directions/boxing utilities
	directionService = new google.maps.DirectionsService();
	directionsRenderer = new google.maps.DirectionsRenderer( {
	    'map':map,
	    'draggable':true
	} );
	google.maps.event.addListener( directionsRenderer, 'directions_changed',
				       function() {
					   doPolygon( directionsRenderer.getDirections(),
						      ObietaxiMapper.polyfield || "#id_polygon" );
				       }
				     );
	routeBoxer = new RouteBoxer();
    }

    function doPolygon( directions ) {
	// Bounding-box encapsulation distance
	var distance = "10";

	// Box around the overview path of the first route
	var path = directions.routes[0].overview_path;
	var boxes = routeBoxer.box( path, distance );

	// Save the JSON'd boxes in the "polygon" field of the form
	$(ObietaxiMapper.polyfield || "#id_polygon").val( JSON.stringify(boxesToJSON(boxes)) );
    }

    // Find a route between two points. Find also all points we have
    // stored within a certain distance of that route.
    ObietaxiMapper.route = function( callback, start, end ) {
	// The request to be sent to Google for directions
	var _start = $(start || "#id_start_location").val().replace(/.* - /g,"");
	var _end = $(end || "#id_end_location").val().replace(/.* - /g,"");
	var request = {
	    origin: _start,
	    destination: _end,
	    travelMode: google.maps.DirectionsTravelMode.DRIVING
	};

	// Make the request
	directionService.route( request, function( result, status ) {
	    if ( status == google.maps.DirectionsStatus.OK ) {
		directionsRenderer.setDirections( result );

		// Find bounding box polygon, set in form
		doPolygon( result );

		// Callback
		callback();
	    } else {
		console.log("Could not load directions from Google!");
	    }
	} );
    }

    // Convert boxes into JSON
    function boxesToJSON( boxes ) {
	var box_list = [];
	for ( var i=0; i<boxes.length; i++ ) {
	    var ne = boxes[i].getNorthEast();
	    var sw = boxes[i].getSouthWest();

	    box_list[i*4] = ne.lat();
	    box_list[i*4 + 1] = ne.lng();
	    box_list[i*4 + 2] = sw.lat();
	    box_list[i*4 + 3] = sw.lng();
	}

	return { "rectangles" : box_list };
    }

    $(document).ready( initialize );
}());
