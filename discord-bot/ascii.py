import random

import requests
from bs4 import BeautifulSoup

art = []
ascii_art_url = "https://www.twitchquotes.com/copypastas/ascii-art?page={}&period=alltime&sortby=popular"


def scrape_ascii_art():
    global art
    for i in range(1, 23):
        page = requests.get(ascii_art_url.format(i)).text
        bs = BeautifulSoup(page, 'lxml')
        art += bs.find_all("div", id=lambda value: value and value.startswith("clipboard_copy"))
    art = [element.text for element in art]
    return art[random.randint(0, len(art) - 1)]


async def get_random_ascii_art(ctx):
    if len(art) == 0:
        await ctx.send("It will take a while, because you're using the command for the first time. Next uses will"
                       " have immediate effect.")
        return scrape_ascii_art()
    else:
        return art[random.randint(0, len(art) - 1)]
