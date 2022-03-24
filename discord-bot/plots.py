import datetime

import discord
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from discord.ext import commands
from fuzzywuzzy import process
from matplotlib.patches import Polygon
from pycoingecko import CoinGeckoAPI

from util import check_if_has_nick, get_emoji

api = CoinGeckoAPI()
number_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣']

FONT = {'family': 'serif',
        'weight': 'bold',
        'size': 13,
        }
top_crypto = ['usd-coin', 'dogecoin', 'tether', 'litecoin', 'bitcoin', 'ethereum']
example_durations = ['1', '7', '14', '31', '182', '365', 'max', 'other']


class Plots(commands.Cog):
    def __init__(self, bot, color_theme):
        self.bot = bot
        self.coins_list = []
        self.color_theme = color_theme

    @staticmethod
    def convert_date_to_eu_format(date):
        return date.strftime('%d.%m.%y')

    @staticmethod
    def convert_timestamp(timestamp):
        return timestamp/1000

    @staticmethod
    def get_percentage(start, end):
        percentage = ((end - start) * 100)/start
        return "%.2f" % percentage

    @staticmethod
    def plot_duration_embed():
        embed = discord.Embed(title='Choose the duration', description='')
        for duration in example_durations:
            ordering_number = example_durations.index(duration) + 1
            if duration == 'other':
                embed.description += f'{ordering_number}. `{duration}`\n'
            elif duration == '1':
                embed.description += f'{ordering_number}. `{duration}` day\n'
            else:
                embed.description += f'{ordering_number}. `{duration}` days\n'
        return embed

    def form_date_string(self, timestamp):
        return datetime.datetime.fromtimestamp(self.convert_timestamp(timestamp)).strftime("%d %b '%y")

    def set_x_locator_and_formatter(self, x, ax, bins):
        bins -= 1
        points_locations = [x[0]]

        for i in range(1, bins):
            points_locations.append(x[int(len(x) * i / bins)])

        points_locations.append(x[int(len(x) - 1)])

        ax.xaxis.set_major_locator(plt.FixedLocator(points_locations))
        ax.xaxis.set_major_formatter(plt.FixedFormatter([self.form_date_string(point) for point in points_locations]))

    # TODO: function below (gather user input, ensure that the right crypto is found, unless there is only 1 found)
    def plot_user_duration(self, crypto_id: str):
        if not self.coins_list:
            self.coins_list = api.get_coins_list()

        temp = [[x['id'], x['symbol'], x['name']] for x in self.coins_list]
        k = [p for i in temp for p in i]
        closest, probablity = process.extractOne("Monero", k)
        for item in temp:
            if closest in item:
                print(item[0], probablity)

        prices = api.get_coin_market_chart_range_by_id(id=crypto_id, vs_currency='pln', from_timestamp=1592577232,
                                                       to_timestamp=1630966128)['prices']
        x, y = zip(*[price for price in prices])
        return x, y

    def plot_preset_duration(self, crypto_id: str, duration: str):

        prices = api.get_coin_market_chart_by_id(id=crypto_id, vs_currency='usd', days=duration)['prices']

        x, y = zip(*[price for price in prices])

        rise_percentage = self.get_percentage(y[0], y[-1])

        self.create_plot(x, y, 'usd', crypto_id, self.format_duration_string(duration), rise_percentage)

        return x, y

    def format_duration_string(self, duration):
        if duration == 'max':
            return "all time"
        duration = int(duration)
        from_date = datetime.date.today() - datetime.timedelta(days=duration)
        return f'{self.convert_date_to_eu_format(from_date)} - {self.convert_date_to_eu_format(datetime.date.today())}'

    def create_plot(self, x, y, currency, crypto_id, duration_string, rise_percentage):
        plt.clf()
        with plt.style.context('dark_background'):
            if float(rise_percentage) > 0:
                fill_color, color = 'seagreen', 'lime'
            else:
                fill_color, color = 'lightcoral', 'red'

            ax = plt.axes()
            self.set_x_locator_and_formatter(x, ax, 4)
            plt.grid(linestyle=':')

            ax.set_ylabel(f"{currency.upper()}($)", rotation=0, labelpad=30, weight='bold')
            ax.yaxis.set_label_coords(-0.05, 1.02)
            plt.title(f"{crypto_id}\n{duration_string}".capitalize(), fontdict=FONT)
            self.gradient_fill(x, y, fill_color=fill_color, color=color)

            plt.plot([x[0], x[-1]], [y[0], y[-1]], 'wo--', zorder=25)
            plt.plot([x[0], x[y.index(max(y))]], [y[0], y[y.index(max(y))]], 'o--', zorder=26, color='royalblue')
            plt.plot([x[0], x[y.index(min(y))]], [y[0], y[y.index(min(y))]], 'yo--', zorder=27)
            plt.savefig('foo.png', bbox_inches='tight')

    @commands.command(name="crypto")
    async def _crypto(self, ctx):

        embed = discord.Embed(title='Choose the cryptocurrency', description='')
        embed.set_author(icon_url=ctx.author.avatar_url, name=check_if_has_nick(ctx.author))
        for crypto in top_crypto:
            embed.description += f'{top_crypto.index(crypto) + 1}. {crypto}\n'

        msg = await ctx.send(embed=embed)
        for i in range(len(top_crypto)):
            await msg.add_reaction(number_emojis[i])

        emoji = await get_emoji(ctx, msg, number_emojis, self.bot)
        if not emoji:
            return
        crypto_id = top_crypto[number_emojis.index(str(emoji))]

        await msg.edit(embed=self.plot_duration_embed())
        await msg.add_reaction(number_emojis[6])
        await msg.add_reaction(number_emojis[7])

        second_emoji = await get_emoji(ctx, msg, number_emojis, self.bot)
        if not second_emoji:
            return
        duration = example_durations[number_emojis.index(str(second_emoji))]

        if str(second_emoji) == '8️⃣':
            await msg.delete()
            return await ctx.send("This is not implemented yet.")

        else:
            x, y = self.plot_preset_duration(crypto_id, duration)

        await msg.delete()
        embed, file = self.format_final_embed(crypto_id, duration, x, y)
        return await ctx.send(embed=embed, file=file)

    def gradient_fill(self, x, y, fill_color=None, ax=None, **kwargs):
        if ax is None:
            ax = plt.gca()

        line, = ax.plot(x, y, **kwargs)
        if fill_color is None:
            fill_color = line.get_color()

        zorder = line.get_zorder()
        alpha = line.get_alpha()
        alpha = 1.0 if alpha is None else alpha

        z = np.empty((100, 1, 4), dtype=float)
        rgb = mcolors.colorConverter.to_rgb(fill_color)
        z[:, :, :3] = rgb
        z[:, :, -1] = np.linspace(0, alpha, 100)[:, None]

        xmin, xmax, ymin, ymax = min(x), max(x), min(y), max(y)
        im = ax.imshow(z, aspect='auto', extent=[xmin, xmax, ymin, ymax],
                       origin='lower', zorder=zorder)

        xy = np.column_stack([x, y])
        xy = np.vstack([[xmin, ymin], xy, [xmax, ymin], [xmin, ymin]])
        clip_path = Polygon(xy, facecolor='none', edgecolor='none', closed=True)
        ax.add_patch(clip_path)
        im.set_clip_path(clip_path)
        ax.autoscale(True)
        return line, im

    def format_final_embed(self, crypto_id, duration, x, y):

        percentage = self.get_percentage(y[0], y[-1])
        open, close = self.floats_comparing(y[0], y[-1])
        change = 'increased' if float(percentage) > 0 else 'decreased'
        file = discord.File("foo.png")
        embed = discord.Embed(color=self.color_theme)
        embed.title = f"{crypto_id} ({self.format_duration_string(duration)})".capitalize()
        embed.set_image(url="attachment://foo.png")
        embed.add_field(name=":white_circle: Open-Close values in the chosen time span.", value=f"{crypto_id.capitalize()} "
        f"has {change} in value by `{percentage}%`\nPrice change: **{open}$** :arrow_right: **{close}$**", inline=False)
        embed.add_field(name=":blue_circle: Open-High values in the chosen time span.", value=f"Highest price for {crypto_id.capitalize()} - "
        f"**{self.format_single_float(max(y))}$**\nAchieved on `{self.form_date_string(x[y.index(max(y))])}` ",
                        inline=False)
        embed.add_field(name=":yellow_circle: Open-Low values in the chosen time span.", value=f"Lowest price for {crypto_id.capitalize()} - "
        f"**{self.format_single_float(min(y))}$**\nAchieved on `{self.form_date_string(x[y.index(min(y))])}` ", inline=False)

        return embed, file

    def floats_comparing(self, float1, float2):
        float1_arr = []
        float2_arr = []
        [float1_arr.append(digit) for digit in str(float1)]
        [float2_arr.append(digit) for digit in str(float2)]
        i = 0
        while float1_arr[i] == float2_arr[i]:
            i += 1
        if i < float1_arr.index('.') or i < float2_arr.index('.'):
            i = max(float1_arr.index('.'), float2_arr.index('.')) - 1
        return "".join(float1_arr[:i+3]), "".join(float2_arr[:i+3])

    def format_single_float(self, float_value):
        float_arr = []
        [float_arr.append(digit) for digit in str(float_value)]
        if 'e' in float_arr:
            amount_of_zeros = int(float_arr[-1]) - 1
            float_arr.remove('.')
            float_arr.insert(0, '0')
            float_arr.insert(1, '.')
            float_arr = float_arr[:-4]
            for i in range(amount_of_zeros):
                float_arr.insert(2, '0')
        j = float_arr.index('.') + 1
        while float_arr[j] == '0':
            j += 1
        return "".join(float_arr[:j+2])
