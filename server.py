#!/usr/bin/env python
import hashlib
import json
import sys
import pathlib

import PIL.Image
import tornado.ioloop
import tornado.template
import tornado.web

root = pathlib.Path('.')
loader = tornado.template.Loader('templates')

DIRECTORY_THUMBNAIL_SAMPLE_RATIO = 0.10
DIRECTORY_THUMBNAIL_CACHE_DIRNAME = '.directory-thumbnail-cache'
DIRECTORY_THUMBNAIL_METADATA_DIRNAME = 'metadata'
DIRECTORY_THUMBNAIL_IMAGES_DIRNAME = 'images'

directory_thumbnail_cache_root = None
directory_thumbnail_metadata_root = None
directory_thumbnail_images_root = None


class ImageCache(object):
    def __init__(self):
        self._cache = {}

    def add(self, path, image):
        #self._cache[path] = image
        pass

    def get(self, path):
        return self._cache.get(path, None)


cache = ImageCache()


def _ensure_directory_thumbnail_cache_dirs():
    global directory_thumbnail_cache_root
    global directory_thumbnail_metadata_root
    global directory_thumbnail_images_root

    if directory_thumbnail_cache_root is None:
        directory_thumbnail_cache_root = root / DIRECTORY_THUMBNAIL_CACHE_DIRNAME
        directory_thumbnail_metadata_root = (
            directory_thumbnail_cache_root / DIRECTORY_THUMBNAIL_METADATA_DIRNAME
        )
        directory_thumbnail_images_root = (
            directory_thumbnail_cache_root / DIRECTORY_THUMBNAIL_IMAGES_DIRNAME
        )

    directory_thumbnail_metadata_root.mkdir(parents=True, exist_ok=True)
    directory_thumbnail_images_root.mkdir(parents=True, exist_ok=True)


def _atomic_write_text(path: pathlib.Path, text: str):
    tmp_path = path.with_name(path.name + '.tmp')
    tmp_path.write_text(text, encoding='utf-8')
    tmp_path.replace(path)


def _dir_cache_key(dir_path: str):
    normalized = pathlib.PurePosixPath(dir_path).as_posix()
    if normalized in ('', '.'):
        normalized = '__root__'
    digest = hashlib.sha1(normalized.encode('utf-8')).hexdigest()
    return normalized, digest


def _dir_metadata_path(dir_key: str):
    return directory_thumbnail_metadata_root / f'{dir_key}.json'


def _dir_image_cache_path(dir_key: str, image_path: str):
    image_digest = hashlib.sha1(image_path.encode('utf-8')).hexdigest()
    return directory_thumbnail_images_root / f'{dir_key}-{image_digest}.png'


def _evenly_sample(items, ratio):
    if len(items) == 0:
        return []

    sample_size = max(1, int(len(items) * ratio))
    sample_size = min(sample_size, len(items))
    indices = {(i * len(items)) // sample_size for i in range(sample_size)}
    return [items[i] for i in sorted(indices)]


def _build_metadata_for_directory(directory: pathlib.Path, metadata_path: pathlib.Path):
    files = filter_images(i for i in walk(directory) if i.is_file())
    sampled = _evenly_sample(files, DIRECTORY_THUMBNAIL_SAMPLE_RATIO)
    metadata = {
        'sample_ratio': DIRECTORY_THUMBNAIL_SAMPLE_RATIO,
        'images': [str(p) for p in sampled],
        'next_index': 0,
    }
    _atomic_write_text(metadata_path, json.dumps(metadata, indent=2, sort_keys=True))
    return metadata


def _load_metadata(directory: pathlib.Path, metadata_path: pathlib.Path):
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
            images = metadata.get('images', [])
            if isinstance(images, list) and len(images) > 0:
                return metadata
        except (OSError, json.JSONDecodeError):
            pass
    return _build_metadata_for_directory(directory, metadata_path)


def _next_sampled_image(metadata: dict, metadata_path: pathlib.Path):
    images = metadata.get('images', [])
    if len(images) == 0:
        return None

    index = int(metadata.get('next_index', 0)) % len(images)
    image_path = images[index]
    metadata['next_index'] = (index + 1) % len(images)
    _atomic_write_text(metadata_path, json.dumps(metadata, indent=2, sort_keys=True))
    return image_path


def _compose_directory_thumbnail(selected_image_relpath: str):
    base = PIL.Image.open('static/directory.png')
    try:
        img = PIL.Image.open(root / selected_image_relpath)
    except IOError:
        return base

    img.thumbnail((150, 150))
    x_off = (base.width - img.width) // 2
    y_off = (base.height - img.height) // 2
    base.paste(img, (x_off, y_off))
    return base


def _save_thumbnail_image(path: pathlib.Path, image: PIL.Image.Image):
    tmp_path = path.with_name(path.name + '.tmp')
    with tmp_path.open('wb') as fh:
        image.save(fh, 'PNG')
    tmp_path.replace(path)


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
        directory = root / dir_path
        if not directory.exists() or not directory.is_dir():
            self.send_error(404)
            return

        _, dir_key = _dir_cache_key(dir_path)
        metadata_path = _dir_metadata_path(dir_key)
        metadata = _load_metadata(directory, metadata_path)
        selected = _next_sampled_image(metadata, metadata_path)
        if selected is None:
            base = PIL.Image.open('static/directory.png')
            base.save(self, 'PNG')
            return

        cached_thumb_path = _dir_image_cache_path(dir_key, selected)
        if cached_thumb_path.exists():
            with cached_thumb_path.open('rb') as fh:
                self.write(fh.read())
            return

        composed = _compose_directory_thumbnail(selected)
        if (root / selected).exists():
            _save_thumbnail_image(cached_thumb_path, composed)
        composed.save(self, 'PNG')

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
    global directory_thumbnail_cache_root
    global directory_thumbnail_metadata_root
    global directory_thumbnail_images_root

    root = pathlib.Path(sys.argv[1])
    directory_thumbnail_cache_root = None
    directory_thumbnail_metadata_root = None
    directory_thumbnail_images_root = None
    _ensure_directory_thumbnail_cache_dirs()

    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    else:
        port = 8999

    app = browser_app(debug=True)
    print(f"Serving {root} on 0.0.0.0:{port}")
    app.listen(port, '0.0.0.0')
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
