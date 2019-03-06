import discord
import asyncio
import youtube_dl
from discord.ext import commands
from discord.utils import find
import requests as rq



def get_prefix(bot, msg):
    """A callable Prefix for our bot. This could be edited to allow per server prefixes."""

    # Notice how you can use spaces in prefixes. Try to keep them simple though.
    prefixes = ['a']

    return commands.when_mentioned_or(*prefixes)(bot, msg)


bot = commands.Bot(command_prefix=get_prefix,description='A music bot fro discord Kurusaki')
YOUTUBE_API='YOUR YOUTUBE API'
bot.remove_command('help')

from discord import opus
OPUS_LIBS = ['libopus-0.x86.dll', 'libopus-0.x64.dll','libopus-0.dll', 'libopus.so.0', 'libopus.0.dylib']


def load_opus_lib(opus_libs=OPUS_LIBS):
    if opus.is_loaded():
        return True

    for opus_lib in opus_libs:
            try:
                opus.load_opus(opus_lib)
                return
            except OSError:
                pass

    raise RuntimeError('Could not load an opus lib. Tried %s' %(', '.join(opus_libs)))


load_opus_lib()
opts = {
    'default_search': 'auto',
    'quiet': True,
    "no_warnings":True,
    "simulate":True, #do not keep the video files
    "nooverwrites":True,
    "keepvideo":False,
    "noplaylist":True,
    "skip_download":True,
    "prefer_ffmpeg":True
}  # youtube_dl options



servers_songs = {}
player_status = {}
now_playing = {}
song_names = {}
paused = {}
rq_channel = {}


async def set_player_status():
    for i in bot.servers:
        player_status[i.id] = False
        servers_songs[i.id] = None
        paused[i.id] = False
        song_names[i.id] = []
    print(200)


async def bg():
    bot.loop.create_task(set_player_status())


@bot.event
async def on_ready():
    bot.loop.create_task(bg())
    print(bot.user.name)


@bot.event
async def on_command_error(con, error):
    pass


async def queue_songs(con, skip, clear):
    if clear == True:
        # servers_songs[con.message.server.id].stop()
        await bot.voice_client_in(con.message.server).disconnect()
        player_status[con.message.server.id] = False
        song_names[con.message.server.id].clear()

    if clear == False:
        if skip == True:
            servers_songs[con.message.server.id].pause()
            # servers_songs[con.message.server.id].stop()

        if len(song_names[con.message.server.id]) == 0:
            servers_songs[con.message.server.id] = None

        if len(song_names[con.message.server.id]) != 0:
            r = rq.Session().get('https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q={}&key={}'.format(song_names[con.message.server.id][0],YOUTUBE_API)).json()
            pack = discord.Embed(title=r['items'][0]['snippet']['title'],url="https://www.youtube.com/watch?v={}".format(r['items'][0]['id']['videoId']))
            pack.set_thumbnail(url=r['items'][0]['snippet']['thumbnails']['default']['url'])
            pack.add_field(name="Requested by:", value=con.message.author.name)
            servers_songs[con.message.server.id] = await bot.voice_client_in(con.message.server).create_ytdl_player(song_names[con.message.server.id][0], ytdl_options=opts, after=lambda: bot.loop.create_task(after_song(con, False, False)))
            servers_songs[con.message.server.id].start()
            if servers_songs[con.message.server.id].duration != 0.0:
                pack.add_field(name='Length', value=servers_songs[con.message.server.id].duration, inline=True)
            if servers_songs[con.message.server.id].duration == 0.0:
                pack.add_field(name='Length', value='Live!',inline=True)
            await bot.delete_message(now_playing[con.message.server.id])
            msg = await bot.send_message(con.message.channel, embed=pack)
            now_playing[con.message.server.id] = msg

            if len(song_names[con.message.server.id]) >= 1:
                song_names[con.message.server.id].pop(0)

        if len(song_names[con.message.server.id]) == 0 and servers_songs[con.message.server.id] == None:
            player_status[con.message.server.id] = False


async def after_song(con, skip, clear):
    bot.loop.create_task(queue_songs(con, skip, clear))

@bot.command(pass_context=True)
async def play(con, *, url):
    """PLAY THE GIVEN SONG AND QUEUE IT IF THERE IS CURRENTLY SONG PLAYING"""
    if con.message.channel.is_private == True:
        await bot.send_message(con.message.channel, "**You must be in a `server text channel` to use this command**")

    if con.message.channel.is_private == False:  # command is used in a server
        rq_channel[con.message.server.id] = con.message.channel.id
        if bot.is_voice_connected(con.message.server) == False:
            await bot.join_voice_channel(con.message.author.voice.voice_channel)

        if bot.is_voice_connected(con.message.server) == True:
            if player_status[con.message.server.id] == True:
                song_names[con.message.server.id].append(url)
                r = rq.Session().get('https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q={}&key={}'.format(url,YOUTUBE_API)).json()
                await bot.send_message(con.message.channel, "**Song `{}` Queued**".format(r['items'][0]['snippet']['title']))

            if player_status[con.message.server.id] == False:
                player_status[con.message.server.id] = True
                song_names[con.message.server.id].append(url)
                song = await bot.voice_client_in(con.message.server).create_ytdl_player(song_names[con.message.server.id][0], ytdl_options=opts, after=lambda: bot.loop.create_task(after_song(con, False, False)))
                servers_songs[con.message.server.id] = song
                servers_songs[con.message.server.id].start()
                r = rq.Session().get('https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q={}&key={}'.format(url,YOUTUBE_API)).json()
                pack = discord.Embed(title=r['items'][0]['snippet']['title'],url="https://www.youtube.com/watch?v={}".format(r['items'][0]['id']['videoId']))
                pack.set_thumbnail(
                    url=r['items'][0]['snippet']['thumbnails']['default']['url'])
                pack.add_field(name="Requested by:",value=con.message.author.name)
                if servers_songs[con.message.server.id].duration != 0.0:
                    pack.add_field(name='Length',value=servers_songs[con.message.server.id].duration,inline=True)
                if servers_songs[con.message.server.id].duration == 0.0:
                    pack.add_field(name='Length',value='Live!',inline=True)
                msg = await bot.send_message(con.message.channel, embed=pack)
                now_playing[con.message.server.id] = msg
                song_names[con.message.server.id].pop(0)


