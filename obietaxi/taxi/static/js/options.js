/*
 * options.js
 * 
 * Works with offer_options.html and request_options.html
 * Currently, just to get the cancel button to work
 */

$(document).ready( function() {
    // What we do when the "Update" button is pressed
    $("#update_button").click( function () {

	// Check whether this is a request or an offer
	var pathArray = window.location.pathname.split( '/' );
	var rideType = pathArray[1];

	if (rideType == "offer"){
	    $("#OfferOptionsForm").attr( {"action":"."} )
	} else if (rideType == "request"){
	    $("#RequestOptionsForm").attr( {"action":"."} )
	}
    } );

			     
    // What we do when the "Cancel Offer/Ride Button" is pressed
    $("#cancel_button").click( function( event ) {
	event.preventDefault();
	
	console.log("We could be cancelling");

	var pathArray = window.location.pathname.split('/');
	var rideType = pathArray[1];
	var id = pathArray[pathArray.length-2];

	// create the path for window.location redirect
	var redirectPath = "/" + pathArray[1] + "/cancel/" + id + "/" ;

	for (var j=0; j<pathArray.length; j++){
	    console.log("bucket " + j + " : " + pathArray[j] + "\n");
	}
	
	if (rideType == "offer"){
	    console.log("RideOffer with path " + redirectPath); 
//	    $("#CancellationForm").attr( {"action":"/offer/cancel/" + id + "/"} );
	    window.location = redirectPath;
	} else if (rideType == "request"){
//	    $("#CancellationForm").attr( {"action":"/request/cancel/" + id + "/"} );
	    window.location = redirectPath;
	}
    } );

} );
