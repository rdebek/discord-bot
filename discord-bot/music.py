from discord.ext import commands

from player import Player

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                  'options': '-vn'}


class Music(commands.Cog):
    def __init__(self, bot, color_theme):
        self.players = []
        self.bot = bot
        self.color_theme = color_theme

    async def get_player(self, ctx):
        for item in self.players:
            if item.guild == ctx.guild.id:
                return item
        player = Player(bot=self.bot, color_theme=self.color_theme, guild=ctx.guild.id)
        self.players.append(player)
        return player

    @commands.command(name="disconnect", aliases=["dc", "leave"])
    async def _disconnect(self, ctx):
        player = await self.get_player(ctx)
        await player._disconnect(ctx)

    @commands.command(name="clear")
    async def _clear(self, ctx):
        player = await self.get_player(ctx)
        await player._clear(ctx)

    @_disconnect.error
    async def disconnect_error(self, ctx, error):
        return await ctx.send("Couldn't leave for some reason.")

    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *args):
        player = await self.get_player(ctx)
        await player.play(ctx, *args)

    @play.error
    async def error(self, ctx, error):
        if "webpage" in str(error):
            return await ctx.send("You probably entered a invalid link, try again.")
        if "out of range" in str(error):
            return await ctx.send("Couldn't find the phrase you're looking for.")
        if "attribute" in str(error):
            return await ctx.send("Please be a little slower with the commands, I can't keep up.")
        else:
            raise error

    @commands.command(name="volume", aliases=["v"])
    async def _volume(self, ctx, volume: int):
        player = await self.get_player(ctx)
        await player._volume(ctx, volume)

    @commands.command(name="queue", aliases=["q"])
    async def _queue(self, ctx):
        player = await self.get_player(ctx)
        await player._queue(ctx)

    @commands.command(name="skip", aliases=["s"])
    async def _skip(self, ctx, *args):
        player = await self.get_player(ctx)
        await player._skip(ctx, *args)

    @commands.command(name="song", aliases=["now", "name"])
    async def _song(self, ctx):
        player = await self.get_player(ctx)
        await player._song(ctx)

    @commands.command(name="lyrics", aliases=[])
    async def _lyrics(self, ctx):
        player = await self.get_player(ctx)
        await player._lyrics(ctx)

    @_lyrics.error
    async def lyrics_error(self, ctx, error):
        if isinstance(error, commands.errors.CommandInvokeError):
            return await ctx.send("Lyrics couldn't be found.")
        else:
            raise error

    @commands.command(name="remove", aliases=["rm", "r"])
    async def _remove(self, ctx, song_number: int):
        player = await self.get_player(ctx)
        await player._remove(ctx, song_number)

    @commands.command(name="skip_to", aliases=["st"])
    async def _skip_to(self, ctx, song_number: int):
        player = await self.get_player(ctx)
        await player._skip_to(ctx, song_number)

    @_remove.error
    @_skip_to.error
    async def error(self, ctx, error):
        if isinstance(error, commands.errors.BadArgument):
            await ctx.send("Please give me a valid number ._.")
        else:
            raise error

    @commands.command(name="play_top", aliases=["pt"])
    async def _play_top(self, ctx, *args):
        player = await self.get_player(ctx)
        await player._play_top(ctx, *args)

    @commands.command(name="play_skip", aliases=["ps"])
    async def _play_skip(self, ctx, *args):
        player = await self.get_player(ctx)
        await player._play_skip(ctx, *args)

    @commands.command(name="shuffle", aliases=["randomize"])
    async def _shuffle(self, ctx):
        player = await self.get_player(ctx)
        await player._shuffle(ctx)

    @commands.command(name="pause", aliases=["stop"])
    async def _pause(self, ctx):
        player = await self.get_player(ctx)
        await player._pause(ctx)