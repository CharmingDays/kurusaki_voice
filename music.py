import discord
import asyncio
import youtube_dl
from discord.ext import commands
import requests as rq
from discord import opus


bot = commands.Bot(command_prefix='.')
YOUTUBE_API = 'YOUR YOUTUBE API TOKEN HERE'


bot.remove_command('help')
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
    "no_warnings": True,
    "simulate": True,  # do not keep the video files
    "nooverwrites": True,
    "keepvideo": False,
    "noplaylist": True,
    "skip_download": False,
    "prefer_ffmpeg": True
}  # youtube_dl options
beforeOps = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
players={}


async def background_player(msg,song):
    voice_client = bot.voice_client_in(msg.message.server)
    song_pack = rq.get(
        "https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q={}&key={}".format(song, YOUTUBE_API)).json()
    song = "https://www.youtube.com/watch?v={}".format(
        song_pack['items'][0]['id']['videoId'])

    if msg.message.server.id in players:
        data = {
            "song": song,
            "title": song_pack['items'][0]['snippet']['title'],
            "url": "https://www.youtube.com/watch?v={}".format(song_pack['items'][0]['id']['videoId']),
            "thumbnail": song_pack['items'][0]['snippet']['thumbnails']['high']['url'],
            "author": msg.message.author,
            "publish": song_pack['items'][0]['snippet']['publishedAt'],
            "channel": msg.message.channel
        }
        if players[msg.message.server.id]['stream'] != None:
            players[msg.message.server.id]['songs'].append(data)
            await bot.send_message(msg.message.channel,"Song **{}** queued".format(data['title']))

        if not players[msg.message.server.id]['songs'] and players[msg.message.server.id]['stream'] == None:
            players[msg.message.server.id]['stream'] = await voice_client.create_ytdl_player(url=song, ytdl_options=opts, before_options=beforeOps, after=lambda: bot.loop.create_task(player_control(msg.message.server)))
            emb = discord.Embed(title=data['title'], url=data['url'])
            emb.set_thumbnail(url=data['thumbnail'])
            emb.add_field(name='Published At', value=data['publish'])
            emb.set_footer(icon_url=msg.message.author.avatar_url,text='Requested by {}'.format(msg.message.author.display_name))
            await bot.send_message(msg.message.channel,embed=emb)
            players[msg.message.server.id]['stream'].volume = players[msg.message.server.id]['volume']
            players[msg.message.server.id]['stream'].start()

    if msg.message.server.id not in players:
        players[msg.message.server.id] = {
            "stream": await voice_client.create_ytdl_player(url=song, ytdl_options=opts, before_options=beforeOps, after=lambda: bot.loop.create_task(player_control(msg.message.server))),
            "songs": [],
            "status": False,
            "message": None,
            "volume":1
        }
        emb = discord.Embed(title=song_pack['items'][0]['snippet']['title'],
                            url="https://www.youtube.com/watch?v={}".format(song_pack['items'][0]['id']['videoId']))
        emb.set_thumbnail(
            url=song_pack['items'][0]['snippet']['thumbnails']['high']['url'])
        emb.add_field(name='Published at',value=song_pack['items'][0]['snippet']['publishedAt'])
        emb.set_footer(icon_url=msg.message.author.avatar_url,text=f'Requested by: {msg.message.author.display_name}')
        players[msg.message.server.id]['message'] = await bot.send_message(msg.message.channel, embed=emb)
        players[msg.message.server.id]['stream'].volume =players[msg.message.server.id]['volume']
        players[msg.message.server.id]['stream'].start()








@bot.event
async def on_command_error(error,msg):
    if isinstance(error,commands.errors.CommandInvokeError):
        if error.args[0] == 'Command raised an exception: ClientException: Already connected to a voice channel in this server':
            await bot.send_message(msg.message.channel,"**Bot already in a voice channel**")
        if error.args[0].startswith('Command raised an exception: TimeoutError:'):
            pass

        if error.args[0] == "Command raised an exception: AttributeError: 'NoneType' object has no attribute 'disconnect'":
            await bot.send_message(msg.message.channel,'**Bot already left the voice channel**')

        if error.args[0] == "Command raised an exception: AttributeError: 'NoneType' object has no attribute 'create_ytdl_player'":
            if msg.message.author.voice_channel != None:
                await bot.join_voice_channel(msg.message.author.voice_channel)
                await background_player(msg,msg.message.content[6:])
            
            if msg.message.author.voice_channel == None:
                await bot.send_message(msg.message.channel,"**You are must be in a voice channel to use this command**")


@bot.event
async def on_ready():
    print(bot.user.name)



async def player_control(server):
    if players[server.id]['songs']:
        await bot.delete_message(players[server.id]['message'])
        voice_client = bot.voice_client_in(server)
        players[server.id]['stream']=await voice_client.create_ytdl_player(url=players[server.id]['songs'][0]['song'],ytdl_options=opts,before_options=beforeOps,after=lambda: bot.loop.create_task(player_control(server)))
        emb = discord.Embed(title=players[server.id]['songs'][0]['title'],url=players[server.id]['songs'][0]['url'])
        emb.set_thumbnail(url=players[server.id]['songs'][0]['thumbnail'])
        emb.add_field(name='Published At',value=players[server.id]['songs'][0]['publish'])
        emb.set_footer(icon_url=players[server.id]['songs'][0]['author'].avatar_url,text='Requested by {}'.format(players[server.id]['songs'][0]['author'].display_name))
        players[server.id]['message'] = await bot.send_message(players[server.id]['songs'][0]['channel'], embed=emb)
        players[server.id]['stream'].volume = players[server.id]['volume']
        players[server.id]['stream'].start()
        players[server.id]['songs'].pop(0)

    else:
        players[server.id]['stream']=None


