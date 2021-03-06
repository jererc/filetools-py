import os
import re
import logging

from filetools import media


RE_DOWNLOAD_JUNK = re.compile(r'/(\.DS_Store|Thumbs\.db)$', re.I)
UNPACK_PASSES = 3
SIZE_ALBUM_IMAGE_MIN = 50     # KB

logger = logging.getLogger(__name__)


def downloads(path):
    '''Iterate processed downloads.
    '''
    if not os.path.exists(path):
        logger.error('%s does not exist', path)
        return

    for file in media.iter_files(path, incl_dirs=True, recursive=False):
        if media.is_file_open(file):
            continue
        file = unpack_download(file)
        for res in get_downloads(file):
            res = clean_download_dir(res)
            if res:
                yield media.File(res)

def unpack_download(download, passes=UNPACK_PASSES):
    '''Move download file into a directory and unpack the archives.

    :return: directory
    '''
    download = media.clean_file(download, strip_extra=True)
    if os.path.isfile(download):
        # Move file into a directory
        path_dst = media.get_unique(os.path.splitext(download)[0])
        path, filename, ext = media.fsplit(download)
        file_dst = media.rename_file(download,
                os.path.join(path_dst, filename + ext))
        download = os.path.dirname(file_dst)

    to_skip = []
    for i in range(passes):
        for file in sorted(list(media.iter_files(download))):  # sort for multipart archives
            if file in to_skip:
                continue
            res = media.get_file(file)
            if res.type == 'archive':
                to_skip += res.unpack(remove_src=True)
            else:
                to_skip.append(file)

    return download

def clean_download_dir(path):
    '''Clean the download directories and files.
    '''
    for file in list(media.iter_files(path, incl_dirs=True)) + [path]:
        if os.path.isdir(file) and not os.listdir(file):
            media.remove_file(file)
        elif RE_DOWNLOAD_JUNK.search(file):
            media.remove_file(file)
        else:
            try:
                os.utime(file, None)
            except OSError:
                pass
            media.clean_file(file)

    if os.path.exists(path):
        return path

def get_downloads(path_root):
    '''Clean and get download sub directories.

    :return: directories list
    '''
    paths = []
    for path in list(media.iter_files(path_root,
            incl_files=False, incl_dirs=True)) + [path_root]:

        if media.get_type(path) == 'audio':
            album = {}
            extra = []
            for file in media.files(path, recursive=False):
                # Get album files
                if file.type == 'audio' and file.ext.lower() not in ('.m3u',):
                    album[file.file] = file.get_file_info()
                # Get extra files
                elif file.type == 'video' or (file.type == 'image' \
                        and media.get_size(file.file) > SIZE_ALBUM_IMAGE_MIN):
                    extra.append(file.file)
                else:
                    media.remove_file(file.file)

            path_dst = path
            if album:
                stat = {}
                for info in album.values():
                    def set_stat(key, force=False):
                        stat.setdefault(key, [])
                        val = info.get(key)
                        if val and (force or val not in stat[key]):
                            stat[key].append(val)
                    set_stat('title', True)
                    for key in ('artist', 'album', 'date', 'track_number'):
                        set_stat(key)

                if len(stat['title']) == len(stat['track_number']) == len(album):
                    # Rename tracks files
                    for file, info in album.items():
                        track_name = '%02d-%s-%s' % (info.get('track_number', 0), info['artist'], info['title'])
                        track_name = re.sub(r'\s+', '_', track_name).lower()
                        file_dst = os.path.join(path, track_name + os.path.splitext(file)[1])
                        media.rename_file(file, file_dst)

                # Get album directory name
                if len(stat['artist']) == len(stat['album']) == 1:
                    date_str = '-%s' % stat['date'][0] if len(stat['date']) == 1 else ''
                    album_name = '%s-%s%s' % (stat['artist'][0].capitalize(), stat['album'][0].capitalize(), date_str)
                    album_name = re.sub(r'\s+', '_', album_name)

                    # Rename extra files using the album name
                    for file in extra:
                        filename_extra = os.path.basename(file)
                        if not filename_extra.startswith('00-'):
                            file_dst = os.path.join(path, '00-%s-%s' % (album_name.lower(), filename_extra.lower()))
                            media.rename_file(file, file_dst)

                    # Rename album directory
                    path_dst = media.rename_file(path,
                            os.path.join(os.path.dirname(path_root), album_name))
                    paths.append(path_dst)

    if os.path.exists(path_root) and path_root not in paths:
        paths.append(path_root)
    return paths

def check_download_file(file, finished_file=None, finished=False):
    '''Check the file and its meta data.

    :param file: download file finished or incomplete
        (if incomplete, also pass the finished_file param)
    :param finished_file: finished file if the incomplete file
        has a different name (e.g.: '.part' extension)
    :param finished: True if the download is finished

    :return: True if the file is valid
    '''
    if not os.path.exists(file):
        return True

    file = media.get_file(file, real_file=finished_file)
    ext = getattr(file, 'real_ext', file.ext).lower()

    if file.type == 'archive':
        if file.is_main_file() and file.is_protected():
            logger.info('invalid archive %s: password protected', file.file)
            return False

    elif file.type == 'video':
        if not media.check_size(file.file, size_min=100):
            return True

        info = file.get_file_info()

        # Check extension
        if ext in ('.wmv', '.asf'):
            if info['season'] and info['episode']:
                logger.info('invalid extension "%s" for tvshow %s', ext, file.file)
                return False

        # Check duration
        if info.get('duration'):
            if not 15 < info['duration'] / 60 < 240:
                logger.info('invalid duration "%s" for %s', info['duration'], file.file)
                return False
        elif finished:
            logger.info('failed to get duration for %s', file.file)
            return False

        # Check bitrate
        if info.get('video_bitrate') and info.get('audio_bitrate'):
            if not 300 < info['video_bitrate'] / 1024 < 10000:
                logger.info('invalid video bitrate "%s" for %s', info['video_bitrate'], file.file)
                return False
            if not 30 < info['audio_bitrate'] / 1024 < 1000:
                logger.info('invalid audio bitrate "%s" for %s', info['audio_bitrate'], file.file)
                return False

        elif info.get('bitrate'):
            if not 300 < info['bitrate'] / 1024 < 10000:
                logger.info('invalid bitrate "%s" for %s', info['bitrate'], file.file)
                return False

        elif finished:
            logger.info('failed to get bitrate for %s', file.file)
            return False

    return True

def check_download(file):
    '''Check a download file or directory.
    '''
    for file in media.iter_files(file):
        if not check_download_file(file):
            return False
    return True
