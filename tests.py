#!/usr/bin/env python
import unittest
import logging

from mock import patch, Mock

from filetools.title import Title, clean, get_episode_info, get_size


logging.basicConfig(level=logging.DEBUG)


#
# Title
#

# TODO
# class TitleCleanTest(unittest.TestCase):

#     def setUp(self):
#         self.fixtures = [
#             ('Artist_Name_-_Album_Name_-_2012_-_TEAM',
#                 'artist name', 'album name', 2012),
#             ('Artist_Name-Album_Name-2012-TEAM',
#                 'artist name', 'album name', 2012),
#             ('07-Artist_Name-Album_Name.mp3',
#                 'artist name', 'album name', 2012),
#             ]

#     def test_clean_special(self):
#         pass


class TitleMovieTest(unittest.TestCase):

    def setUp(self):
        self.fixtures = [
            ('movie name DVDrip XviD TEAM',
                'movie name', '', '', '', ' DVDRip XviD TEAM'),
            ('movie name BRRip XviD TEAM',
                'movie name', '', '', '', ' BRRip XviD TEAM'),
            ('movie name 2012 DVDrip XviD TEAM',
                'movie name', '', '', '', ' 2012 DVDRip XviD TEAM'),
            ('movie name (2012) DVDrip',
                'movie name', '', '', '', ' DVDRip'),
            ('movie name 2012 LIMITED BDRip XviD TEAM',
                'movie name', '', '', '', ' LIMITED BDRip XviD TEAM'),
            ('movie name LIMITED BDRip XviD TEAM',
                'movie name', '', '', '', ' LIMITED BDRip XviD TEAM'),
            ('4.44.Last.Day.On.Earth.2011.VODRiP.XViD.AC3-MAJESTiC',
                '4 44 last day on earth', '', '', '', '.VODRiP.XViD.AC3-MAJESTiC'),
            ('movie name 312 LIMITED BDRip XviD TEAM',
                'movie name 312', '', '', '', ' LIMITED BDRip XviD TEAM'),
            ('11 flowers',
                '11 flowers', '', '', '', ''),
            ]

    def test_episode_info(self):
        for title, name, season, episode, episode_alt, rip in self.fixtures:
            res = get_episode_info(title)

            self.assertEqual(res, None)

    def test_title(self):
        for title, name, season, episode, episode_alt, rip in self.fixtures:
            res = Title(title)

            self.assertEqual(res.name, name)
            self.assertEqual(res.season, season)
            self.assertEqual(res.episode, episode)


class TitleTvTest(unittest.TestCase):

    def setUp(self):
        self.fixtures = [
            ('show name s03e02 HDTV XviD TEAM',
                'show name', '3', '02', '', ' HDTV XviD TEAM', '3', '02'),
            ('Show Name S03E02 HDTV XviD TEAM',
                'show name', '3', '02', '', ' HDTV XviD TEAM', '3', '02'),
            ('show name s03e02-03 HDTV XviD TEAM',
                'show name', '3', '02', '', '-03 HDTV XviD TEAM', '3', '02'),
            ('show name s03e02',
                'show name', '3', '02', '', '', '3', '02'),
            ('show name 3x02',
                'show name', '3', '02', '', '', '3', '02'),
            ('show name 11 3x02',
                'show name 11', '3', '02', '', '', '3', '02'),
            ('show name 11 3X02',
                'show name 11', '3', '02', '', '', '3', '02'),
            ('show name 111 3x02',
                'show name 111', '3', '02', '', '', '3', '02'),
            ('show name 102 1998 3x02',
                'show name 102 1998', '3', '02', '', '', '3', '02'),
            ('show name 1998-2008 3x02',
                'show name 1998 2008', '3', '02', '', '', '3', '02'),
            ('show name 302',
                'show name', '3', '02', '302', '', '', '302'),
            ('show name 11 302',
                'show name 11', '3', '02', '302', '', '', '302'),
            ('show name part 2 HDTV XviD TEAM',
                'show name', '', '2', '', ' HDTV XviD TEAM', '', '2'),
            ('show name part2 HDTV XviD TEAM',
                'show name', '', '2', '', ' HDTV XviD TEAM', '', '2'),
            ('show name 2013 s01e03 HDTV XviD TEAM',
                'show name 2013', '1', '03', '', ' HDTV XviD TEAM', '1', '03'),

            ('anime name 002',
                'anime name', '', '02', '002', '', '', '002'),
            ('anime name 02',
                'anime name', '', '02', '02', '', '', '02'),
            ('anime name 302',
                'anime name', '3', '02', '302', '', '', '302'),
            ('Naruto_Shippuuden_-_261_[480p]',
                'naruto shippuuden', '2', '61', '261', ' [480p]', '', '261'),
            ]

    def test_episode_info(self):
        for title, name, season, episode, episode_alt, rip, real_season, real_episode in self.fixtures:
            res = get_episode_info(title)

            self.assertEqual(res, (name, season, episode, episode_alt, rip))

    def test_title(self):
        for title, name, season, episode, episode_alt, rip, real_season, real_episode in self.fixtures:
            res = Title(title)

            self.assertEqual(res.name, name)
            self.assertEqual(res.season, real_season)
            self.assertEqual(res.episode, real_episode)


