import re
from datetime import datetime
from urlparse import urlparse
import logging

from lxml import html

import trans


RE_EPISODE_LIST = [
    re.compile(r'\b(s?(\d{1,2})[ex](\d{2}))\b', re.I),
    re.compile(r'\b((\d{1,2})(\d{2}))\b', re.I),
    re.compile(r'\b(()part[\W_]*(\d+))\b', re.I),
    re.compile(r'\D(()(\d{1,2}))\b', re.I),
    ]
RE_AUDIO = re.compile(r'^((.*?)[\W_]*-[\W_]*(.*)|(\d{2,3})[\W_]*-[\W_]*(.*?)[\W_]*-[\W_]*(.*))$', re.I)
RE_SIZE = re.compile(r'([\d\.]+)\W*([tgmk])?i?b?\s*$', re.I)
LIST_JUNK_SEARCH = ['the', 'a', 'and', 's', 'le', 'la', 'un', 'une', 'us']
PATTERN_SEP_EXTRA = '([\(\[][^\)\]]*[\)\]])'
PATTERN_SEP_JUNK = '(%s)' % '|'.join(LIST_JUNK_SEARCH)
PATTERN_EXTRA = r'[\(\[\{].*?[\)\]\}]'
PATTERN_RIP_PRE = r'\d*[\W_]*(cd|dvd)[\W_]*\d*|pal|ntsc|(480|576|720|1080)[pi]'
PATTERN_RIP_MOVIES = r'blu[\W_]*ray|md|screener|ts|teaser|cam|r5|(bd|br|dvd|web|vod|dtt)rip|dvd[\W_]*(r|rip|scr)?|dvd\w*|(bd|br)[\W_]*scr'
PATTERN_RIP_TV = r'[hp]dtv|stv|tv[\W_]?rip|dvdrip'
PATTERN_RIP_FORMAT = r'ac3|xvid|divx|hd|[xh]264|rmvb'
PATTERN_RIP_EXTRA = r'ws|limited|final|proper|multi|repack([\W_]*\dcd)?|ld|hd'  # need PATTERN_RIP_MOVIES or PATTERN_RIP_TV to match
PATTERNS_LANGS = {
    'en': r'eng?(lish)?([\W_]*subs?(titles)?)?',
    'fr': r'(true|subs?[\W]?)?fr(e|ench)?([\W_]*subs?(titles)?)?()?|vostf?r?|vf',
    'sp': r'(sub)?esp|spa(nish)?([\W_]*subs?(titles)?)?',
    'ge': r'ger(man)?([\W_]*subs?(titles)?)?',
    'it': r'ita(liano?)?([\W_]*subs?(titles)?)?',
    'du': r'dutch([\W_]*subs?(titles)?)?',
    'nl': r'nl([\W_]*subs?(titles)?)?',
    'sw': r'swe([\W_]*subs?(titles)?)?',
    'ar': r'(subs?)?arab(ic)?([\W_]*subs?(titles)?)?',
    }
LANG_DEFAULT = 'en'     # default language when none found
SEARCH_MODE_MIN_CHARS = 8

logger = logging.getLogger(__name__)


def _clean_special(val):
    val = re.sub(r'[\n\r\t]+', '', val)
    val = re.sub(r'(&(nbsp|#160|#xA0);)+', ' ', val)    # replace no-break spaces

    # Remove html markup
    try:
        val = html.tostring(html.fromstring(val), method='text', encoding=unicode)
    except Exception:
        pass

    # Replace special characters (e.g.: accents)
    if not isinstance(val, unicode):
        val = val.decode('utf-8')
    val = val.encode('trans')

    return str(val).strip()

def clean(val, level=0):
    if not val:
        return ''
    val = _clean_special(val)

    if level >= 1:
        val = val.lower()

        # Remove brackets with text inside and everything after if there's text before
        if level >= 4:
            val = re.compile(r'(.+?)(%s.*$)' % PATTERN_EXTRA, re.I).sub(r'\1', val)

        # Remove brackets with text inside if there's text before or after
        if level >= 3:
            val = re.compile(r'(.+)%s' % PATTERN_EXTRA, re.I).sub(r'\1 ', val)
            val = re.compile(r'%s(.+)' % PATTERN_EXTRA, re.I).sub(r' \1', val)

        # Remove rip info and everything after an open bracket
        if level >= 5:
            val = re.compile(r'%s' % re.escape(get_rip(val)), re.I).sub('', val)
            val = re.compile(r'[\(\[\{<][^\)\]\}>]*$').sub('', val)

        # Replace non-word characters
        val = val.replace("'", '')
        val = ' '.join([w for w in re.split(r'[\W_]+', val) if w])

        # Remove every word from the last date
        # TODO: check the date is not preceded by a '-' or other separator
        if level >= 7:
            words = val.split()
            date_indexes = [i for i, w in enumerate(words) if is_year(w)]
            if date_indexes:
                val = ' '.join(words[:date_indexes[-1]])

        # Remove years
        if level >= 6:
            val = ' '.join([w for w in val.split() if not is_year(w)])

        # Get the most accurate name for media
        if level >= 9:
            title = Title(val)
            if title.episode:
                val = '%s %s%s' % (title.name, '%s ' % title.season or '', title.episode)
            else:
                val = title.name
    return val

