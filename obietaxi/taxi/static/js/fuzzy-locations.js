$(document).ready(function(){
    var startPoint = document.getElementById('id_start_location');
    var endPoint = document.getElementById('id_end_location');

    var defaultBounds = new google.maps.LatLngBounds(
	new google.maps.LatLng(25.641526,-122.622072),
	new google.maps.LatLng(49.837982, -64.174806));

    var searchStartBox = new google.maps.places.SearchBox(startPoint, {bounds: defaultBounds});
    var searchEndBox = new google.maps.places.SearchBox(endPoint, {bounds: defaultBounds});

    google.maps.event.addListener(searchStartBox, 'places_changed', function(){
	var places = searchStartBox.getPlaces();
	var start_lat = places[0].geometry.location.Ya;
	var start_long = places[0].geometry.location.Za;
	$("#start_latitude").val(start_lat);
	$("#start_longitude").val(start_long);
    });
    google.maps.event.addListener(searchEndBox, 'places_changed', function(){
	var places = searchEndBox.getPlaces();
	var end_lat = places[0].geometry.location.Ya;
	var end_long = places[0].geometry.location.Za;
	$("#end_latitude").val(end_lat);
	$("#end_longitude").val(end_long);
    });
});