class PreviousEpisodeTest(unittest.TestCase):

    def setUp(self):
        self.fixtures = [
            ('show name 1x23', '1', '22'),
            ('show name s01e03', '1', '02'),
            ('show name 1x01', '1', '00'),
            ('show name s02e01', '2', '00'),
            ('show name 123', '', '122'),
            ('show name 100', '', '099'),
            ]

    def test_previous_episode(self):
        for query, season, episode in self.fixtures:
            res = Title(query)._get_prev_episode()

            self.assertEqual(res, (season, episode))


class TitleSearchTest(unittest.TestCase):

    def setUp(self):
        self.fixtures_tv = [
            ('show name', '.show.name.'),
            ('show name', 'the.show.name.'),
            ('show name', 'the show\'s name'),
            ('show name', 'the the show\'s and the names'),
            ('show name', 'SHOW NAME'),
            ('show name', 'show\'s name\'s'),
            ('show name 2011', 'show name 2011'),
            ('show name 20x11', 'show name s20e11'),
            ('show name 1x23', 'show name s01e23'),
            ('show name 01x23', 'show name s01e23'),
            ('show name 1x23', 'show name s01e23 episode title'),
            ('show name 1x23', 'show name s01e22-23 episode title'),
            ('show name 1x23', 'show name s01e23-24 episode title'),
            ('show name 78 1x23', 'show name 78 s01e23 episode title'),
            ('show name 23 1x23', 'show name 23 s01e23 episode title'),
            ('show name 1x23', 'show name 2013 s01e23 episode title'),

            ('anime name 123', '[TEAM]_Anime_Name-123_[COMMENT]'),
            ('anime name 123', '[TEAM]_Anime_Name-0123_[COMMENT]'),
            ('anime name 123', '[TEAM]_Anime_Name-ep123_[COMMENT]'),
            ]

        self.fixtures_tv_err = [
            ('show name', '.show.name2.'),
            ('show name', 'that.show.name.'),
            ('show name', 'SHOWS NAMEZ'),
            ('show name 2011', 'show name 2012'),
            ('show name 20x11', 'show name s20e12'),
            ('show name 1x23', 'show name s1e24'),
            ('show name 01x23', 'show name s01e24'),
            ('show name 1x23', 'show name s02e23 episode title'),

            ('anime name 123', '[TEAM]_Anime_Name-124_[COMMENT]'),
            ('anime name 123', '[TEAM]_Anime_Name-1123_[COMMENT]'),
            ('anime name 123', '[TEAM]_Anime_Name-23_[COMMENT]'),
            ]

        self.fixtures_movies = [
            ('my movie name', 'my.movie.name.2012.DVDRip.XviD-TEAM'),
            ('movie name', 'the.movie.name.2012.DVDRip.XviD-TEAM'),
            ('my movie name', 'My.Movie.Name.2012.DVDRip.XviD-TEAM'),
            ('my movie name', 'My.Movie\'s.Name.2012.DVDRip.XviD-TEAM'),
            ]

        self.fixtures_movies_err = [
            ('my movie name', 'My.Other.Movie.Name.2012.DVDRip.XviD-TEAM'),
            ]

    def test_search_tv(self):
        for query, title in self.fixtures_tv:
            res = Title(query).get_search_re()

            self.assertTrue(res.search(title), '"%s" (%s) should match "%s"' % (query, res.pattern, title))

        for query, title in self.fixtures_tv_err:
            res = Title(query).get_search_re()

            self.assertFalse(res.search(title), '"%s" (%s) should not match "%s"' % (query, res.pattern, title))

    def test_search_movies(self):
        for query, title in self.fixtures_movies:
            res = Title(query).get_search_re(mode='__all__')

            self.assertTrue(res.search(title), '"%s" (%s) should match "%s"' % (query, res.pattern, title))

        for query, title in self.fixtures_movies_err:
            res = Title(query).get_search_re(mode='__all__')

            self.assertFalse(res.search(title), '"%s" (%s) should not match "%s"' % (query, res.pattern, title))


class SizeTest(unittest.TestCase):

    def setUp(self):
        self.fixtures = [
            ('123', 123.0 / 1024 / 1024),
            ('123 B', 123.0 / 1024 / 1024),
            ('-123 B', 123.0 / 1024 / 1024),
            ('123 KiB', 123.0 / 1024),
            ('123 KB', 123.0 / 1024),
            ('123 K', 123.0 / 1024),
            ('123 MiB', 123),
            ('123 MB', 123),
            ('123 M', 123),
            ('123 GiB', 123 * 1024),
            ('123 GB', 123 * 1024),
            ('123 G', 123 * 1024),
            ]

    def test_size(self):
        for val, expected in self.fixtures:
            res = get_size(val)
            self.assertEqual(res, expected)


if __name__ == '__main__':
    unittest.main()
