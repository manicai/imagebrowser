A simple web based image browser.

Designed to navigate directory trees of images. Each directory is shown with a
changing random example image from its contents. Once you get down to the
image  level clicking and image brings up slide show mode, left and right
arrow will move through the images, space will toggle auto-advance, up arrow
exits.

To run: 
  $ server.py {image root dir}

Requires [Tornado Web Framework](http://www.tornadoweb.org/en/stable/),
[Pillow image processing library](http://python-pillow.github.io/),
[path.py](https://github.com/jaraco/path.py).
