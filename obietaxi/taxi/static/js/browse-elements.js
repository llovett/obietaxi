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
		// TODO: show the map!
		console.log("show the map");
	    }
	);
    }
);