@bot.command(pass_context=True)
async def skip(con):
    if con.message.channel.is_private == True:
        await bot.send_message(con.message.channel, "**You must be in a `server text channel` to use this command**")

    # COMMAND NOT IN DM
    if con.message.channel.is_private == False:
        if servers_songs[con.message.server.id] == None or len(song_names[con.message.server.id]) == 0 or player_status[con.message.server.id] == False:
            await bot.send_message(con.message.channel, "**No songs in queue to skip**")
        if servers_songs[con.message.server.id] != None:
            bot.loop.create_task(queue_songs(con, True, False))


@bot.command(pass_context=True)
async def join(con, *, channel=None):
    """JOIN A VOICE CHANNEL THAT THE USR IS IN OR MOVE TO A VOICE CHANNEL IF THE BOT IS ALREADY IN A VOICE CHANNEL"""

    # COMMAND IS IN DM
    if con.message.channel.is_private == True:
        await bot.send_message(con.message.channel, "**You must be in a `server text channel` to use this command**")

    # COMMAND NOT IN DM
    if con.message.channel.is_private == False:
        voice_status = bot.is_voice_connected(con.message.server)

        voice = find(lambda m: m.name == channel, con.message.server.channels)

        if voice_status == False and channel == None:  # VOICE NOT CONNECTED
            if con.message.author.voice_channel == None:
                await bot.send_message(con.message.channel, "**You must be in a voice channel or give a voice channel name to join**")
            if con.message.author.voice_channel != None:
                await bot.join_voice_channel(con.message.author.voice.voice_channel)

        if voice_status == False and channel != None:  # PICKING A VOICE CHANNEL
            await bot.join_voice_channel(voice)

        if voice_status == True:  # VOICE ALREADY CONNECTED
            if voice == None:
                await bot.send_message(con.message.channel, "**Bot is already connected to a voice channel**")

            if voice != None:
                if voice.type == discord.ChannelType.voice:
                    await bot.voice_client_in(con.message.server).move_to(voice)


@bot.command(pass_context=True)
async def leave(con):
    """LEAVE THE VOICE CHANNEL AND STOP ALL SONGS AND CLEAR QUEUE"""
    # COMMAND USED IN DM
    if con.message.channel.is_private == True:
        await bot.send_message(con.message.channel, "**You must be in a `server text channel` to use this command**")

    # COMMAND NOT IN DM
    if con.message.channel.is_private == False:

        # IF VOICE IS NOT CONNECTED
        if bot.is_voice_connected(con.message.server) == False:
            await bot.send_message(con.message.channel, "**Bot is not connected to a voice channel**")

        # VOICE ALREADY CONNECTED
        if bot.is_voice_connected(con.message.server) == True:
            bot.loop.create_task(queue_songs(con, False, True))


@bot.command(pass_context=True)
async def pause(con):
    # COMMAND IS IN DM
    if con.message.channel.is_private == True:
        await bot.send_message(con.message.channel, "**You must be in a `server text channel` to use this command**")

    # COMMAND NOT IN DM
    if con.message.channel.is_private == False:
        if servers_songs[con.message.server.id] != None:
            if paused[con.message.server.id] == True:
                await bot.send_message(con.message.channel, "**Audio already paused**")
            if paused[con.message.server.id] == False:
                servers_songs[con.message.server.id].pause()
                paused[con.message.server.id] = True


@bot.command(pass_context=True)
async def resume(con):
    # COMMAND IS IN DM
    if con.message.channel.is_private == True:
        await bot.send_message(con.message.channel, "**You must be in a `server voice channel` to use this command**")

    # COMMAND NOT IN DM
    if con.message.channel.is_private == False:
        if servers_songs[con.message.server.id] != None:
            if paused[con.message.server.id] == False:
                await bot.send_message(con.message.channel, "**Audio already playing**")
            if paused[con.message.server.id] == True:
                servers_songs[con.message.server.id].resume()
                paused[con.message.server.id] = False


@bot.command(pass_context=True)
async def volume(con, vol: float):
    if player_status[con.message.server.id] == False:
        await bot.send_message(con.message.channel, "No Audio playing at the moment")
    if player_status[con.message.server.id] == True:
        servers_songs[con.message.server.id].volume = vol


bot.run('bot token')
