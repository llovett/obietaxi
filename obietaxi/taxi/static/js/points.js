/**
* points.js
*
* Works with index.html to send queries for points that lie within a given distance of
* a given route.
*/

var map, markersArray = [];
var routeBoxes;
var directionService, directionsRenderer, routeBoxer;
var routeBounds;

// What we do when the page loads
function initialize() {
    // Oberlin, OH
    var latLng = new google.maps.LatLng(41.2939, -82.2175);
    var mapOptions = {
	center: latLng,
	zoom: 11,
	mapTypeId: google.maps.MapTypeId.ROADMAP
    };
    // This should match the id of the map div on points.html
    map = new google.maps.Map(document.getElementById("map_canvas"), mapOptions);

    // Callback for clicking on the map
    // google.maps.event.addListener( map, 'click', addPoint );

    // Click handler for the directions "submit" button
    $("#submit").click( function( event ) {
	event.preventDefault();
	route();
    } );
    $("#clear").click( function( event ) {
	event.preventDefault();
	clearBoxes();
    } );

    // Setup directions/boxing utilities
    directionService = new google.maps.DirectionsService();
    directionsRenderer = new google.maps.DirectionsRenderer( {map: map} );
    routeBoxer = new RouteBoxer();

    // Date and time pickers
    $('.datepicker-default').datepicker({
	format:'mm/dd/yyyy'
    });
    $('.timepicker-default').timepicker();

    // Change form action URL based on submit button
    $("#offer_button").click(
	    function( event ) {
		//$("#offer_or_request_form").attr( 'action', '/request/search/' );
		event.preventDefault();
		route();
	    }
    );
    $("#ask_button").click(
	    function( event ) {
		$("#offer_or_request_form").attr( 'action', '/request/new/' );
	    }
    );
}

// This will submit the point's location to the server for storage in
// the database, then display that point as a marker on the map.
function addPoint( mouseEvent ) {
    $.ajax( {
	type: "POST",
	url: "/point/add/",
	data: { 'lat': mouseEvent.latLng.lat(),
		'lng': mouseEvent.latLng.lng() },
	success: function() {
	    displayPoint( mouseEvent.latLng );
	}
    } );
}

// This will display a point as a marker only.
function displayPoint( latLng, label ) {
    var marker = new MarkerWithLabel( {
    	position: latLng,
    	map: map,
	title: label,
	labelContent: label,
	labelClass: "maplabels"
    } );
    markersArray.push( marker );
}

// Remove all map markers
function clearMarkers() {
    for ( var i=0; i<markersArray.length; i++ ) {
	markersArray[i].setMap( null );
	markersArray[i].setVisible( false );
    }
    markersArray = new Array();
}

// Remove all boxes
function clearBoxes() {
    if ( routeBoxes != null ) {
	for ( var i=0; i<routeBoxes.length; i++ ) {
	    routeBoxes[i].setMap( null );
	    routeBoxes[i].setVisible( false );
	}
    }
    routeBoxes = null;
}

// Find a route between two points. Find also all points we have
// stored within a certain distance of that route.
function route() {
    // Clear all previous boxes
    //clearBoxes();

    // Bounding-box encapsulation distance
    //var distance = $("#distance").val();
    var distance = "10";
    
    // The request to be sent to Google for directions
    var request = {
	origin: $("#id_start_location").val(),
	destination: $("#id_end_location").val(),
	travelMode: google.maps.DirectionsTravelMode.DRIVING
    };

    // Make the request
    directionService.route( request, function( result, status ) {
	$("#status").empty();
	if ( status == google.maps.DirectionsStatus.OK ) {
	    directionsRenderer.setDirections( result );

	    // Box around the overview path of the first route
	    var path = result.routes[0].overview_path;
	    var boxes = routeBoxer.box( path, distance );

	    // Make a request to the server -------
	    // bounding boxes:
	    var request = boxesToJSON( boxes );
	    var startDate = Date.parse($("#id_date_0").val()+" "+$("#id_date_1").val());
	    // Get approximate start/end times for this trip
	    request.start_time = startDate;
	    var rideLength = 0;
	    for ( var i=0; i<result.routes[0].legs.length; i++ ) {
		rideLength += result.routes[i].legs[0].duration.value;
	    }
	    var endDate = startDate + 1000.0*rideLength;
	    request.end_time = endDate;
	    
	    $.ajax( {
		type: "POST",
		url: "/request/search/",
		data: request,
		dataType: "text",
		success: function( data ) {
		    // Convert to object from JSON string
		    var requests = ( $.parseJSON( data ) ).requests;
		    var start_points = new Array();
		    var end_points = new Array();
		    for( var i = 0; i<requests.length; i++){
			//grabbing start and end points for each location
			start_points[i] = requests[i].location_start;
			end_points[i] = requests[i].location_end;
		    }

		    $("#status").text(start_points.length+" rides returned.");

		    // Display markers that fit within the union of the boxes
		    clearMarkers();
		    showRides( requests );
		}
	    } );
	} else {
	    $("#status").text("Directions query failed: "+status);
	}
    } );
}

// List the relevant ride requests beneath the map
// start_points[i] is the start location of the ride ending at end_points[i]
function showRides( requests ){
    // Start out by emptying the current passenger listing
    $("#ride_listing").empty();

    for ( var i=0; i<requests.length; i++ ) {
	// Display starting point of passenger on the map, along with their name
	var start_point = requests[i].location_start;
	var end_point = requests[i].location_end;
	var passenger_name = requests[i].passenger_first_name + requests[i].passenger_last_name;
	displayPoint( new google.maps.LatLng(start_point[0], start_point[1]), passenger_name);

	// Put an item in the passenger list
	var newitem = $("<li></li>");
	newitem.addClass("passenger_item");
	var userlink = $("<a></a>");
	userlink.attr( {"href":"/accounts/profile/?user_id="+requests[i].passenger_id} );
	userlink.append( passenger_name );
//	var itemdesc = $("<
	newitem.append( userlink );
	$("#ride_listing").append( newitem );
    }
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

    return JSON.stringify( { "rectangles" : box_list } );
}

// Draw some boxes
function drawBoxes( boxes ) {
    routeBoxes = new Array( boxes.length );
    for ( var i=0; i<boxes.length; i++ ) {
	routeBoxes[i] = new google.maps.Rectangle({
	    bounds: boxes[i],
	    map: map
	});
    }
}

// See https://docs.djangoproject.com/en/dev/ref/contrib/csrf/
function getCSRF() {
    return $.cookie('csrftoken');
}

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function sameOrigin(url) {
    // test that a given url is a same-origin URL
    // url could be relative or scheme relative or absolute
    var host = document.location.host; // host + port
    var protocol = document.location.protocol;
    var sr_origin = '//' + host;
    var origin = protocol + sr_origin;
    // Allow absolute or scheme relative URLs to same origin
    return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
        (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
        // or any other URL that isn't scheme relative or absolute i.e relative.
        !(/^(\/\/|http:|https:).*/.test(url));
}

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && sameOrigin(settings.url)) {
            // Send the token to same-origin, relative URLs only.
            // Send the token only if the method warrants CSRF protection
            // Using the CSRFToken value acquired earlier
            xhr.setRequestHeader("X-CSRFToken", getCSRF() );
        }
    }
});
$(document).ready( initialize );
