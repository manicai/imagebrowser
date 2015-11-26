$(document).ready(function() {

function updateSlide() {
	var anchor = document.location.hash.substring(1);
	var path = '/slide/' + directory + '/' + anchor;
	var width = jQuery(window).width();
	var height = jQuery(window).height()
	$('#slide').attr('src', path + '?w=' + width + '&h=' + height);
}

function setIndex(index) {
 	var new_anchor = images[index];
	document.location = '#' + new_anchor;
	updateSlide();	
}

function nextImage() {
	var anchor = document.location.hash.substring(1);
	var index = images.indexOf(anchor);
	if (index == -1 || index >= images.length - 1) {
		return false;
	}

	setIndex(index + 1);
}

function prevImage() {
	var anchor = document.location.hash.substring(1);
	var index = images.indexOf(anchor);
	if (index <= 0) {
		return false;
	}

	setIndex(index - 1);	
}

function exit() {
	document.location = '/list/' + directory;
}

var interval = null;

function toggleSlideshow() {
	if (interval) {
		clearInterval(interval);
	} else {
		interval = setInterval(nextImage, 2500);
	}
}

$('#back-button').click(function (evt) {
	prevImage();
});

$('#next-button').click(function (evt) {
	nextImage();
});

$('#closs-button').click(function (evt) {
	exit();
});

$(window).resize(updateSlide);
$(document).keydown(function (evt) {
    switch(evt.which) {
    	case 32: // space
    		toggleSlideshow();
    		break;
        case 37: // left
        	prevImage();
        	break;
        case 38: // up
        	exit();
        	break;
        case 39: // right
        	nextImage();
       		break;
        //case 40: // down
        //break;
        default: return; // exit this handler for other keys
    }

    evt.preventDefault(); 
});

updateSlide();
});

