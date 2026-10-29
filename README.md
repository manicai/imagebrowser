A simple web based image browser.

Designed to navigate directory trees of images. Each directory is shown with a
changing random example image from its contents. Once you get down to the
image  level clicking and image brings up slide show mode, left and right
arrow will move through the images, space will toggle auto-advance, up arrow
exits.

To run: 
  $ server.py {image root dir}

Directory thumbnail cache:
- Directory thumbnails now use a sampled subset of images per directory and are cached on disk.
- Cache location: {image root dir}/.directory-thumbnail-cache
- To clear cached directory thumbnails, delete that folder on the server.

Videos:
- Only .mp4, .webm and .avi files are listed; browsers can only reliably play
  H.264/AAC MP4.
- `scripts/recode.sh [-n] FILE...` converts to NAME.mp4 (H.264/AAC, max
  1080p), removing the original once it succeeds. Compatible files are
  remuxed losslessly; the rest are re-encoded with x264. `-n` is a dry run.
  Needs ffmpeg (built with libx264) and ffprobe.

Requires [Tornado Web Framework](http://www.tornadoweb.org/en/stable/),
[Pillow image processing library](http://python-pillow.github.io/),
[path.py](https://github.com/jaraco/path.py).
