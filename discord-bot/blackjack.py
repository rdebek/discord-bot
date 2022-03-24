import os
from random import randint

import discord
import psycopg2
import pydealer
from discord.ext import commands

from util import check_if_has_nick, get_emoji

icon_url = 'https://static.thenounproject.com/png/1454015-200.png'
gamble_url = 'https://static.thenounproject.com/png/3407495-200.png'
emojis = ['🗯', '🧍‍♂️', '⏬', '✌']


class Blackjack(commands.Cog):
    def __init__(self, bot, color_theme):
        self.bot = bot
        self.color_theme = color_theme
        self.doube_down_flag = False
        self.connection = psycopg2.connect(os.environ['DATABASE_URL'])
        self.cur = self.connection.cursor()
        self.deck = pydealer.Deck(rebuild=True, re_shuffle=True)
        self.deck.shuffle()

    @staticmethod
    def convert_card(card):
        return f'**{card.value}** :{card.suit.lower()}:'

    @staticmethod
    def compute_card_value(card):
        if card.value not in ['King', 'Queen', 'Jack', 'Ace']:
            return int(card.value)
        elif card.value == 'Ace':
            return 11
        else:
            return 10

    @staticmethod
    def get_distance_to_21(value):
        distance = 21 - value
        if distance < 0:
            return 'bust'
        return distance

    def subtract_add_money_to_account(self, user, amount):
        self.cur.execute(f"UPDATE blackjack SET money_amount = money_amount + '{amount}' WHERE user_id = '{user}'")
        self.connection.commit()
        pass

    def check_if_user_in_db(self, user):
        self.cur.execute(f"SELECT exists (SELECT 1 FROM blackjack WHERE user_id = '{user}' LIMIT 1);")
        if not self.cur.fetchone()[0]:
            self.cur.execute(f"INSERT INTO blackjack VALUES ('{user}', 10000)")
            self.connection.commit()
            return False
        else:
            return True

    def get_cards_sum(self, cards):
        cards_values = [self.compute_card_value(card) for card in cards]
        if 11 not in cards_values:
            return [sum(cards_values)]
        elif cards_values.count(11) == 1:
            aces_replaced = [1 if card == 11 else card for card in cards_values]
            return [sum(cards_values), sum(aces_replaced)]
        else:
            both_replaced = [1 if card == 11 else card for card in cards_values]
            one_replaced = [1 if card == 11 else card for card in cards_values]
            one_replaced[one_replaced.index(1)] = 11
            return [sum(one_replaced), sum(both_replaced)]

    def format_initial_embed(self, ctx, player_cards, dealer_cards, amount):
        embed = discord.Embed(colour=self.color_theme)
        embed.set_author(icon_url=ctx.author.avatar_url, name=f"{check_if_has_nick(ctx.author)}'s blackjack game")
        player_cards_sum = "/".join(reversed([str(value) for value in self.get_cards_sum(player_cards)]))
        if '/' in player_cards_sum and int(player_cards_sum[player_cards_sum.find('/') + 1:]) > 21:
            player_cards_sum = player_cards_sum[:player_cards_sum.find('/')]
        embed.set_thumbnail(url=icon_url)
        embed.add_field(name='Stake', value=f'`${amount}`', inline=False)
        embed.add_field(name='Dealer cards', value=f'{self.convert_card(dealer_cards[0])}, :black_joker:, Sum: `{self.compute_card_value(dealer_cards[0])}`', inline=False)
        embed.add_field(name='Player cards', value=f'{", ".join([self.convert_card(player_cards[i]) for i in range(len(player_cards))])}, Sum: `{player_cards_sum}`', inline=False)
        embed.add_field(name='Options', value=':anger_right: - hit\n:man_standing: - stand\n:arrow_double_down: - double down')
        return embed

    async def stand_case(self, ctx, player_cards, dealer_cards, embed, msg, amount):
        dealer_score = max(self.get_cards_sum(dealer_cards))
        dealer_distance = self.get_distance_to_21(dealer_score)
        if dealer_distance == 'bust' and self.get_distance_to_21(min(self.get_cards_sum(dealer_cards))) != 'bust':
            dealer_score = min(self.get_cards_sum(dealer_cards))
            dealer_distance = self.get_distance_to_21(dealer_score)

        player_score = max(self.get_cards_sum(player_cards))
        player_distance = self.get_distance_to_21(player_score)
        if player_distance == 'bust' and self.get_distance_to_21(min(self.get_cards_sum(player_cards))) != 'bust':
            player_distance = self.get_distance_to_21(min(self.get_cards_sum(player_cards)))

        while dealer_score <= 16:
            dealer_cards.add(self.deck.deal(1))
            dealer_score = max(self.get_cards_sum(dealer_cards))
            dealer_distance = self.get_distance_to_21(dealer_score)
            if dealer_distance == 'bust':
                dealer_score = min(self.get_cards_sum(dealer_cards))
                dealer_distance = self.get_distance_to_21(dealer_score)

        if dealer_distance == 'bust' or dealer_distance > player_distance:
            embed.description = f'Congrats, you win `${amount}`'
            embed.colour = discord.Colour.green()
            self.subtract_add_money_to_account(ctx.author, amount)
        elif dealer_distance == player_distance:
            embed.description = f'The round ended in a draw.'
        else:
            embed.description = f'Dealer wins, you lost `${amount}`'
            embed.colour = discord.Color.red()
            self.subtract_add_money_to_account(ctx.author, -amount)

        embed.set_field_at(1, name='Dealer cards', value=f'{", ".join([self.convert_card(dealer_cards[i]) for i in range(len(dealer_cards))])}, Sum: `{dealer_score}`', inline=False)
        embed.remove_field(3)
        await msg.edit(embed=embed)
        await msg.clear_reactions()

    async def hit_case(self, ctx, player_cards, dealer_cards, embed, msg, amount):
        bust_flag = False
        player_cards.add(self.deck.deal(1))
        player_cards_sum = "/".join(reversed([str(value) for value in self.get_cards_sum(player_cards)]))
        if '/' in player_cards_sum and int(player_cards_sum[player_cards_sum.find('/') + 1:]) > 21:
            player_cards_sum = player_cards_sum[:player_cards_sum.find('/')]
        dealer_cards_sum = max(self.get_cards_sum(dealer_cards))
        embed.set_field_at(2, name='Player cards', value=f'{", ".join([self.convert_card(player_cards[i]) for i in range(len(player_cards))])}, Sum: `{player_cards_sum}`', inline=False)
        embed.set_field_at(3, name='Options', value=':anger_right: - hit\n:man_standing: - stand')
        if min(self.get_cards_sum(player_cards)) > 21:
            bust_flag = True
            embed.description = f'You **BUSTED** :x:, you lost `${amount}`'
            embed.colour = discord.Color.red()
            embed.set_field_at(1, name='Dealer cards', value=f'{", ".join([self.convert_card(dealer_cards[i]) for i in range(len(dealer_cards))])}, Sum: `{dealer_cards_sum}`', inline=False)
            self.subtract_add_money_to_account(ctx.author, -amount)
            embed.remove_field(3)
        await msg.edit(embed=embed)
        if not bust_flag:
            if self.doube_down_flag:
                return await self.stand_case(ctx, player_cards, dealer_cards, embed, msg, amount)

            await msg.clear_reactions()
            await msg.add_reaction(emojis[0])
            await msg.add_reaction(emojis[1])

            emoji = await get_emoji(ctx, msg, emojis, self.bot)
            if str(emoji) == '🗯':
                await self.hit_case(ctx, player_cards, dealer_cards, embed, msg, amount)
            if str(emoji) == '🧍‍♂️':
                await self.stand_case(ctx, player_cards, dealer_cards, embed, msg, amount)

        else:
            await msg.clear_reactions()

    def validate_stake(self, user, stake):
        self.cur.execute(f"SELECT money_amount::numeric FROM blackjack WHERE user_id = '{user}'")
        return int(self.cur.fetchone()[0]) > stake

    def blackjack_found(self, embed, player_cards, dealer_cards):
        dealer_cards_sum = max(self.get_cards_sum(dealer_cards))
        player_cards_sum = max(self.get_cards_sum(player_cards))
        embed.set_field_at(1, name='Dealer cards', value=f'{", ".join([self.convert_card(dealer_cards[i]) for i in range(len(dealer_cards))])}, Sum: `{dealer_cards_sum}`',
                           inline=False)
        embed.set_field_at(2, name='Player cards', value=f'{", ".join([self.convert_card(player_cards[i]) for i in range(len(player_cards))])}, Sum: `{player_cards_sum}`', inline=False)
        embed.remove_field(3)

    @commands.command(name='blackjack', aliases=['bj', 'black_jack'])
    async def _blackjack(self, ctx, amount: int):
        self.doube_down_flag = False
        self.check_if_user_in_db(ctx.author)
        if not self.validate_stake(ctx.author, amount):
            return await ctx.send(f'`${amount}` is too much, see `{await self.bot.get_prefix(ctx.message)}balance` for more info.')
        blackjack_flag = False
        dealer_cards, player_cards = self.deck.deal(2), self.deck.deal(2)
        embed = self.format_initial_embed(ctx, player_cards, dealer_cards, amount)
        if self.get_cards_sum(player_cards)[0] == 21 and self.get_cards_sum(dealer_cards)[0] != 21:
            blackjack_flag = True
            embed.colour = discord.Colour.green()
            embed.description = f'You have a **BLACKJACK!** :moneybag: You win 3 to 2 - `${int(amount * 3 / 2)}`'
            self.blackjack_found(embed, player_cards, dealer_cards)
            self.subtract_add_money_to_account(ctx.author, int(amount * 3/2))
        elif self.get_cards_sum(player_cards)[0] != 21 and self.get_cards_sum(dealer_cards)[0] == 21:
            blackjack_flag = True
            embed.colour = discord.Colour.red()
            embed.description = f'Dealer has a **BLACKJACK!** :x:, you lose `${amount}`'
            self.blackjack_found(embed, player_cards, dealer_cards)
            self.subtract_add_money_to_account(ctx.author, -amount)

        msg = await ctx.send(embed=embed)
        if not blackjack_flag:
            await msg.add_reaction(emojis[0])
            await msg.add_reaction(emojis[1])
            await msg.add_reaction(emojis[2])
            # if self.compute_card_value(player_cards[0]) == self.compute_card_value(player_cards[1]):
            #     embed.set_field_at(3, name='Options',
            #                        value=':anger_right: - hit\n:man_standing: - stand\n:arrow_double_down: - double down\n:v: - split')
            #     await msg.edit(embed=embed)
            #     await msg.add_reaction(emojis[3])
            emoji = await get_emoji(ctx, msg, emojis, self.bot)
            if str(emoji) == '🗯':
                await self.hit_case(ctx, player_cards, dealer_cards, embed, msg, amount)
            elif str(emoji) == '🧍‍♂️':
                await self.stand_case(ctx, player_cards, dealer_cards, embed, msg, amount)
            elif str(emoji) == '⏬':
                self.doube_down_flag = True
                amount = amount * 2
                embed.set_field_at(0, name='Stake', value=f'`${amount}`', inline=False)
                await self.hit_case(ctx, player_cards, dealer_cards, embed, msg, amount)

        else:
            await msg.clear_reactions()

    def get_balance(self, user_id):
        self.cur.execute(f"SELECT money_amount::numeric FROM blackjack WHERE user_id = '{user_id}'")
        return int(self.cur.fetchone()[0])

    @commands.command(name='balance', aliases=['money', 'cash', 'coinflip'])
    async def _balance(self, ctx):
        self.check_if_user_in_db(ctx.author)
        return await ctx.send(f'Your current balance: `${self.get_balance(ctx.author)}`')

    @commands.command(name='gamble', aliases=['bet'])
    async def _gamble(self, ctx, amount: int):
        self.check_if_user_in_db(ctx.author)
        self.validate_stake(ctx.author, amount)
        if not self.validate_stake(ctx.author, amount):
            return await ctx.send(f'`${amount}` is too much, see `{await self.bot.get_prefix(ctx.message)}balance` for more info.')
        random_number = randint(1, 10)
        if random_number in range(1, 6):
            self.subtract_add_money_to_account(ctx.author, amount)
            embed = discord.Embed(
                description=f'**WIN** :moneybag:\nCongrats, you win `${amount}`\nNew balance: `${self.get_balance(ctx.author)}`',
                colour=discord.Colour.green())
        else:
            self.subtract_add_money_to_account(ctx.author, -amount)
            embed = discord.Embed(
                description=f'**LOSE** :x:\nUnfortunately, you lose `${amount}`\nNew balance: `${self.get_balance(ctx.author)}`',
                colour=discord.Colour.red())
        embed.set_author(icon_url=ctx.author.avatar_url, name=f"{check_if_has_nick(ctx.author)}'s gambling game")
        embed.set_thumbnail(url=gamble_url)
        await ctx.send(embed=embed)

    @_gamble.error
    @_blackjack.error
    async def error(self, ctx, error):
        if isinstance(error, commands.errors.BadArgument) or isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("Please give me a whole number of dollars (like 1, 5, 25, 100, 500).")
        else:
            raise error


