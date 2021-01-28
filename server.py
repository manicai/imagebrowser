#!/usr/bin/env python
import random
import sys
import pathlib

import PIL.Image
import tornado.ioloop
import tornado.template
import tornado.web

root = pathlib.Path('.')
loader = tornado.template.Loader('templates')


class ImageCache(object):
    def __init__(self):
        self._cache = {}

    def add(self, path, image):
        #self._cache[path] = image
        pass

    def get(self, path):
        return self._cache.get(path, None)


cache = ImageCache()


def filter_movies(listing):
    return sorted([fn.relative_to(root) for fn in listing
                   if fn.match('*.mp4') or fn.match('*.avi') or fn.match('*.webm')])


def filter_images(listing):
    return sorted([fn.relative_to(root) for fn in listing
                   if fn.match('*.jpg') or fn.match('*.JPG')
                   or fn.match('*.jpeg') or fn.match('*.JPEG')])


def walk(p: pathlib.Path):
    if p.is_file():
        yield p
        return
    else:
        for entry in p.iterdir():
            if entry.is_file():
                yield entry
            elif entry.is_dir():
                for x in walk(entry):
                    yield x


class DirectoryThumbnailHandler(tornado.web.RequestHandler):
    def get(self, dir_path: str):
        self.set_header('Content-Type', 'image/png')
        base = PIL.Image.open('static/directory.png')
        directory = root / dir_path
        files = filter_images(i for i in walk(directory) if i.is_file())
        if len(files) == 0:
            base.save(self, 'PNG')
            return

        filepath = random.choice(files)
        try:
            img = PIL.Image.open(root / filepath)
        except IOError:
            base.save(self, 'PNG')
            return

        img.thumbnail((150, 150))
        x_off = (base.width - img.width) // 2
        y_off = (base.height - img.height) // 2
        base.paste(img, (x_off, y_off))
        base.save(self, 'PNG')

class ThumbnailHandler(tornado.web.RequestHandler):
    def get(self, image_path: str):
        image = cache.get(self.request.uri)
        if not image:
            filepath = root / image_path
            try:
                image = PIL.Image.open(filepath)
            except IOError:
                self.send_error(404)
                return

            image.thumbnail((200, 200))
            cache.add(self.request.uri, image)

        self.set_header('Content-Type', 'image/jpeg')
        image.save(self, 'JPEG')


class SlideHandler(tornado.web.RequestHandler):
    def get(self, image_path: str):
        image = cache.get(self.request.uri)
        if not image:
            filepath = root / image_path
            try:
                image = PIL.Image.open(filepath)
            except IOError:
                self.send_error(404)
                return

            width = int(self.get_argument('w'))
            height = int(self.get_argument('h'))
            image.thumbnail((width, height))
            cache.add(self.request.uri, image)

        self.set_header('Content-Type', 'image/jpeg')
        image.save(self, 'JPEG')


class IndexHandler(tornado.web.RequestHandler):
    def get(self, dir_path: str):
        directory = root / dir_path
        if not directory.exists():
            self.send_error(404)
            return

        images = filter_images(f for f in directory.iterdir() if f.is_file())
        movies = filter_movies(f for f in directory.iterdir() if f.is_file())
        directories = sorted([dn for dn in directory.iterdir()
                              if dn.is_dir() and not dn.name.startswith('.')],
                             key=lambda p: p.name.casefold())

        self.write(loader.load('index.html') \
                   .generate(files=images,
                             movies=movies,
                             dirs=directories))


class SlideshowHandler(tornado.web.RequestHandler):
    def get(self, dir_path: str):
        directory = pathlib.Path(dir_path)

        images = filter_images(f for f in (root / directory).iterdir() if f.is_file())
        self.write(loader.load('slides.html')
                   .generate(imgs=[str(i.name) for i in images],
                             directory=str(directory)))


class MovieHandler(tornado.web.RequestHandler):
    def get(self, path: str):
        movie_path = root / path
        self.set_header('Content-Type', 'video/mp4')
        with open(movie_path, 'rb') as fh:
            while True:
                data = fh.read(64 * 1024)
                if not data:
                    break
                self.write(data)
        self.finish()


class MoviePlayerHandler(tornado.web.RequestHandler):
    def get(self, path: str):
        self.write(loader.load('movie.html').generate(video=path))


def browser_app(debug=False, **kwargs):
    handlers = [tornado.web.url('/list/?(.*)', IndexHandler),
                tornado.web.url('/thumbnail/(.*)', ThumbnailHandler),
                tornado.web.url('/dirthumbnail/(.*)',
                                DirectoryThumbnailHandler),
                tornado.web.url('/movie/(.*)', MovieHandler),
                tornado.web.url('/player/(.*)', MoviePlayerHandler),
                tornado.web.url('/static/(.*)',
                                tornado.web.StaticFileHandler,
                                {'path': 'static'}),
                tornado.web.url('/slideshow/(.*)', SlideshowHandler),
                tornado.web.url('/slide/(.*)', SlideHandler),
                tornado.web.url('/',
                                tornado.web.RedirectHandler,
                                {"url": "/list/"}), ]
    return tornado.web.Application(handlers, debug=debug, **kwargs)


def main():
    global root
    root = pathlib.Path(sys.argv[1])
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    else:
        port = 8999

    app = browser_app(debug=True)
    app.listen(port, '0.0.0.0')
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
