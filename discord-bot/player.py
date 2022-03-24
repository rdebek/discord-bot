from random import shuffle

import discord
from discord.ext import tasks

import api_handler
import spotify
import text_cmds
import util

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                  'options': '-vn'}


class Player:
    def __init__(self, bot, color_theme, guild):
        self.guild = guild
        self.is_playing = False
        self.music_queue = []
        self.bot = bot
        self.vc = ""
        self.current_song = []
        self.music_volume = 0.5
        self.color_theme = color_theme
        self.spotify_flag = False
        self.current_song_tracked = None

    @tasks.loop(hours=3)
    async def afk_check(self, ctx):
        if (self.vc != "" and not self.vc.is_playing()) or not self.is_playing:
            await ctx.send(f"Disconnected from `{self.vc.channel}` due to inactivity.")
            await self.vc.disconnect()
            self.afk_check.stop()

    async def _disconnect(self, ctx):
        if not self.vc.is_connected():
            return await ctx.send("The bot is not connected to any voice channels.")
        if not ctx.author.voice:
            return await ctx.send("You are not in any voice channel.")
        if self.vc.channel != ctx.author.voice.channel:
            return await ctx.send(f"You are not in `{self.vc.channel}`, move over and try again.")
        else:
            await ctx.send("Ok, leaving now..")
            self.vc.stop()
            await self.vc.disconnect()
            self.vc = ""
            self.is_playing = False
            self.music_queue.clear()
            self.current_song = ""

    async def _clear(self, ctx):
        self.music_queue.clear()
        return await ctx.send("Queue has been cleared.")

    def play_next(self):
        if len(self.music_queue) > 0:

            self.is_playing = True
            url = self.music_queue[0][0]
            self.current_song = self.music_queue[0]
            self.music_queue.pop(0)
            self.current_song_tracked = AudioSourceTracked(discord.FFmpegPCMAudio(
                source=url,
                **FFMPEG_OPTIONS))

            self.vc.play(
                self.current_song_tracked, after=lambda e: self.play_next())
            self.vc.source = discord.PCMVolumeTransformer(self.vc.source, volume=self.music_volume)
        else:
            self.is_playing = False
            self.current_song = ""

    async def play_music(self, ctx):
        if len(self.music_queue) > 0:
            self.is_playing = True

            url = self.music_queue[0][0]
            self.current_song = self.music_queue[0]

            if self.vc == "" or not self.vc.is_connected():
                self.vc = await ctx.author.voice.channel.connect()
            else:
                await self.vc.move_to(ctx.author.voice.channel)

            self.music_queue.pop(0)

            self.current_song_tracked = AudioSourceTracked(
                discord.FFmpegPCMAudio(
                    source=url, **FFMPEG_OPTIONS))

            self.vc.play(self.current_song_tracked, after=lambda e: self.play_next())
            self.vc.source = discord.PCMVolumeTransformer(self.vc.source, volume=self.music_volume)

            if not self.afk_check.is_running():
                self.afk_check.start(ctx)
        else:
            self.is_playing = False
            self.vc.stop()

    async def play(self, ctx, *args):
        if not ctx.author.voice:
            return await ctx.send("You don't seem to be in a voice channel. Join one and try again.")
        if self.is_playing and ctx.author.voice.channel != self.vc.channel:
            return await ctx.send(
                f"You are not in `{self.vc.channel}` voice channel, join it or move the bot and try again.")

        if self.current_song and self.is_playing:
            helper = [self.current_song[2]]
            helper.extend([item[2] for item in self.music_queue])
            estimated_time = util.get_overall_duration(helper)
        else:
            estimated_time = util.get_overall_duration([item[2] for item in self.music_queue])

        self.spotify_flag = False
        if util.is_spotify_link(args[0]):
            with ctx.typing():
                spotify_instance = spotify.Spotify()
                song_info, embed = await spotify_instance.handle_spotify(args[0], ctx,
                                                                         discord.Embed(colour=self.color_theme))
                if not song_info:
                    return
                embed.add_field(name="Position in queue",
                                value=f"`{len(self.music_queue) + 1 if self.music_queue else 1}`", inline=True)
                embed.add_field(name="Estimated time until playing", value=f"`{estimated_time}`", inline=True)
                embed.add_field(name="Current volume", value=f"`{str(int(self.music_volume * 100)) + '%'}`",
                                inline=True)
                [song_info.remove(item) for item in song_info if item == ""]
                self.music_queue.extend(song_info)
                self.spotify_flag = True
                await ctx.send(embed=embed)

        if not self.spotify_flag and not util.is_yt_playlist(args):
            try:
                song_info = await util.get_yt_url(args, None)
                song_info.append(ctx.author)
                self.music_queue.append(song_info)
                embed = util.format_song_embed(discord.Embed(colour=self.color_theme), song_info, estimated_time,
                                               self.music_volume,
                                               len(self.music_queue))
                await ctx.send(embed=embed)
            except:
                return await ctx.send("An error occured (maybe the video is adult-only restricted).")
        elif not self.spotify_flag:
            msg = await ctx.send("Preparing the playlist..")
            individual_info, playlist_title, overall_duration = await util.parse_yt_playlist(args, msg)
            playlist_url, playlist_count, queue_pos = args[0], len(individual_info), len(self.music_queue) + 1
            for song in individual_info:
                song.append(ctx.author)
                self.music_queue.append(song)
            embed = util.format_yt_playlist_embed(discord.Embed(colour=self.color_theme), individual_info,
                                                  playlist_title,
                                                  overall_duration,
                                                  playlist_url, playlist_count, estimated_time, queue_pos,
                                                  self.music_volume)
            await ctx.send(embed=embed)

        if not self.is_playing or not self.vc.is_playing():
            await self.play_music(ctx)

    async def _volume(self, ctx, volume: int):
        if (self.vc != "" and not self.vc.is_playing()) or self.vc == "":
            return await ctx.send("Bot is not playing, so the volume cannot be changed.")
        if volume not in range(0, 101):
            return await ctx.send("Please give me a value between 0 and 100.")
        if self.is_playing and ctx.author.voice.channel != self.vc.channel:
            return await ctx.send(
                f"You are not in `{self.vc.channel}` voice channel, join it or move the bot and try again.")
        else:
            self.music_volume = volume / 100
            self.vc.source.volume = self.music_volume
            await ctx.send(f"Volume changed to {volume}%")

    async def _queue(self, ctx):
        if len(self.music_queue) < 1 and self.vc != "" and self.vc.is_playing():
            return await ctx.send(
                f"Sorry, the queue seems to be **empty**.\n**Current song**: `{self.current_song[1]}`")
        elif len(self.music_queue) < 1:
            return await ctx.send("Sorry, the queue is empty and nothing is playing.")
        else:
            embeds = util.format_queue_embed(self.music_queue, self.current_song[1], self.color_theme)
            text_cmds_instance = text_cmds.TextCmds(self.bot, self.color_theme)
            [embed.set_footer(text=f"Page: {embeds.index(embed) + 1}/{len(embeds)}", icon_url=ctx.author.avatar_url) for
             embed in embeds]
            message = await ctx.send(embed=embeds[0])

            while not text_cmds_instance.flag:
                await text_cmds_instance.handle_pages(ctx, message, embeds)

    async def _skip(self, ctx, *args):
        if self.is_playing and ctx.author.voice.channel != self.vc.channel:
            return await ctx.send(
                f"You are not in `{self.vc.channel}` voice channel, join it or move the bot and try again.")
        if args and args[0] == 'all':
            if self.vc != "" and self.vc.is_playing():
                await self._clear(ctx)
                return await self._skip(ctx)
            else:
                return await self._clear(ctx)
        if self.vc != "":
            if not self.vc.is_playing():
                await ctx.send("There's nothing to skip :(")
            else:
                await ctx.send("Skipped the song(s) 😎:pinched_fingers_tone5:")
                self.vc.stop()
        else:
            await ctx.send("Something went wrong.. ☠, perhaps the queue is empty")

    async def _song(self, ctx):
        if self.vc != "" and self.vc.is_playing():
            return await ctx.send(f"Currently playing: `{self.current_song[1]}`.")
        else:
            return await ctx.send(f"Nothing's playing 0_o")

    async def _lyrics(self, ctx):
        if self.vc == "" or not self.vc.is_playing():
            return await ctx.send("Nothing is playing right now.")
        async with ctx.typing():
            song_lyrics = api_handler.get_song_lyrics(self.current_song[1])
            embed = util.format_song_lyrics_embed(discord.Embed(colour=self.color_theme), self.current_song,
                                                  song_lyrics)
            return await ctx.send(embed=embed)

    async def _remove(self, ctx, song_number: int):
        song_number -= 1
        if song_number not in range(len(self.music_queue)):
            return await ctx.send(
                f"You didn't give me a valid number. Amount of songs in queue: `{len(self.music_queue)}`.")
        removed_song = self.music_queue.pop(song_number)
        return await ctx.send(f"`{removed_song[1]}` removed! :sunglasses:")

    async def _skip_to(self, ctx, song_number: int):
        song_number -= 1
        if song_number not in range(len(self.music_queue)):
            return await ctx.send(
                f"You didn't give me a valid number. Amount of songs in queue: `{len(self.music_queue)}`.")
        self.music_queue = self.music_queue[song_number:]
        await self._skip(ctx)
        return await ctx.send(f"Playing: `{self.music_queue[0][1]}`")

    async def _play_top(self, ctx, *args):
        if not args:
            return await ctx.send("You need to specify a song to be played.")
        if util.is_yt_playlist(args):
            return await ctx.send("Playlists aren't supported in this command yet.")
        if self.music_queue or (self.vc != "" and self.vc.is_playing()):
            self.music_queue.reverse()
            song_info = await util.get_yt_url(args, None)
            song_info.append(ctx.author)
            self.music_queue.append(song_info)
            self.music_queue.reverse()
            await ctx.send(embed=util.format_play_top_embed(discord.Embed(colour=self.color_theme),
                                                            song_info,
                                                            util.get_overall_duration([self.current_song[2]]),
                                                            self.music_volume))
        else:
            await ctx.send("Queue was empty, so the song has been placed on top of it.")
            await self.play(ctx, *args)

    async def _play_skip(self, ctx, *args):
        if not args:
            return await ctx.send("You need to specify a song to be played.")
        if self.current_song and self.vc != "" and self.vc.is_playing():
            self.current_song[2] = ""
            await self._play_top(ctx, *args)
            await self._skip(ctx)
        else:
            await self.play(ctx, *args)

    async def _shuffle(self, ctx):
        return await ctx.send(self.current_song_tracked.progress)
        if not self.music_queue:
            return await ctx.send("Queue is empty, so there is nothing to shuffle, try adding a few songs first.")
        else:
            shuffle(self.music_queue)
            return await ctx.send("The queue has been shuffled.")

    async def _pause(self, ctx):
        if self.is_playing and ctx.author.voice.channel != self.vc.channel:
            return await ctx.send(
                f"You are not in `{self.vc.channel}` voice channel, join it or move the bot and try again.")
        if self.vc.is_paused():
            self.vc.resume()
            return await ctx.send("Resumed.. 🎵")
        if self.vc != "" and not self.vc.is_playing():
            return await ctx.send("There is no song to pause.")
        self.vc.pause()
        return await ctx.send(
            f"The song is paused now.\nUse `{await self.bot.get_prefix(ctx.message)}pause` again to unpause.")


class AudioSourceTracked(discord.AudioSource):
    def __init__(self, source):
        self._source = source
        self.count_20ms = 0

    def read(self) -> bytes:
        data = self._source.read()
        if data:
            self.count_20ms += 1
        return data

    @property
    def progress(self) -> float:
        return self.count_20ms * 0.02
