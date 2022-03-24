import asyncio
import datetime
import os

import discord
import psycopg2
from discord.ext import commands, tasks
from fuzzywuzzy import process

import api_handler
import blackjack
import music
import plots
import text_cmds
import util

discord_token = api_handler.discord_token
prefix = '$'
bot_color_theme = discord.colour.Colour.from_rgb(128, 0, 255)
client = commands.Bot(command_prefix=prefix, case_insensitive=True, help_command=None)
role_name = 'D-J'


connection = psycopg2.connect(os.environ['DATABASE_URL'])
cur = connection.cursor()


def get_prefix(bot, message):
    global prefix
    guild_id = message.guild.id
    cur.execute(f"SELECT exists (SELECT 1 FROM guilds WHERE guild_id = '{guild_id}' LIMIT 1);")
    if not cur.fetchone()[0]:
        prefix = '$'
        cur.execute(f"INSERT INTO guilds VALUES({guild_id}, '{prefix}')")
        connection.commit()

    else:
        cur.execute(f"SELECT prefix FROM guilds WHERE guild_id = '{guild_id}'")
        prefix = cur.fetchone()[0]
    return prefix


client.command_prefix = get_prefix


@client.event
async def on_ready():
    called_once_a_day.start()
    game = discord.Game("Use 'help' for help")
    await client.change_presence(status=discord.Status.online, activity=game)


@client.event
async def on_guild_join(guild):
    text_channel = guild.text_channels[0]
    embed = discord.Embed(description='The default prefix is `$`, if you want to change it, use `$prefix`.\nFor list of available commands use `$help`.\nHave fun!', color=bot_color_theme)
    embed.set_author(name='Thank you for adding me to your server! :]')
    await text_channel.send(embed=embed)


@client.event
async def on_command_error(ctx, error):
    def check(reaction, user):
        return ctx.author == user and (str(reaction.emoji) == "👍" or str(reaction.emoji) == "👎") and return_msg == reaction.message

    if hasattr(ctx.command, 'on_error'):
        return
    if isinstance(error, commands.CommandNotFound):
        closest_command, probability = process.extractOne(ctx.invoked_with, [item.name for item in client.commands])
        if probability > 50:
            return_msg = await ctx.send(f"That command doesn't exist, did you mean `{prefix}{closest_command}`?")
            await return_msg.add_reaction("👍")
            await return_msg.add_reaction("👎")
            try:
                reaction, user = await client.wait_for("reaction_add", timeout=30, check=check)
            except asyncio.TimeoutError:
                return await ctx.send("Time has ran out.")
            if str(reaction.emoji) == "👎":
                return await ctx.send(f"Okay, you can try `{prefix}help` instead.")
            if str(reaction.emoji) == "👍":
                cmd = client.get_command(closest_command)
                if "args" in cmd.clean_params:
                    args = ctx.message.content.split(" ")[1:]
                    return await ctx.invoke(cmd, *args)
                elif cmd.clean_params:
                    args = int(ctx.message.content.split(" ")[1])
                    return await ctx.invoke(cmd, args)
                else:
                    return await ctx.invoke(cmd)
        else:
            return await ctx.send(
             f"The command you're trying to invoke doesn't exist.\nList of available commands - `{prefix}help`.")
    else:
        await ctx.send("Something went wrong..")
        raise error


@client.event
async def on_command(ctx):
    guild = ctx.guild
    user = ctx.author
    cmd = ctx.command
    msg = ctx.message.content
    print(f'Serwer: {guild}\nUżytkownik: {user}, {user.nick}\nKomenda: {cmd}\nWiadomość: {msg}')


@tasks.loop(hours=24)
async def called_once_a_day():
    cur.execute("UPDATE yt SET token_id = 0")
    cur.execute("UPDATE yt SET times_used = 0")
    connection.commit()


@called_once_a_day.before_loop
async def before():
    if datetime.datetime.utcnow().hour == 9:
        pass
    else:
        await asyncio.sleep(3600)
        await before()


