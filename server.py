import path
import PIL.Image
import tornado.ioloop
import tornado.template
import tornado.web
import random
import sys

root = path.path('.')
loader = tornado.template.Loader('templates')

def filter_images(listing):
    return [fn.relpath(root) for fn in listing
            if fn.fnmatch('*.jpg', lambda x: x.lower())
            or fn.fnmatch('*.jpeg', lambda x: x.lower())]

class DirectoryThumbnailHandler(tornado.web.RequestHandler):
    def get(self, path):
        self.set_header('Content-Type', 'image/jpeg')
        base = PIL.Image.open('static/directory.jpg')
        dirpath = root / path
        files = filter_images(dirpath.walkfiles())
        if len(files) == 0:
            base.save(self, 'JPEG')
            return

        filepath = random.choice(files)
        try:
            img = PIL.Image.open(root / filepath)
        except IOError:
            base.save(self, 'JPEG')
            return

        img.thumbnail((150, 150))
        x_off = (base.width - img.width) / 2
        y_off = (base.height - img.height) / 2
        base.paste(img, (x_off, y_off))
        base.save(self, 'JPEG')

class ThumbnailHandler(tornado.web.RequestHandler):
    def get(self, path):
        filepath = root / path
        try:
            img = PIL.Image.open(filepath)
        except IOError:
            self.send_error(404)
            return

        img.thumbnail((200, 200))
        self.set_header('Content-Type', 'image/jpeg')
        img.save(self, 'JPEG')

class SlideHandler(tornado.web.RequestHandler):
    def get(self, path):
        filepath = root / path
        try:
            img = PIL.Image.open(filepath)
        except IOError:
            self.send_error(404)
            return

        width = int(self.get_argument('w'))
        height = int(self.get_argument('h'))
        img.thumbnail((width, height))

        self.set_header('Content-Type', 'image/jpeg')
        img.save(self, 'JPEG')

class IndexHandler(tornado.web.RequestHandler):
    def get(self, path):
        directory = root / path
        if not directory.exists():
            self.send_error(404)
            return 

        images = filter_images(directory.files())
        directories = [dn for dn in directory.dirs()
                       if not dn.basename().startswith('.')]

        self.write(loader.load('index.html') \
                        .generate(files=images,
                                  dirs=directories))

class SlideshowHandler(tornado.web.RequestHandler):
    def get(self, dir_path):
        directory = path.path(dir_path)

        images = filter_images((root / directory).files())
        self.write(loader.load('slides.html') \
                         .generate(imgs=[str(i.basename()) for i in images],
                                   directory=str(directory)))

def browser_app(debug = False, port = 8000, **kwargs):
    handlers = [tornado.web.url('/list/?(.*)', IndexHandler),
                tornado.web.url('/thumbnail/(.*)', ThumbnailHandler),
                tornado.web.url('/dirthumbnail/(.*)', 
                                DirectoryThumbnailHandler),
                tornado.web.url('/static/(.*)', 
                                tornado.web.StaticFileHandler, 
                                {'path': 'static'}),
                tornado.web.url('/slideshow/(.*)', SlideshowHandler),
                tornado.web.url('/slide/(.*)', SlideHandler),
                tornado.web.url('/', 
                                tornado.web.RedirectHandler, 
                                {"url": "/list/"}),]
    return tornado.web.Application(handlers, debug=debug, **kwargs)

def main():
    global root
    root = path.path(sys.argv[1])
    port = 8999

    app = browser_app(debug=True, port=port)
    app.listen(port, '0.0.0.0')
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()