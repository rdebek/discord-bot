import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import api_handler
import spotify_embeds
import util


class Spotify():
    def __init__(self):
        self.auth_manager = SpotifyClientCredentials()
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)

    @staticmethod
    def get_spotify_type(url):
        sliced_url = url.split("com")[1][1:]
        spotify_type = sliced_url[:sliced_url.index("/")]
        return spotify_type

    def handle_spotify(self, url, ctx, embed):
        spotify_type = self.get_spotify_type(url)
        if spotify_type == "playlist" or spotify_type == "album":
            return self.handle_playlist_album(url, ctx, embed)
        elif spotify_type == "track":
            return self.handle_track(url, ctx, embed)

    async def handle_playlist_album(self, url, ctx, embed):
        message = await ctx.send("Preparing the playlist..")
        overall_duration = 0
        songs_info = []
        if self.get_spotify_type(url) == "playlist":
            json = self.sp.playlist(url)
        else:
            json = self.sp.album(url)

        for item in json['tracks']['items']:
            item_before_change = item
            if self.get_spotify_type(url) == "playlist":
                item = item['track']
            song_info = await util.get_yt_url([item['artists'][0]['name'], item['name']], message, len(json['tracks']['items']))
            if song_info:
                songs_info.append(song_info)
                songs_info[json['tracks']['items'].index(item_before_change)][-1] = item['external_urls']['spotify']
                songs_info[json['tracks']['items'].index(item_before_change)].append(ctx.author)
                songs_info[json['tracks']['items'].index(item_before_change)][1] = f"{item['artists'][0]['name']} - {item['name']}"
                songs_info[json['tracks']['items'].index(item_before_change)][2] = int(item['duration_ms'] / 1000)
                overall_duration += item['duration_ms']
            else:
                songs_info.append("")
                await ctx.send(f"There was an issue with downloading `{item['artists'][0]['name']} - {item['name']}`..")
        await ctx.send("Done.")
        api_handler.clear_counter()
        return songs_info, spotify_embeds.playlist_album_embed(ctx, embed, json,
                                                               util.format_duration(int(overall_duration / 1000)))

    async def handle_track(self, url, ctx, embed):
        json = self.sp.track(url)
        song_name = json['name']
        artist = json['artists'][0]['name']
        song_info = await util.get_yt_url([artist, song_name])
        if song_info:
            song_info[-1] = json['external_urls']['spotify']
            song_info.append(ctx.author)
            return [song_info], spotify_embeds.track_embed(ctx, embed, song_info)
        else:
            await ctx.send("There was an error (probably it's an adult-only video on yt).")
            return False, False
