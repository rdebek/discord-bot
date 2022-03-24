import json
import os
import random

import psycopg2
import requests
from lyricsgenius import Genius

import util

discord_token = os.environ['DISCORD_TOKEN']
# discord_token = os.environ['DISCORD_TEST_TOKEN']
weather_token = os.environ['WEATHER_TOKEN']
nasa_token = os.environ['NASA_TOKEN']
youtube_token = os.environ['YOUTUBE_TOKEN_0']
genius = Genius(os.environ['GENIUS_TOKEN'])

kanye_api_url = "https://api.kanye.rest/"
youtube_api_url = "https://youtube.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q={}&key={}" \
                  "&type=video&relevanceLanguage=PL"
weather_api_url = "https://api.openweathermap.org/data/2.5/weather?q={0}&appid={1}&units=metric&lang"
zenquote_api_url = "https://zenquotes.io/api/random"
bored_api_url = "https://www.boredapi.com/api/activity?type={}"
nasa_api_url = "https://api.nasa.gov/planetary/apod?api_key={}&count=1"

music_thumbnail_url = "https://cdn.icon-icons.com/icons2/2098/PNG/512/music_icon_128798.png"
text_thumbnail_url = "https://icons-for-free.com/iconfiles/png/512/chat+comment+communication+message+talk+text+icon-1320166550137140710.png"
utility_thumbnail_url = "https://static.thenounproject.com/png/2035509-200.png"
money_thumbnail_url = "https://static.thenounproject.com/png/997725-200.png"

counter = 0
connection = psycopg2.connect(os.environ['DATABASE_URL'])
cur = connection.cursor()


def get_quote():
    response = requests.get(zenquote_api_url)
    json_data = json.loads(response.text)
    quote = json_data[0]['q'] + ' - ' + json_data[0]['a']
    return quote


def get_kanye_quote():
    response = requests.get(kanye_api_url)
    json_data = json.loads(response.text)
    quote = json_data['quote']
    return quote


def get_nasa_pic_with_info():
    response = requests.get(nasa_api_url.format(nasa_token))
    json_data = json.loads(response.text)
    if 'hdurl' in json_data[0]:
        pic_url = json_data[0]['hdurl']
    else:
        pic_url = json_data[0]['url']
    title = json_data[0]['title']
    if 'copyright' in json_data[0]:
        author = f"Author: {json_data[0]['copyright']}, "
    else:
        author = ""
    date = json_data[0]['date']
    date = date[-2:] + date[4:-2] + date[0:4]
    return pic_url, title, author, date


def get_weather_info(city):
    response = requests.get(weather_api_url.format(city, weather_token))
    if response.status_code == 200:
        json_data = json.loads(response.text)
        temperature = round(json_data['main']['temp'])
        time_shift = json_data['timezone']
        emoji = util.get_weather_emoji(json_data['weather'][0]['main'], time_shift)
        return f"It's currently {str(temperature)}°C in {city.title()}. {emoji}"
    else:
        return "That doesn't seem to be a valid city name :[."


def bored_command(activity_types):
    response = requests.get(bored_api_url.format(activity_types[random.randint(0, len(activity_types) - 1)]))
    json_data = json.loads(response.text)
    return json_data['activity']


async def get_yt_url_from_search(search, message=None, playlist_length=0):
    global counter
    global youtube_token
    cur.execute("SELECT * FROM yt")
    token_number, times_used = cur.fetchone()
    youtube_token = os.environ[f"YOUTUBE_TOKEN_{token_number}"]

    if times_used == 100:
        token_number += 1
        youtube_token = os.environ[f"YOUTUBE_TOKEN_{token_number}"]
        times_used = 0

    times_used += 1
    counter += 1
    cur.execute(f"UPDATE yt SET token_id = {token_number}")
    cur.execute(f"UPDATE yt SET times_used = {times_used}")
    connection.commit()
    if message and counter <= playlist_length:
        await message.edit(content=f"Preparing the playlist, loaded: `{counter}` songs.")
    p = requests.get(youtube_api_url.format(search, youtube_token))
    json_data = json.loads(p.text)
    return "https://www.youtube.com/watch?v=" + json_data['items'][0]['id']['videoId']


def clear_counter():
    global counter
    counter = 0


def get_song_lyrics(song):
    if "(Official" in song:
        song = song[:song.index("(Official")]
    if "(prod" in song:
        song = song[:song.index("(prod")]
    songs = genius.search_songs(song)
    url = songs['hits'][0]['result']['url']
    song_lyrics = genius.lyrics(song_url=url)
    if "EmbedShare" in song_lyrics:
        song_lyrics = song_lyrics[:song_lyrics.index("EmbedShare")]
    return song_lyrics

