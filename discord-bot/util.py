import asyncio
import datetime
import random

import discord
import youtube_dl
# import yt-dlp as youtube_dl

YDL_OPTIONS = {'format': 'bestaudio/best',
               'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
               'restrictfilenames': True,
               'noplaylist': False,
               'nocheckcertificate': True,
               'ignoreerrors': False,
               'logtostderr': False,
               'quiet': True,
               'no_warnings': True,
               'default_search': 'auto',
               'source_address': '0.0.0.0'}


def format_description_string(group_name: str, dictionary: {}):
    return f"**{group_name.upper()} COMMANDS**\n\n" + "".join(
        ["  **" + x + "** - " + dictionary[x] + "\n\n" for x in dictionary])


def format_help_command():
    text_cmds_with_descriptions = {}
    music_cmds_with_descriptions = {}
    utility_cmds_with_descriptions = {}
    money_cmds_with_descriptions = {}

    text_cmds_with_descriptions["kanye_wisdom"] = "returns a quote by Kanye West himself"
    text_cmds_with_descriptions["regular_wisdom"] = "returns a inspirational quote.. not by Kanye West though"
    text_cmds_with_descriptions["weather <city>"] = "returns the current temperature in a given <city>"
    text_cmds_with_descriptions["im_bored"] = "returns an activity for you to do when bored"
    text_cmds_with_descriptions["nasa_pic"] = "returns a random 'picture of the day' from NASA"
    text_cmds_with_descriptions["ascii"] = "returns a random ASCII art"
    text_cmds_with_descriptions["crypto"] = "retrieves information about certain cryptocurrencies"

    music_cmds_with_descriptions[
        "play"] = "plays a song from youtube or spotify, input can either be an url or the name of the song, playlists are also supported"
    music_cmds_with_descriptions["skip/skip all"] = "skips a song/skips all songs"
    music_cmds_with_descriptions["volume <0-100>"] = "changes current volume to <0-100%>"
    music_cmds_with_descriptions["queue"] = "shows current status of the queue"
    music_cmds_with_descriptions["disconnect"] = "disconnects the bot from current voice channel"
    music_cmds_with_descriptions["song"] = "displays current song"
    music_cmds_with_descriptions["lyrics"] = "displays lyrics for current song"
    music_cmds_with_descriptions["play_top <song>"] = "places the <song> on top of the queue"
    music_cmds_with_descriptions["shuffle"] = "shuffles songs in the queue"
    music_cmds_with_descriptions[
        "play_skip <song>"] = "places the <song> on top of the queue and skips the song that is currently playing"
    music_cmds_with_descriptions[
        "skip_to <song_id>"] = "skips to a given song in queue, use `queue` to get the desired song_id"
    music_cmds_with_descriptions[
        "remove <song_id>"] = "removes a song from the queue, use `queue` to get the desired song id"
    music_cmds_with_descriptions["clear"] = "clears the queue"

    utility_cmds_with_descriptions["help"] = "you should know that one"
    utility_cmds_with_descriptions["change_prefix"] = "allows the user to change the bot prefix"
    # utility_cmds_with_descriptions["change_color <0-255> <0-255> <0-255>"] = \
    #     "allows the user to change the bot theme color, " \
    #     "supply the command with R, G, B values separated by spaces"
    utility_cmds_with_descriptions["aliases <command>"] = "displays aliases for the chosen command"

    money_cmds_with_descriptions["blackjack <money>"] = "play a game of blackjack for amount of <money>"
    money_cmds_with_descriptions["gamble <money>"] = "gamble amount of <money>, chances are 50/50"
    money_cmds_with_descriptions["balance"] = "allows you to check your account balance"

    text_cmds_embed_description = format_description_string('text', text_cmds_with_descriptions)
    music_embed_description = format_description_string('music', music_cmds_with_descriptions)
    utility_cmds_embed_description = format_description_string('utility', utility_cmds_with_descriptions)
    money_cmds_embed_description = format_description_string('money', money_cmds_with_descriptions)

    return text_cmds_embed_description, music_embed_description, utility_cmds_embed_description, money_cmds_embed_description


