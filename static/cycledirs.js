
function updateThumbnail() {
	d = new Date();
	$('.dirimage').each(function (i, el) {
		src = el.src.split('?')[0]
		el.src = src + '?' + d.getTime();
	});
}

window.setInterval(updateThumbnail, 10000);