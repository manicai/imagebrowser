$(document).ready(function() {

function getPath(anchor) {
    var path = '/slide/' + directory + '/' + anchor;
    var width = jQuery(window).width();
    var height = jQuery(window).height();
    return path + '?w=' + width + '&h=' + height;
}

function updateSlide() {
	var anchor = document.location.hash.substring(1);
	$('img#slide').attr('src', getPath(anchor));
}

function updateCache(index) {
    if (index > 0) {
        var prev_anchor = images[index-1];
        $('img#prev').attr('src', getPath(prev_anchor));
    }

    if (index < images.length - 1) {
        var next_anchor = images[index+1];
        $('img#next').attr('src', getPath(next_anchor));
    }
}

function setIndex(index) {
    if (index === -1) {
        return;
    }

 	var new_anchor = images[index];
	document.location = '#' + new_anchor;
	updateSlide();
    updateCache(index);
}

function nextImage() {
	var anchor = document.location.hash.substring(1);
	var index = images.indexOf(anchor);
	if (index === -1 || index >= images.length - 1) {
		return -1;
	}

	return index + 1;
}

function prevImage() {
	var anchor = document.location.hash.substring(1);
	var index = images.indexOf(anchor);
	if (index <= 0) {
		return -1;
	}

	return index - 1;
}

function exit() {
	document.location = '/list/' + directory;
}

var interval = null;

function toggleSlideshow() {
	if (interval) {
		clearInterval(interval);
	} else {
		interval = setInterval(function() { setIndex(nextImage()); }, 2500);
	}
}

$('#back-button').click(function (evt) {
	setIndex(prevImage());
});

$('#next-button').click(function (evt) {
	setIndex(nextImage());
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
        	setIndex(prevImage());
        	break;
        case 38: // up
        	exit();
        	break;
        case 39: // right
        	setIndex(nextImage());
       		break;
        //case 40: // down
        //break;
        default: return; // exit this handler for other keys
    }

    evt.preventDefault();
});

updateSlide();
});