def get_weather_emoji(weather, time_shift):
    if (datetime.datetime.utcnow() + datetime.timedelta(seconds=time_shift)).hour not in range(8, 21):
        return ":waxing_gibbous_moon:"
    if weather == 'Clear':
        return ":sunny:"
    if weather == 'Thunderstorm':
        return ":thunder_cloud_rain:"
    if weather == 'Drizzle':
        return ":cloud_rain:"
    if weather == 'Rain':
        return ":white_sun_rain_cloud:"
    if weather == 'Snow':
        return ":cloud_snow: :snowflake:"
    if weather in ['Mist', 'Smoke', 'Haze', 'Dust', 'Fog', 'Sand', 'Ash', 'Squall', 'Tornado']:
        return ":fog:"
    if weather == 'Clouds':
        return ":white_sun_cloud:"
    return ""


def get_rand_emote_combo():
    emotes = ['😈', '😡', '😩', '😱', '🤓', '😎', '🥵', '😔', '🤔', '🥰', '☠', '🤡']
    hand_gestures = ['👌', '👍', '✊', '🤝', '👀', '👊']
    return emotes[random.randint(0, len(emotes) - 1)] + " " + hand_gestures[random.randint(0, len(hand_gestures) - 1)]


def parse_city(message):
    city = ''
    tab = message.content.split()
    for x in range(1, len(tab)):
        city += tab[x]
        if x < len(tab) - 1:
            city += " "
    return city


async def get_yt_url(search_terms: [], message=None, playlist_length=0):
    if search_terms[0].startswith('http'):
        url = search_terms[0]
        return get_yt_info_from_url(url)
    else:
        import api_handler
        url = await api_handler.get_yt_url_from_search("%20".join(search_terms), message, playlist_length)
        return get_yt_info_from_url(url)


def get_yt_info_from_url(url):
    try:
        info = youtube_dl.YoutubeDL(YDL_OPTIONS).extract_info(url, download=False)
    except youtube_dl.DownloadError:
        return
    if info['duration'] == 0.0:
        title = crop_stream_title(info['title'])
    else:
        title = info['title']
    return [info['formats'][0]['url'], title, info['duration'], info['thumbnail'], url]


async def parse_yt_playlist(playlist_url, msg=None):
    counter = 0
    individual_songs_info = []
    playlist_info = youtube_dl.YoutubeDL(YDL_OPTIONS).extract_info(playlist_url[0], download=False)
    for entry in playlist_info['entries']:
        song_info = get_yt_info_from_url("https://www.youtube.com/watch?v=" + entry['id'])
        if song_info:
            individual_songs_info.append(song_info)
            counter += 1
            await msg.edit(content=f"Preparing the playlist, loaded: `{counter}` songs.")

    overall_duration = get_overall_duration([item[2] for item in individual_songs_info])
    playlist_title = playlist_info['entries'][0]['playlist_title']
    return individual_songs_info, playlist_title, overall_duration


def get_overall_duration(array_of_durations):
    if array_of_durations and array_of_durations != ['']:
        return format_duration(int(sum(array_of_durations)))
    return "Now!"


def crop_stream_title(title):
    return title[:-17]


def is_yt_playlist(url):
    if url[0].startswith('http') and 'list' in url[0]:
        return True
    else:
        return False


def is_spotify_link(url):
    return "open.spotify" in url


def format_duration(duration_in_secs):
    if duration_in_secs == 0.0:
        return "Endless stream"
    if duration_in_secs / 3600 >= 1:
        return_str = str(
            f"{int(duration_in_secs / 3600)}:{int((duration_in_secs % 3600) / 60)}:{(duration_in_secs % 3600) % 60}")
    else:
        return_str = str(f"{int(duration_in_secs / 60)}:{duration_in_secs % 60}")
    if len(return_str[return_str.rfind(':'):]) < 3:
        return_str = return_str[:return_str.rfind(':') + 1] + '0' + return_str[return_str.rfind(':') + 1:]
    if ':' in return_str[return_str.find(':') + 1:return_str.find(':') + 3]:
        return_str = return_str[:return_str.find(':') + 1] + '0' + return_str[return_str.find(':') + 1:]
    return return_str