class UtilFunctions(commands.Cog):
    @commands.command(name="help")
    async def _help(self, ctx):
        embeds = [discord.Embed(description=i, colour=bot_color_theme) for i in util.format_help_command()]
        [embed.set_footer(text=f"Page: {embeds.index(embed) + 1}/{len(embeds)}", icon_url=ctx.author.avatar_url) for embed in embeds]
        embeds[0].set_thumbnail(url=api_handler.text_thumbnail_url)
        embeds[1].set_thumbnail(url=api_handler.music_thumbnail_url)
        embeds[2].set_thumbnail(url=api_handler.utility_thumbnail_url)
        embeds[3].set_thumbnail(url=api_handler.money_thumbnail_url)
        message = await ctx.send(embed=embeds[0])

        text_cmds_instance = text_cmds.TextCmds(client, bot_color_theme)
        while not text_cmds_instance.flag:
            await text_cmds_instance.handle_pages(ctx, message, embeds)

    @commands.command(name="change_prefix")
    async def _change_prefix(self, ctx):
        global prefix
        await ctx.send(f'Current prefix is: **{prefix}**, do you want to change it? [y/n]')

        def check(msg):
            return msg.channel == ctx.channel and msg.author == ctx.author and msg.content.lower() in ['y', 'n']

        def check_2(msg):
            return msg.channel == ctx.channel and msg.author == ctx.author

        try:
            msg = await client.wait_for("message", check=check, timeout=30)
            if msg.content.lower() == "y":
                await ctx.send("Ok, so what's the new prefix?")
                prefix = await client.wait_for("message", check=check_2, timeout=30)
                prefix = prefix.content
                cur.execute(f"UPDATE guilds SET prefix = '{prefix}' WHERE guild_id = '{ctx.guild.id}'")
                connection.commit()
                await ctx.send(f"Done, new prefix is: **{prefix}**")
            else:
                await msg.add_reaction('🤔')
                await ctx.send("Alright, let me know if u change your mind.")
        except asyncio.TimeoutError:
            await ctx.send("You were too slow..")

    # @commands.command(name="change_color")
    # async def _change_color(self, ctx, *args):
    #     global bot_color_theme
    #     if (len(args)) == 3 and False not in [int(args[p]) in range(0, 256) for p in range(len(args))]:
    #         red, green, blue = int(args[0]), int(args[1]), int(args[2])
    #         bot_color_theme = discord.colour.Colour.from_rgb(red, green, blue)
    #         await ctx.send("Color has been changed!")
    #         self.reload_cogs()
    #     else:
    #         await ctx.send("You entered invalid values ._.")

    def reload_cogs(self):
        client.remove_cog("Music")
        client.remove_cog("TextCmds")
        client.add_cog(music.Music(color_theme=bot_color_theme, bot=client))
        client.add_cog(text_cmds.TextCmds(color_theme=bot_color_theme, bot=client))

    @commands.command(name="aliases")
    async def _aliases(self, ctx, *args):
        aliases = [item.aliases for item in client.commands]
        cmd_names = [item.name for item in client.commands]
        for item in aliases:
            if args[0] in item:
                return await ctx.send(f"`{args[0]}` is an alias of `{cmd_names[aliases.index(item)]}`!")
        if args[0] not in cmd_names:
            return await ctx.send(f"There is no `{args[0]}` command.")
        if client.get_command(args[0]).aliases:
            await ctx.send(f"Aliases for {args[0]}: `{', '.join(client.get_command(args[0]).aliases)}`")
        else:
            await ctx.send("There are no aliases for this command.")


client.add_cog(music.Music(client, color_theme=bot_color_theme))
client.add_cog(UtilFunctions())
client.add_cog(text_cmds.TextCmds(bot=client, color_theme=bot_color_theme))
client.add_cog(plots.Plots(bot=client, color_theme=bot_color_theme))
client.add_cog(blackjack.Blackjack(bot=client, color_theme=bot_color_theme))
client.run(discord_token)
