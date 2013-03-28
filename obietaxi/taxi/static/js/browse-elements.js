$(document).ready(
    function() {
	// Submit button for asking for a ride
	$("#ask_for_ride_button").click(
	    function() {
		$("#request_form").submit();
	    }
	);

	// Next button to take user to map for offering a ride
	$("#offer_show_map_button").click(
	    function() {
		// Calculate route
		ObietaxiMapper.polyfield = "#offer_form #id_polygon";
		ObietaxiMapper.route(
		    function() {
			$(".new_offer_modal_form").slideUp();
			$(".new_offer_modal_map").slideDown();
			google.maps.event.trigger(ObietaxiMapper.map, 'resize');
		    },
		    "#id_offer_start_location",
		    "#id_offer_end_location"
		);
	    }
	);

	// Back button to take user back to form for offering a ride
	$("#offer_show_form_button").click(
	    function() {
		$(".new_offer_modal_map").slideUp();
		$(".new_offer_modal_form").slideDown();
	    }
	);

	// Submit button when offering a ride
	$("#offer_ride_button").click(
	    function() {
		$("#offer_form").submit();
	    }
	);

	// Initialize fuzzy search boxes
	function initSearchElements( type ) {
	    var startPoint = document.getElementById('id_'+type+'_start_location');
	    var endPoint = document.getElementById('id_'+type+'_end_location');

	    var defaultBounds = new google.maps.LatLngBounds(
		new google.maps.LatLng(25.641526,-122.622072),
		new google.maps.LatLng(49.837982, -64.174806));

	    // Available locations for drop-downs
	    var locations = [
		{'name':"Oberlin, OH",
		 'lat':41.2939386,
		 'lng':-82.21737859999996},
		{'name':"Cleveland Airport - 5300 Riverside Dr, Cleveland, OH",
		 'lat':41.410339,
		 'lng':-81.83616699999999},
		{'name':"Crocker Park - 159 Crocker Park Blvd #260  Westlake, OH",
		 'lat':41.45953129999999,
		 'lng':-81.95110779999999},
		{'name':"CVS Pharmacy - 297 S Main St, Oberlin, OH",
		 'lat':41.2847,
		 'lng':-82.21809999999999},
		{'name':"IGA -  331 E Lorain St, Oberlin, OH",
		 'lat':41.293209,
		 'lng':-82.20551899999998},
		{'name':"Johnny's Liquor Store - 12290 Leavitt Rd, Oberlin, OH",
		 'lat':41.308722,
		 'lng':-82.2168201},
		{'name':"Walmart - 46440 U.S. 20, Oberlin, OH",
		 'lat':41.266583,
		 'lng':-82.223344}
	    ];
	    var location_names = new Array();
	    for ( var i=0; i<locations.length; i++ ) {
		location_names.push( locations[i].name );
	    }

	    // Initialize combo-boxes
	    $("#id_"+type+"_start_location").combobox( location_names );
	    $("#id_"+type+"_end_location").combobox( location_names );

	    // Click handlers for combo-boxes
	    var doLatLng = function( who, startOrEnd ) {
		var index = 0;
		for (; index<locations.length; index++ ) {
		    if ( locations[index].name === who.text() ) {
			$("#id_"+type+"_"+startOrEnd+"_lat").val(locations[index].lat);
			$("#id_"+type+"_"+startOrEnd+"_lng").val(locations[index].lng);
			break;
		    }
		}
	    }
	    // N.B.: changing the start/end location on either
	    // offering or asking for a ride will result in changing
	    // the lat/lng for both!
	    $(document).on(
		'click',
		"#div_id_start_location .combobox_selector ul li",
		function() { doLatLng($(this), 'start'); }
	    );
	    $(document).on(
		'click',
		"#div_id_end_location .combobox_selector ul li",
		function() { doLatLng($(this), 'end'); }
	    );

	    var searchStartBox = new google.maps.places.Autocomplete(startPoint, { 'bounds': defaultBounds });
	    var searchEndBox = new google.maps.places.Autocomplete(endPoint, { 'bounds': defaultBounds });

	    var updateLatLng = function( startOrEnd ) {
		var place = (startOrEnd === 'start' ? searchStartBox : searchEndBox).getPlace();
		if ( place ) {
		    // Seems like this could be either one... ?
		    var lat = place.geometry.location.Ya || place.geometry.location.lat();
		    var lng = place.geometry.location.Za || place.geometry.location.lng();
		    $("#id_"+type+"_"+startOrEnd+"_lat").val(lat);
		    $("#id_"+type+"_"+startOrEnd+"_lng").val(lng);
		}
	    }

	    // Update lat/lng when input in fuzzy location inputs changes
	    google.maps.event.addListener(searchStartBox, 'place_changed', function(){
		updateLatLng( 'start' );
	    });
	    google.maps.event.addListener(searchEndBox, 'place_changed', function(){
		updateLatLng( 'end' );
	    });
	    // Also update when we loose focus on a search box
	    $("#id_"+type+"_start_location").blur( function () {
		updateLatLng( 'start' );
	    } );
	    $("#id_"+type+"_end_location").blur( function () {
		updateLatLng( 'end' );
	    } );

	    // Set start/end lat/lng if there is already text in one of the
	    // fuzzy location inputs.  This is useful when the form doesn't
	    // validate the first time, and the browser needs to refresh.
	    if ( $("#id_"+type+"_start_location").val().length > 0 ) {
		updateLatLng( 'start' );
	    }
	    if ( $("#id_"+type+"_end_location").val().length > 0 ) {
		updateLatLng( 'end' );
	    }
	}
	initSearchElements('request');
	initSearchElements('offer');

	// Initialize the date and time pickers
	$('.datepicker-default').datepicker({
	    format:'mm/dd/yyyy'
	});
	$('.timepicker-default').timepicker();
    }
);
