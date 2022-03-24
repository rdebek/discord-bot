import util


def playlist_album_embed(ctx, embed, json, overall_duration):
    author = ctx.author
    image_url = json['images'][0]['url']
    playlist_name = json['name']
    playlist_length = len(json['tracks']['items'])
    embed.set_thumbnail(url=image_url)
    embed.set_author(name=f"{util.check_if_has_nick(author)} added a playlist to the queue",
                     icon_url=author.avatar_url)
    embed.description = f"[**{playlist_name}**]({json['external_urls']['spotify']})"
    embed.add_field(name="Playlist duration", value=f"`{overall_duration}`", inline=True)
    embed.add_field(name="Amount of songs", value=f"`{playlist_length}`", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    return embed


def track_embed(ctx, embed, song_info):
    author = ctx.author
    embed.set_author(name=f"{util.check_if_has_nick(author)} added a song to the queue",
                     icon_url=author.avatar_url)
    embed.description = f"[**{song_info[1]}**]({song_info[4]})"
    embed.add_field(name="Song duration", value=f"`{util.format_duration(song_info[2])}`", inline=True)
    embed.set_thumbnail(url=song_info[3])
    return embed




