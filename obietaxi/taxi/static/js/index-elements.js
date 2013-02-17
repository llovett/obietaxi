$(document).ready(
    function() {
	var startPoint = document.getElementById('id_start_location');
	var endPoint = document.getElementById('id_end_location');

	var defaultBounds = new google.maps.LatLngBounds(
	    new google.maps.LatLng(25.641526,-122.622072),
	    new google.maps.LatLng(49.837982, -64.174806));

	// Initialize combo-boxes
	// createEditableSelect( startPoint );
	// createEditableSelect( endPoint );
	$("#id_start_location").combobox(
	    ["Oberlin, OH",
	     "Cleveland Airport - 5300 Riverside Dr, Cleveland, OH",
	     "Crocker Park - 159 Crocker Park Blvd #260  Westlake, OH",
	     "CVS Pharmacy - 297 S Main St, Oberlin, OH",
	     "IGA -  331 E Lorain St, Oberlin, OH",
	     "Johnny's Carryout - 12290 Leavitt Rd, Oberlin, OH",
	     "Walmart - 46440 U.S. 20, Oberlin, OH"]
	);
	$("#id_end_location").combobox(
	    ["Oberlin, OH",
	     "Cleveland Airport - 5300 Riverside Dr, Cleveland, OH",
	     "Crocker Park - 159 Crocker Park Blvd #260  Westlake, OH",
	     "CVS Pharmacy - 297 S Main St, Oberlin, OH",
	     "IGA -  331 E Lorain St, Oberlin, OH",
	     "Johnny's Carryout - 12290 Leavitt Rd, Oberlin, OH",
	     "Walmart - 46440 U.S. 20, Oberlin, OH"]
	);

	var searchStartBox = new google.maps.places.SearchBox(startPoint,
							      { 'bounds': defaultBounds,
								'autocomplete': true });
	var searchEndBox = new google.maps.places.SearchBox(endPoint, { 'bounds': defaultBounds,
									'autocomplete': true});

	var updateLatLng = function( startOrEnd ) {
	    var places = (startOrEnd === 'start' ? searchStartBox : searchEndBox).getPlaces();
	    if ( places ) {
		var lat = places[0].geometry.location.Ya;
		var lng = places[0].geometry.location.Za;
		$("#id_"+startOrEnd+"_lat").val(lat);
		$("#id_"+startOrEnd+"_lng").val(lng);
	    }
	}

	// Update lat/lng when input in fuzzy location inputs changes
	google.maps.event.addListener(searchStartBox, 'places_changed', function(){
	    updateLatLng( 'start' );
	});
	google.maps.event.addListener(searchEndBox, 'places_changed', function(){
	    updateLatLng( 'end' );
	});
	// Also update when we loose focus on a search box
	$("#id_start_location").blur( function () {
	    updateLatLng( 'start' );
	} );
	$("#id_end_location").blur( function () {
	    updateLatLng( 'end' );
	} );

	// Set start/end lat/lng if there is already text in one of the
	// fuzzy location inputs.  This is useful when the form doesn't
	// validate the first time, and the browser needs to refresh.
	if ( $("#id_start_location").val().length > 0 ) {
	    updateLatLng( 'start' );
	}
	if ( $("#id_end_location").val().length > 0 ) {
	    updateLatLng( 'end' );
	}

	// Initialize the date and time pickers
	$('.datepicker-default').datepicker({
	    format:'mm/dd/yyyy'
	});
	$('.timepicker-default').timepicker();

	// What we do when the "Search Offers" button is pressed
	$("#search_offers_button").click(
	    function() {
		$("#offer_or_request_form").attr( {"action": "/offer/search/browse/"} );
	    }
	);
	// What we do when the "Search Rides" button is pressed
	$("#search_rides_button").click(
	    function( event ) {
		event.preventDefault();

		// Show suggested travel route on the map
		ObietaxiMapper.route(
		    function() {
			$(".search_map").slideDown();
			$(".search_form").slideUp();
			google.maps.event.trigger(ObietaxiMapper.map, 'resize');
		    }
		);
	    }
	);
	$("#back_to_form").click(
	    function() {
		$(".search_map").slideUp();
		$(".search_form").slideDown();
		google.maps.event.trigger(ObietaxiMapper.map, 'resize');
	    }
	);

	// Submission after meddling with the map
	$("#submit_from_map").click(
	    function() {
		// Save the JSON'd boxes in the "polygon" field of the form
		$("#offer_or_request_form").attr( {"action": "/request/search/browse/"} );
		$("#offer_or_request_form").submit();
	    }
	);
    }
);