def format_song_embed(embed, song_info, estimated_time, music_volume, queue_pos):
    embed.set_author(name=f"{check_if_has_nick(song_info[5])} added a song to the queue",
                     icon_url=song_info[5].avatar_url)
    embed.description = f"[**{song_info[1]}**]({song_info[4]})"
    embed.add_field(name="Song duration", value=f"`{format_duration(song_info[2])}`", inline=True)
    embed.add_field(name="Position in queue", value=f"`{queue_pos}`", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="Estimated time until playing", value=f"`{estimated_time}`", inline=True)
    embed.add_field(name="Current volume", value=f"`{str(int(music_volume * 100)) + '%'}`", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.set_thumbnail(url=song_info[3])
    return embed


def check_if_has_nick(author):
    return author.nick if author.nick else author.name


def format_yt_playlist_embed(embed, individual_info, playlist_title, overall_duration, playlist_url, playlist_count,
                             estimated_time, queue_pos, music_volume):
    embed.set_author(name=f"{check_if_has_nick(individual_info[0][5])} added a playlist to the queue",
                     icon_url=individual_info[0][5].avatar_url)
    embed.description = f"[**{playlist_title}**]({playlist_url})"
    embed.add_field(name="Playlist duration", value=f"`{overall_duration}`", inline=True)
    embed.add_field(name="Amount of songs", value=f"`{playlist_count}`", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="Position in queue", value=f"`{queue_pos}`", inline=True)
    embed.add_field(name="Estimated time until playing", value=f"`{estimated_time}`", inline=True)
    embed.add_field(name="Current volume", value=f"`{str(int(music_volume * 100)) + '%'}`", inline=True)
    embed.set_thumbnail(url=individual_info[0][3])
    return embed


def format_queue_embed(music_queue, current_song, color_theme):
    i = 1
    p = 0
    embeds = [discord.Embed() for i in range(int(len(music_queue)/10) + 1)]
    for embed in embeds:
        embed.title = f"Currently playing:\n{current_song}"
        embed.description = "**Queue:**"
        embed.colour = color_theme

    for song in music_queue:
        if(len(embeds[p].fields)) == 10:
            p += 1
        embeds[p].add_field(name=f"{str(i)}. {song[1]}",
                        value=f"song link: [**link**]({song[4]})\n requested by: **{check_if_has_nick(song[5])}**",
                        inline=False)
        i += 1
    [embed.add_field(value=f"**queue length:** `{get_overall_duration([x[2] for x in music_queue])}\n`**amount of songs in the queue:** `{len(music_queue)}`",
                    name="\u200b", inline=False) for embed in embeds]
    if len(embeds[-1].fields) == 1:
        embeds.pop()
    return embeds


def format_song_lyrics_embed(embed, song, song_lyrics):
    embed.title = song[1]
    embed.set_thumbnail(url=song[3])
    embed.description = song_lyrics
    return embed


def format_play_top_embed(embed, song_info, estimated_time, music_volume):
    embed.set_author(name=f"{check_if_has_nick(song_info[5])} added a song on TOP of the queue",
                     icon_url=song_info[5].avatar_url)
    embed.description = f"[**{song_info[1]}**]({song_info[4]})"
    embed.add_field(name="Song duration", value=f"`{format_duration(song_info[2])}`", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="Estimated time until playing", value=f"`{estimated_time}`", inline=True)
    embed.add_field(name="Current volume", value=f"`{str(int(music_volume * 100)) + '%'}`", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.set_thumbnail(url=song_info[3])
    return embed


async def get_emoji(ctx, msg, emotes_arr, bot):

    def check(payload):
        return payload.message_id == msg.id and str(payload.emoji) in emotes_arr and payload.member == ctx.author

    try:
        payload = await bot.wait_for("raw_reaction_add", timeout=30, check=check)
        await msg.remove_reaction(payload.emoji, ctx.author)
        return payload.emoji
    except asyncio.TimeoutError:
        await msg.clear_reactions()
        await msg.delete()
