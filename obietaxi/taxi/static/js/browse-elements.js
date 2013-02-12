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
		$(".new_offer_modal_form").slideUp();
		$(".new_offer_modal_map").slideDown();
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
    }
);
