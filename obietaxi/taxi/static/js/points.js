/**
 * points.js
 *
 * Works with index.html to send queries for points that lie within a given distance of
 * a given route.
 */

(function() {
    var map, markersArray = [];
    var routeBoxes;
    var directionService, directionsRenderer, routeBoxer;
    var routeBounds;

    // What we do when the page loads
    function initialize() {
	// Initialize the date and time pickers
	$('.datepicker-default').datepicker({
	    format:'mm/dd/yyyy'
	});
	$('.timepicker-default').timepicker();

	// Map & directions initialization code
	var latLng = new google.maps.LatLng(41.2939, -82.2175);    // Oberlin, OH
	var mapOptions = {
	    center: latLng,
	    zoom: 11,
	    mapTypeId: google.maps.MapTypeId.ROADMAP
	};

	// This should match the id of the map div on points.html
	map = new google.maps.Map(document.getElementById("map_canvas"), mapOptions);

	// Setup directions/boxing utilities
	directionService = new google.maps.DirectionsService();
	directionsRenderer = new google.maps.DirectionsRenderer( {
	    'map':map,
	    'draggable':true
	} );
	google.maps.event.addListener( directionsRenderer, 'directions_changed',
				       function() {
					   doPolygon( directionsRenderer.getDirections() );
				       }
				     );
	routeBoxer = new RouteBoxer();

	// What we do when the "Search Offers" button is pressed
	$("#search_offers_button").click(
	    function() {
		$("#offer_or_request_form").attr( {"action": "/request/search/browse/"} );
	    }
	);
	// What we do when the "Search Rides" button is pressed
	$("#search_rides_button").click(
	    function( event ) {
		event.preventDefault();

		$("#offer_or_request_form").attr( {"action": "/offer/search/browse/"} );

		// Show suggested travel route on the map
		route(
		    function() {
			//TODO: allow the driver to modify the route and
			//update #id_polygon as necessary
			$("#right_panel").css( {'margin-left':0} );
		    }
		);
	    }
	);
	// Submission after meddling with the map
	$("#submit_from_map").click(
	    function() {
		// Save the JSON'd boxes in the "polygon" field of the form
		$("#id_polygon").val( JSON.stringify(boxesToJSON(boxes)) );
		$("#offer_or_request_form").attr( {"action": "/request/search/browse/"} );
		$("#offer_or_request_form").submit();
	    }
	);

	// Hide the right panel (containing the map, "OK" button for searching rides)
	$("#right_panel").css( {'margin-left':1000} );
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

    // AJAX request to search offers
    function searchOffers( callback ) {
	$.ajax( {
	    type: "POST",
	    url: "/offer/search/",
	    data: $("#offer_or_request_form").serialize(),
	    dataType: "text",
	    success: function( data ) {
		if ( data.length > 0 ) {
		    offers = ( $.parseJSON( data ) ).offers;
		    showOffers( offers );
		    callback( offers );
		}
	    }
	} );
    }

    function doPolygon( directions ) {
	// Bounding-box encapsulation distance
	var distance = "10";

	// Box around the overview path of the first route
	var path = directions.routes[0].overview_path;
	var boxes = routeBoxer.box( path, distance );

	// Save the JSON'd boxes in the "polygon" field of the form
	$("#id_polygon").val( JSON.stringify(boxesToJSON(boxes)) );
    }

    // Find a route between two points. Find also all points we have
    // stored within a certain distance of that route.
    function route( callback ) {
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

		// Find bounding box polygon, set in form
		doPolygon( result );

		// Callback
		callback();
	    } else {
		console.log("Could not load directions from Google!");
	    }
	} );
    }

    function showOffers( offers ) {
	// Start out by emptying the current passenger listing
	$("#ride_listing").empty();

	for ( var i=0; i<offers.length; i++ ) {
	    // Display starting point of driver on the map, along with their name
	    var start_point = offers[i].location_start.point;
	    var end_point = offers[i].location_end.point;
	    var driver_name = offers[i].driver_first_name + " " + offers[i].driver_last_name;
	    displayPoint( new google.maps.LatLng(start_point[0], start_point[1]), driver_name);

	    // Put an item in the driver list
	    var newitem = $("<li></li>");
	    newitem.addClass("driver_item");
	    var userlink = $("<a></a>");
	    userlink.attr( {"href":"/accounts/profile/?user_id="+offers[i].driver_id} );
	    userlink.append( driver_name );
	    var offerlink = $("<a></a>");
	    offerlink.attr( {'href':'/offer/show/?offer_id='+offers[i].id} );
	    offerlink.append("Offer going from <strong>"+
			     offers[i].location_start.title+
			     "</strong> to <strong>"+
			     offers[i].location_end.title+
			     "</strong>");
	    var itemdate = $("<p><strong>"+offers[i].date+"</strong></p>");
	    // TODO: add "ask for ride" button
	    newitem
		.append( offerlink )
		.append( " by " )
		.append( userlink )
		.append( " on " )
		.append( itemdate );
	    $("#ride_listing").append( newitem );
	}
    }

    // List the relevant ride requests beneath the map
    // start_points[i] is the start location of the ride ending at end_points[i]
    function showRides( requests ){
	// Start out by emptying the current passenger listing
	$("#ride_listing").empty();

	for ( var i=0; i<requests.length; i++ ) {
	    // Display starting point of passenger on the map, along with their name
	    var start_point = requests[i].location_start.point;
	    var end_point = requests[i].location_end.point;
	    var passenger_name = requests[i].passenger_first_name + " " + requests[i].passenger_last_name;
	    displayPoint( new google.maps.LatLng(start_point[0], start_point[1]), passenger_name);

	    // Put an item in the passenger list
	    var newitem = $("<li></li>");
	    newitem.addClass("passenger_item");
	    var userlink = $("<a></a>");
	    userlink.attr( {"href":"/accounts/profile/?user_id="+requests[i].passenger_id} );
	    userlink.append( passenger_name );
	    var reqlink = $("<a></a>");
	    reqlink.attr( {'href':'/request/show/?request_id='+requests[i].id} );
	    reqlink.append("Request to go from <strong>"+
			   requests[i].location_start.title+
			   "</strong> to <strong>"+
			   requests[i].location_end.title+
			   "</strong>");
	    var itemdate = $("<p><strong>"+requests[i].date+"</strong></p>");

	    // TODO: add "offer ride" button
	    newitem
		.append( reqlink )
		.append( " by " )
		.append( userlink )
		.append( " on " )
		.append( itemdate );
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

	return { "rectangles" : box_list };
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
}());
