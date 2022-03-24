import asyncio

import discord
from discord.ext import commands

import api_handler
import ascii
import util


class TextCmds(commands.Cog):
    def __init__(self, bot, color_theme):
        self.bot = bot
        self.flag = False
        self.color_theme = color_theme
        self.current_embed = 0

    @commands.command(name="weather", aliases=["temp"])
    async def _weather(self, ctx):
        city = util.parse_city(ctx.message)
        await ctx.send(api_handler.get_weather_info(city))

    @commands.command(name="kanye_wisdom", aliases=["donda", "kanye"])
    async def _kanye_wisdom(self, ctx):
        await ctx.send(f'{api_handler.get_kanye_quote()}  {util.get_rand_emote_combo()}')

    @commands.command(name="regular_wisdom", aliases=["rw", "quote"])
    async def _regular_wisdom(self, ctx):
        await ctx.send(api_handler.get_quote())

    @commands.command(name="im_bored", aliases=["bored"])
    async def _im_bored(self, ctx):
        await ctx.send("Are you in a mood for something challenging? [y/n]")

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.lower() in ["y", "n"]

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
            if msg.content.lower() == "y":
                await msg.add_reaction('👏')
                await ctx.send(api_handler.bored_command(["education", "social", "diy", "charity", "busywork"]) + "!")

            if msg.content.lower() == "n":
                await msg.add_reaction('🥴')
                await ctx.send(api_handler.bored_command(["recreational", "music", "relaxation", "cooking"]) + "!")
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't send a reply in time.")

    @commands.command(name="nasa_pic", aliases=["nasa"])
    async def _nasa(self, ctx):
        await ctx.send("It might take a while to download.. but it's worth the wait!")

        pic_url, title, author, date = api_handler.get_nasa_pic_with_info()

        embed = discord.Embed()
        embed.title = title
        embed.colour = self.color_theme
        embed.set_image(url=pic_url)
        embed.set_footer(text=f'{author} {date}')

        await ctx.send(embed=embed)

    @commands.command(name="ascii")
    async def _ascii(self, ctx):
        embed = discord.Embed()
        embed.colour = self.color_theme
        embed.description = await ascii.get_random_ascii_art(ctx)
        await ctx.send(embed=embed)

    async def handle_pages(self, ctx, message, embeds):
        if len(embeds) < 2:
            self.flag = True
            return

        await message.add_reaction("⬅")
        await message.add_reaction("➡")

        def check(payload):
            return payload.message_id == message.id and (str(payload.emoji) == "⬅" or str(payload.emoji) == "➡") and payload.member == ctx.author
        try:
            payload = await self.bot.wait_for("raw_reaction_add", timeout=30, check=check)
        except asyncio.TimeoutError:
            self.flag = True
            await message.clear_reactions()
            return

        if str(payload.emoji) == "⬅":
            if self.current_embed - 1 != -1:
                self.current_embed -= 1
            else:
                return await message.remove_reaction(payload.emoji, ctx.author)
            await self.switch_page(ctx, message, embeds, payload)

        if str(payload.emoji) == "➡":
            if self.current_embed + 1 < len(embeds):
                self.current_embed += 1
            else:
                return await message.remove_reaction(payload.emoji, ctx.author)
            await self.switch_page(ctx, message, embeds, payload)

    async def switch_page(self, ctx, message, embeds, payload):
        await message.edit(embed=embeds[self.current_embed])
        await message.remove_reaction(payload.emoji, ctx.author)

