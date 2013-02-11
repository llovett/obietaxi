$(document).ready(function(){
    var startPoint = document.getElementById('id_start_location');
    var endPoint = document.getElementById('id_end_location');

    var defaultBounds = new google.maps.LatLngBounds(
	new google.maps.LatLng(25.641526,-122.622072),
	new google.maps.LatLng(49.837982, -64.174806));

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
});
