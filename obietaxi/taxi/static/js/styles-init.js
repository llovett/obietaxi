$(document).ready(
    function() {
	// Date and time pickers
	$('.datepicker-default').datepicker({
	    format:'mm/dd/yyyy'
	});
	$('.timepicker-default').timepicker();

	// Change form action URL based on submit button
	$("#offer_button").click(
	    function( event ) {
		$("#offer_or_request_form").attr( 'action', '/offer/new/' );
	    }
	);
	$("#ask_button").click(
	    function( event ) {
		$("#offer_or_request_form").attr( 'action', '/request/new/' );
	    }
	);
    }
);