def get_episode_info(title):
    '''Get episode info from a title.
    '''
    if is_movies(title) and not is_tv(title):
        return

    name = ''
    season = ''
    episode = ''
    episode_alt = ''
    extra = ''

    title = title.replace('_', ' ')     # to match regex '\b'
    res = []
    for re_episode in RE_EPISODE_LIST:
        r = re_episode.findall(title)
        if r:
            res += r

    if res:
        sep, season, episode = res[0]
        if is_year(sep):
            return

        name, extra = title.split(sep, 1)
        name = clean(name, 1)
        season = res[0][1].lstrip('0')
        if sep.isdigit():
            episode_alt = sep
        return name, season, episode, episode_alt, extra

def is_tv(title):
    return re.compile(PATTERN_RIP_TV, re.I).search(title) is not None

def is_movies(title):
    return re.compile(PATTERN_RIP_MOVIES, re.I).search(title) is not None

def get_rip(val):
    '''Get the rip info from a title.
    '''
    plang = '|'.join(PATTERNS_LANGS.values())
    p1 = r'((%s)[\W_]+)*([\W_]*%s[\W_]*)' % (plang, PATTERN_RIP_PRE)
    p2 = r'((%s)[\W_]+)*([\W_]*%s|%s[\W_]*)' % (plang, PATTERN_RIP_MOVIES, PATTERN_RIP_TV)
    p3 = r'((%s)[\W_]+)*([\W_]*%s[\W_]*)' % (plang, PATTERN_RIP_FORMAT)
    p4 = r'((%s)[\W_]+)*([\W_]*%s[\W_]*)' % (plang, PATTERN_RIP_EXTRA)

    rips = []
    for pattern in [r'%s[\W_]*%s' % (p4, p4), r'%s[\W_]*%s' % (p4, p2), p1, p2, p3]:
        res = re.compile(r'[\W_]%s([\W_].*$|$)' % pattern, re.I).search(val)
        if res:
            rips.append(res.group(0))

    if rips:
        return max(rips, key=len)
    return ''

def get_langs(val):
    langs = []
    for lang, pattern in PATTERNS_LANGS.items():
        if re.compile(r'(^|[\W_])(%s)([\W_]|$)' % pattern, re.I).search(val):
            langs.append(lang)
    if not langs:
        langs = [LANG_DEFAULT]
    return langs

def is_year(val):
    if val.isdigit() and 1950 <= int(val) <= datetime.utcnow().year + 1:
        return True

def get_year(val):
    for word in re.split(r'[\W_]+', val):
        if is_year(word):
            return int(word)

def is_url(val):
    if urlparse(val).scheme:
        return True

def get_size(val):
    '''Get the size in MB.
    '''
    res = RE_SIZE.search(val)
    if not res:
        logger.error('failed to get size from "%s"', val)
        return

    size, unit = res.groups()
    size = float(size)
    if not unit:
        size /= (1024 * 1024)
    elif unit.lower() == 'k':
        size /= 1024
    elif unit.lower() == 'g':
        size *= 1024
    elif unit.lower() == 't':
        size *= (1024 * 1024)
    return size

def get_words(val):
    return [w for w in re.split(r'[\W_]+', val.lower()) if w not in LIST_JUNK_SEARCH]


