$(document).ready(
    function() {
	// Render href's of all request links
	$(".rr_div").each(
	    function( index ) {
		var id=$(this).attr('id');
		$(this).children("a").attr("href", "/request/show/?request_id="+id);
	    }
	);
    }
);
