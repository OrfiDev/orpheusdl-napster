from string import capwords
from urllib.parse import urlparse
from .napster_api import NapsterAPI
from utils.models import *


module_information = ModuleInformation(
    service_name = 'Napster',
    module_supported_modes = ModuleModes.download | ModuleModes.credits,
    session_settings = {'api_key': '', 'customer_secret': '', 'requested_netloc': '', 'username': '', 'password': ''},
    session_storage_variables = ['access_token', 'refresh_token', 'expiry_time', 'catalog_region', 'max_bitrate', 'hires_enabled'],
    netlocation_constant = 'setting.requested_netloc', 
    test_url = 'http://app.napster.com/artist/alan-walker/album/darkside-single/track/darkside',
    url_decoding = ManualEnum.manual
)


class ModuleInterface:
    def __init__(self, module_controller: ModuleController):
        self.module_controller = module_controller
        self.tsc = module_controller.temporary_settings_controller
        self.settings = module_controller.module_settings
        self.exception = module_controller.module_error
        self.session = NapsterAPI(module_controller.module_error, self.settings['api_key'], self.settings['customer_secret'])

        expiry_time = self.tsc.read('expiry_time')
        if expiry_time and module_controller.get_current_timestamp() > expiry_time:
            [self.tsc.set(i,j) for i,j in zip(['access_token', 'expiry_time'], \
                self.session.refresh_login(self.tsc.read('refresh_token'), module_controller.get_current_timestamp()))]
        else:
            self.session.access_token = self.tsc.read('access_token')
            self.session.catalog_region = self.tsc.read('catalog_region')

        self.quality_parse = { # could use lambda expressions here
            QualityEnum.MINIMUM: 64,
            QualityEnum.LOW: 128,
            QualityEnum.MEDIUM: 192,
            QualityEnum.HIGH: 320,
            QualityEnum.LOSSLESS: -1,
            QualityEnum.HIFI: -1
        }

        self.caches = {'artists': {}, 'genres': {}}

    def login(self, username, password):
        [self.tsc.set(i,j) for i,j in zip(['access_token', 'refresh_token', 'expiry_time', 'catalog_region', 'max_bitrate', 'hires_enabled'], \
            self.session.login(username, password, self.module_controller.get_current_timestamp()))]

    def custom_url_parse(self, url):
        url_parsed = urlparse(url)
        
        queries = {j:k for j,k in [i.split('=') for i in url_parsed.query.lower().split('&')]}
        if 'id' in queries:
            item_types = {
                'alb': DownloadTypeEnum.album,
                'tra': DownloadTypeEnum.track,
                'pp': DownloadTypeEnum.playlist,
                'mp': DownloadTypeEnum.playlist,
                'art': DownloadTypeEnum.artist
            }
            return MediaIdentification(item_types[queries['id'].split('.')[0]], queries['id'])
        else:
            path_components = url_parsed.path.split('/')
            if 'track' in path_components:
                item_type = DownloadTypeEnum.track
            elif 'album' in path_components:
                item_type = DownloadTypeEnum.album
            elif 'artist' in path_components:
                item_type = DownloadTypeEnum.artist
            elif 'playlist' in path_components:
                item_type = DownloadTypeEnum.playlist
            else:
                raise ValueError('Invalid URL')

            return MediaIdentification(item_type, '/'.join([i for i in path_components if i not in ['', 'track', 'album', 'artist', 'playlist']]))

    def search(self, query_type: DownloadTypeEnum, query, track_info: TrackInfo = None, limit = 10):
        results = []
        if track_info and track_info.tags.isrc: results = self.session.get_items_list('tracks/isrc', track_info.tags.isrc, item_string='tracks')
        if not results: results = self.session.search(query_type.name, query, limit)

        if query_type is DownloadTypeEnum.track:
            albums = self.session.get_items_dict('albums', [i['albumId'] for i in results])
            results = [(i, albums[i['albumId']]) for i in results] # bundle with album info
        elif query_type is DownloadTypeEnum.playlist:
            members = self.session.get_string_from_items_list('members', [i['links']['members']['ids'][0] for i in results], string_key='screenName')
            results = [(i, members[i['links']['members']['ids'][0]]) for i in results] # bundle with member name
        else:
            results = [(i, {}) for i in results]

        return [SearchResult(
                result_id = i['id'],
                name = i['name'],
                artists = [j if query_type is DownloadTypeEnum.playlist else i['artistName']] if query_type is not DownloadTypeEnum.artist else [],
                year = (j if query_type is DownloadTypeEnum.track else i)['modified' if query_type is DownloadTypeEnum.playlist else 'released']\
                    .split('-')[0] if query_type is not DownloadTypeEnum.artist else None,
                explicit = i.get('isExplicit'),
                extra_kwargs = {'data': {i['id']: i}, 'album_data': j} if query_type is DownloadTypeEnum.track else \
                    {'data': {i['id']: i}, 'member_name': j} if query_type is DownloadTypeEnum.playlist else {'data': {i['id']: i}}
            ) for i,j in results]

    def get_track_info(self, track_id, quality_tier: QualityEnum, codec_options: CodecOptions, data={}, album_data={}):
        track_data = data[track_id] if track_id in data else self.session.get_items_list('tracks', track_id)[0]
        if not album_data: album_data = self.session.get_items_list('albums', track_data['albumId'])[0]
        error = '' if track_data['isStreamable'] else 'Track is not streamable'

        if (quality_tier is QualityEnum.LOSSLESS or quality_tier is QualityEnum.HIFI) and not self.tsc.read('hires_enabled'): quality_tier = QualityEnum.HIGH
        requested_bitrate = self.quality_parse[quality_tier]
        max_bitrate = self.tsc.read('max_bitrate')
        if requested_bitrate > max_bitrate: requested_bitrate = max_bitrate

        if requested_bitrate == -1:
            bitrate = track_data['losslessFormats'][0]['bitrate']
            codec = track_data['losslessFormats'][0]['name']
            bit_depth = track_data['losslessFormats'][0]['sampleBits']
            sample_rate = track_data['losslessFormats'][0]['sampleRate']
        else:
            bitrate, codec, bit_depth, sample_rate = 0, '', 16, 44.1
            for i in track_data['formats']:
                if i['bitrate'] <= requested_bitrate and i['bitrate'] > bitrate and not (i['name'] == 'MQA' and not codec_options.proprietary_codecs):
                    bitrate = i['bitrate']
                    codec = i['name']
                    bit_depth = i['sampleBits']
                    sample_rate = i['sampleRate'] / 1000
            if bitrate == 0: error = 'No suitable bitrate found'

        if all(contributor in self.caches['artists'] for contributor in list(track_data['contributors'].values())):
            contributing_artists_data = {k:self.caches['artists'][v] for k,v in track_data['contributors'].items()}
        else:
            contributing_artists = self.session.get_string_from_items_list('artists', list(track_data['contributors'].values()), 'name')
            self.caches['artists'].update(contributing_artists)
            contributing_artists_data = {i:contributing_artists[j] for i,j in track_data['contributors'].items()}
        del contributing_artists_data['primaryArtist']

        artists = [track_data['artistName']]
        if 'nonPrimary' in contributing_artists_data and contributing_artists_data['nonPrimary'] not in artists:
            artists.append(contributing_artists_data['nonPrimary'])
        contributing_artists_data.pop('nonPrimary', None)

        genres_list = track_data['links']['genres']['ids']
        if all(genre in self.caches['genres'] for genre in genres_list):
            genres = {i:self.caches['genres'][i] for i in genres_list}
        else:
            genres = self.session.get_string_from_items_list('genres', genres_list, 'name')
            self.caches['genres'].update(genres)

        return TrackInfo(
            name = track_data['name'],
            album_id = track_data['albumId'],
            album = track_data['albumName'],
            artists = artists,
            codec = CodecEnum[codec.replace('AAC PLUS', 'HEAAC')] if codec else CodecEnum.NONE,
            cover_url = f'https://api.napster.com/imageserver/v2/albums/{track_data["albumId"]}/images/600x600.jpg',
            release_year = album_data['released'].split('-')[0],
            explicit = track_data['isExplicit'],
            artist_id = track_data['artistId'],
            bit_depth = bit_depth,
            sample_rate = sample_rate,
            bitrate = bitrate,
            download_extra_kwargs = {'bitrate': bitrate, 'codec': codec, 'track_id': track_data['id']},
            credits_extra_kwargs = {'contributing_artists': contributing_artists_data},
            error = error,
            tags = Tags(
                album_artist = album_data['artistName'],
                composer = contributing_artists_data.get('composer'),
                track_number = track_data['index'],
                total_tracks = album_data['trackCount'],
                copyright = album_data['copyright'],
                isrc = track_data['isrc'],
                upc = album_data['upc'],
                disc_number = track_data['disc'],
                total_discs = album_data['discCount'],
                genres = list(genres.values())
            )
        )

    def get_track_download(self, bitrate, codec, track_id):
        return TrackDownloadInfo(
            download_type = DownloadEnum.URL,
            file_url = self.session.get_stream_url(bitrate, codec, track_id)
        )

    def get_album_info(self, album_id, data={}):
        album_data = data[album_id] if album_id in data else self.session.get_items_list('albums', album_id)[0]
        tracks = self.session.get_items_dict('albums', album_data['id'], 'tracks', 'tracks', 200)

        image_type = self.module_controller.orpheus_options.default_cover_options.file_type
        return AlbumInfo(
            name = album_data['name'],
            artist = album_data['artistName'],
            tracks = list(tracks.keys()),
            release_year = album_data['released'].split('-')[0],
            explicit = album_data['isExplicit'],
            artist_id = album_data['contributingArtists']['primaryArtist'],
            cover_url = f'https://api.napster.com/imageserver/v2/albums/{album_data["id"]}/images/600x600.{image_type.name}',
            cover_type = image_type,
            all_track_cover_jpg_url = f'https://api.napster.com/imageserver/v2/albums/{album_data["id"]}/images/600x600.jpg',
            track_extra_kwargs = {'data': tracks, 'album_data': album_data},
        )

    def get_playlist_info(self, playlist_id, data={}, member_name=''):
        playlist_data = data[playlist_id] if playlist_id in data else self.session.get_items_list('playlists', playlist_id)[0]
        if not member_name: member_name = self.session.get_items_list('members', playlist_data['links']['members']['ids'][0])[0]['screenName']
        tracks = self.session.get_items_dict('playlists', playlist_data['id'], 'tracks', 'tracks', 200)

        image_type = self.module_controller.orpheus_options.default_cover_options.file_type
        return PlaylistInfo(
            name = playlist_data['name'],
            creator = member_name,
            tracks = list(tracks.keys()),
            release_year = playlist_data['modified'].split('-')[0],
            creator_id = playlist_data['links']['members']['ids'][0],
            cover_url = f'https://api.napster.com/imageserver/v2/playlists/{playlist_data["id"]}/artists/images/1800x600.{image_type.name}' \
                if playlist_data['images'] else None,
            cover_type = image_type,
            track_extra_kwargs = {'data': tracks}
        )

    def get_artist_info(self, artist_id, get_credited_albums, data={}):
        artist_data = self.session.get_items_list('artists', artist_id)[0] # search doesn't return all albums
        albums_list = artist_data['albumGroups']['main'] + artist_data['albumGroups']['singlesAndEPs']
        album_data = self.session.get_items_dict('albums', albums_list)

        return ArtistInfo(
            name = artist_data['name'],
            albums = albums_list,
            album_extra_kwargs = {'data': album_data}
        )

    def get_track_credits(self, track_id, contributing_artists={}):
        return [CreditsInfo(capwords(''.join(' ' + c if c.isupper() else c for c in k)), [v]) for k, v in contributing_artists.items()]