class Title(object):

    DEFAULTS = {
        'full_name': '',
        'name': '',
        'display_name': '',
        'rip': '',
        'date': None,
        'langs': [],
        'season': '',
        'episode': '',
        'episode_alt': '',
        'artist': '',
        'album': '',
        'track_number': '',
        'track_title': '',
        }

    def __init__(self, val, alt=None):
        self.title = val
        self.full_name = clean(val, 6)
        self.rip = get_rip(val)
        self.date = get_year(val)

        # Get episode info
        res = get_episode_info(val)
        if res:
            self.name, self.season, self.episode, self.episode_alt, rip = res
            if rip and len(rip) > len(self.rip):
                self.rip = rip
        else:
            self.name = self.full_name
            self.season = ''
            self.episode = ''
            self.episode_alt = ''

        if not self.season and len(self.episode) < 2:
            self.full_name = clean(val, 7)

        # Get audio info
        res = RE_AUDIO.search(clean(val))
        if res:
            groups = res.groups()
            self.artist = clean(groups[1], 6)
            self.album = clean(groups[2], 6)
            self.track_number = groups[3]
            self.track_title = clean(groups[5], 6)
            if not self.artist:
                self.artist = clean(groups[4], 6)

        # Get langs
        self.langs = get_langs(self.rip or val)

        # Set and clean attributes
        for a, v in self.DEFAULTS.items():
            if getattr(self, a, None) is None:
                setattr(self, a, v)

        # Check alternate items and update info
        if alt:
            if not isinstance(alt, (list, tuple)):
                alt = [alt]
            for i_alt in [self.__class__(s_alt) for s_alt in alt]:
                if len(i_alt.rip) > len(self.rip):
                    self.full_name = i_alt.full_name
                    self.name = i_alt.name
                    self.season = i_alt.season
                    self.episode = i_alt.episode
                    self.episode_alt = i_alt.episode_alt
                    self.date = i_alt.date
                    self.rip = i_alt.rip
                    break

                # Update langs
                self.langs.extend([l for l in i_alt.langs if l not in self.langs])

        # Remove default language if others exist
        if len(self.langs) > 1 and LANG_DEFAULT in self.langs:
            self.langs.remove(LANG_DEFAULT)

        # Handle anime episode
        if self.episode_alt and not is_tv(self.rip):
            self.season = ''
            self.episode = self.episode_alt

        # Get display name
        if self.episode:
            season_str = '%sx' % self.season if self.season else ''
            self.display_name = '%s %s%s' % (self.name, season_str, self.episode)
        else:
            self.display_name = self.full_name

    def __repr__(self):
        res = {}
        for attr in self.DEFAULTS:
            res[attr] = getattr(self, attr)
        return str(res)

    def _get_prev_episode(self):
        '''Get the previous season and episode for double episodes.
        '''
        season = self.season
        episode = self.episode

        if episode:
            episode = int(episode) - 1
            if episode < 0:
                episode = 99
                if season:
                    season = int(season) - 1
                    if season == -1:
                        season = 0

        episode = str(episode).zfill(len(self.episode))
        season = str(season).zfill(len(self.season))
        return season, episode

    def _get_search_mode(self, min_chars=SEARCH_MODE_MIN_CHARS):
        words = get_words(self.title)
        chars_count = len(''.join(words))
        if chars_count >= min_chars:
            return '__all__'
        return None

    def _get_separator_patterns(self, mode, category=None):
        '''Get words separators patterns.
        '''
        if mode == '__lazy__':
            p_begin = r'^.*'
            p_inside = r'.*'
            p_end = r'.*$'
        elif mode == '__all__':
            p_begin = r'(^|^.*[\W_])'
            p_inside = r'[\W_s]*%s*[\W_]*(%s[\W_]+)*' % (PATTERN_SEP_EXTRA, PATTERN_SEP_JUNK)
            p_end = r'([\W_].*$|$)'
        else:
            p_begin = r'^[\W_]*%s*[\W_]*(%s[\W_]+)*' % (PATTERN_SEP_EXTRA, PATTERN_SEP_JUNK)
            p_inside = r'[\W_s]*%s*[\W_]*(%s[\W_]+)*' % (PATTERN_SEP_EXTRA, PATTERN_SEP_JUNK)
            if self.episode or category == 'tv':
                p_end = r'([\W_].*$|$)'
            else:
                p_end = r'[\W_s]*%s*[\W_]*([\W_]%s)*[\W_]*$' % (PATTERN_SEP_EXTRA, PATTERN_SEP_JUNK)

        return p_begin, p_inside, p_end

    def get_search_pattern(self, mode=None, category=None, auto=False):
        '''Get a search regex pattern from a query.

        :param mode: search mode, possible values:
            - None: exact match
            - __all__: match phrase and other words
            - __lazy__: match all words without boundaries

        :return: pattern
        '''
        if auto:
            mode = self._get_search_mode()

        if self.episode:
            title = '%s %s%s' % (self.name, '%s ' % self.season if self.season else '', self.episode)
        else:
            title = self.title

        p_begin, p_inside, p_end = self._get_separator_patterns(mode, category)

        pattern = p_inside.join(get_words(title))
        pattern = re.sub(r's(%s|$)' % re.escape(p_inside), r"'?s?\1", pattern)

        if self.episode:
            s_prev, e_prev = self._get_prev_episode()
            p_year = '(\d{4})?%s' % p_inside
            if self.season:
                pattern = re.sub(r'(0?%s)%s(%s)' % (self.season, re.escape(p_inside), self.episode),
                        r'%s([^1-9]{,3}%s\D*%s\D[^1-9]*\1?\D*\2|[^1-9]{,3}\1\D*\2)' % (p_year, s_prev, e_prev),
                        pattern)
            else:
                pattern = re.sub(r'(%s)(%s)' % (re.escape(p_inside), self.episode),
                        r'%s\1([^1-9]{,3}%s[^1-9]{,3}\2|[^1-9]{,3}\2)' % (p_year, e_prev),
                        pattern)

        return r'%s%s%s' % (p_begin, pattern, p_end)

    def get_search_re(self, mode=None, category=None, auto=False):
        pattern = self.get_search_pattern(mode, category=category, auto=auto)
        return re.compile(pattern, re.I)
