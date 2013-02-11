$(document).ready(
    function() {
	function initSearchElements( type ) {
	    var startPoint = document.getElementById('id_'+type+'_start_location');
	    var endPoint = document.getElementById('id_'+type+'_end_location');

	    var defaultBounds = new google.maps.LatLngBounds(
		new google.maps.LatLng(25.641526,-122.622072),
		new google.maps.LatLng(49.837982, -64.174806));

	    var searchStartBox = new google.maps.places.Autocomplete(startPoint, { 'bounds': defaultBounds });
	    var searchEndBox = new google.maps.places.Autocomplete(endPoint, { 'bounds': defaultBounds });

	    var updateLatLng = function( startOrEnd ) {
		var place = (startOrEnd === 'start' ? searchStartBox : searchEndBox).getPlace();
		if ( place ) {
		    var lat = places[0].geometry.location.Ya;
		    var lng = places[0].geometry.location.Za;
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
    }
);