@bot.command(pass_context=True)
async def play(msg,*,song):
    """
    Play an audio of the link or name of song you provide
    Command: s.play <Song name or url>
    Example: s.play I'm nothing but a 2D girl
    """
    await background_player(msg,song)




@bot.command(pass_context=True)
async def leave(msg):
    """
    Leave the voice channel, clear the songs list and stop the audio
    Command: s.leave
    Example: s.leave
    """
    if msg.message.server.id in players:
        await bot.voice_client_in(msg.message.server).disconnect()
        players[msg.message.server.id]['stream']=None
        players[msg.message.server.id]['songs'].clear()
        players[msg.message.server.id]['status']=False
        players[msg.message.server.id]['message'] = None

    if msg.message.author.voice_channel == bot.user.voice_channel:
        await bot.voice_client_in(msg.message.server).disconnect()


@bot.command(pass_context=True)
async def join(msg):
    """
    Join a voice channel that you are currently in
    Command: s.join
    Example: s.join
    """
    if msg.message.author.voice_channel != None:
        await bot.join_voice_channel(msg.message.author.voice_channel)
    else:
        await bot.say("You must be in a voice channel to use this command")

@bot.command(pass_context=True)
async def pause(msg):
    """
    Pause the current audio streamer
    Command: s.pause
    Example: s.pause
    """
    if msg.message.server.id in players:
        if players[msg.message.server.id]['stream'] != None:
            if players[msg.message.server.id]['status'] == True:
                await bot.say("Audio already paused")
            
            if players[msg.message.server.id]['status'] == False:
                players[msg.message.server.id]['stream'].pause()
                players[msg.message.server.id]['status']=True
            

        else:
            await bot.say("No audio playing in voice channel")
    else:
        await bot.say("No audio in voice channel")
    

@bot.command(pass_context=True)
async def resume(msg):
    """
    Resume the current audio streamer
    Command: s.resume
    Example: s.resume
    """
    if msg.message.server.id in players:
        if players[msg.message.server.id]['stream'] !=None:
            if players[msg.message.server.id]['status'] == False:
                await bot.say("Audio already playing")
            
            if players[msg.message.server.id]['status'] == True:
                players[msg.message.server.id]['stream'].resume()
            
        else:
            await bot.say("No audio playing in voice channel")
    else:
        await bot.say("No audio playing in voice channel")


@bot.command(pass_context=True)
async def volume(msg,vol:float):
    """
    Change the volume of the current audio streamer (1.0 == 100% and 2.0 == 200%)
    Command: s.volume <volume_amount>
    Example: s.volume 1.5
    """
    if msg.message.server.id in players:
        if players[msg.message.server.id]['stream'] !=None:
            players[msg.message.server.id]['stream'].volume=vol
            players[msg.message.server.id]['volume']=vol

#TODL: complete this volume options and make it better if possible

@bot.command(pass_context=True)
async def skip(msg):
    """
    Skip the current song that's playing
    Command: s.skip
    Example: s.skip
    """
    if msg.message.server.id in players:
        if players[msg.message.server.id]['stream'] !=None:
            if not players[msg.message.server.id]['songs']:
                players[msg.message.server.id]['stream'].stop()
                await player_control(msg.message.server)
                reply=await bot.say("Skipped song\nNo songs in queue to play next")
                await asyncio.sleep(10)
                await bot.delete_message(reply)
            
            if players[msg.message.server.id]['songs']:
                players[msg.message.server.id]['stream'].stop()
                reply=await bot.say("Song Skipped")
                await asyncio.sleep(10)
                await bot.delete_message(reply)

        if players[msg.message.server.id]['stream']== None:
            await bot.say("No audio currently playing")


@bot.command(pass_context=True)
async def clear_songs(msg):
    """
    Clear the songs and also stop the current audio playing
    Command: s.clear
    Example: s.clear
    """
    if msg.message.server.id in players:
        if players[msg.message.server.id]['stream'] != None:
            players[msg.message.server.id]['stream'].stop()
            players[msg.message.server.id]['stream'] = None
            players[msg.message.server.id]['songs'].clear()
            await bot.say("All songs cleared")
        else:
            await bot.say("No songs playing or in queue")

    else:
        await bot.say("No songs playing or in queue")


@bot.command(pass_context=True)
async def songs(msg):
    """
    Check the current lists of songs that are in queue
    Command: s.songs
    Example: s.songs
    """
    if msg.message.server.id in players:
        if players[msg.message.server.id]['songs']:
            song_order=discord.Embed(title='Songs',description='Current songs in queue')
            for i in players[msg.message.server.id]['songs']:
                song_order.add_field(name=i['author'].display_name,value=i['title'],inline=False)
            await bot.say(embed=song_order)
        else:
            await bot.say("Currently no songs in queue")


bot.run('YUR BOT TOKEN HERE')
