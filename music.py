import discord
import asyncio
import youtube_dl
from discord.ext import commands
import requests as rq
from discord import opus


def get_prefix(bot, msg):
    """A callable Prefix for our bot. This could be edited to allow per server prefixes."""

    # Notice how you can use spaces in prefixes. Try to keep them simple though.
    prefixes = ['.']

    return commands.when_mentioned_or(*prefixes)(bot, msg)

bot = commands.Bot(command_prefix=get_prefix)
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


# @bot.event
# async def on_command_error(error,msg):
#     if isinstance(error,commands.errors.CommandInvokeError):
#         if error.args[0] == 'Command raised an exception: ClientException: Already connected to a voice channel in this server':
#             await bot.send_message(msg.message.channel,"**Bot already in a voice channel**")
#         if error.args[0].startswith('Command raised an exception: TimeoutError:'):
#             pass

#         if error.args[0] == "Command raised an exception: AttributeError: 'NoneType' object has no attribute 'disconnect'":
#             await bot.send_message(msg.message.channel,'**Bot already left the voice channel**')


@bot.event
async def on_ready():
    print(bot.user.name)


@bot.command(pass_context=True)
async def leave(msg):
    await bot.voice_client_in(msg.message.server).disconnect()

@bot.command(pass_context=True)
async def join(msg):
    await bot.join_voice_channel(msg.message.author.voice_channel)




async def player_control(server):
    if players[server.id]['songs']:
        voice_client = bot.voice_client_in(server)
        players[server.id]['stream']=await voice_client.create_ytdl_player(url=players[server.id]['songs'][0]['song'],ytdl_options=opts,before_options=beforeOps,after=lambda: bot.loop.create_task(player_control(server)))
        emb = discord.Embed(title=players[server.id]['songs'][0]['title'],url=players[server.id]['songs'][0]['url'])
        emb.set_thumbnail(url=players[server.id]['songs'][0]['thumbnail'])
        emb.add_field(name='Published At',value=players[server.id]['songs'][0]['publish'])
        emb.set_footer(icon_url=players[server.id]['songs'][0]['author'].avatar_url,text='Requested by {}'.format(players[server.id]['songs'][0]['author'].display_name))
        await bot.send_message(players[server.id]['songs'][0]['channel'], embed=emb)
        players[server.id]['stream'].start()
        players[server.id]['songs'].pop(0)

    else:
        players[server.id]['stream']=None


@bot.command(pass_context=True)
async def play(msg,*,song):

    voice_client=bot.voice_client_in(msg.message.server)
    song_pack=rq.get("https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q={}&key={}".format(song,YOUTUBE_API)).json()
    song = "https://www.youtube.com/watch?v={}".format(song_pack['items'][0]['id']['videoId'])
    
    if msg.message.server.id in players:
        data = {
            "song": song,
            "title": song_pack['items'][0]['snippet']['title'],
            "url": "https://www.youtube.com/watch?v={}".format(song_pack['items'][0]['id']['videoId']),
            "thumbnail": song_pack['items'][0]['snippet']['thumbnails']['high']['url'],
            "author":msg.message.author,
            "publish":song_pack['items'][0]['snippet']['publishedAt'],
            "channel":msg.message.channel
            }
        if players[msg.message.server.id]['stream'] != None:
            players[msg.message.server.id]['songs'].append(data)
            await bot.say("Song **{}** queued".format(data['title']))

        if not players[msg.message.server.id]['songs'] and players[msg.message.server.id]['stream'] ==None:
            players[msg.message.server.id]['stream'] =await voice_client.create_ytdl_player(url=song, ytdl_options=opts, before_options=beforeOps, after=lambda: bot.loop.create_task(player_control(msg.message.server)))
            emb = discord.Embed(title=data['title'],url=data['url'])
            emb.set_thumbnail(url=data['thumbnail'])
            emb.add_field(name='Published At',value=data['publish'])
            emb.set_footer(icon_url=msg.message.author.avatar_url,text='Requested by {}'.format(msg.message.author.display_name))
            await bot.say(embed=emb)
            players[msg.message.server.id]['stream'].start()

    if msg.message.server.id not in players:
        players[msg.message.server.id]={
            "stream":await voice_client.create_ytdl_player(url=song,ytdl_options=opts,before_options=beforeOps,after= lambda: bot.loop.create_task(player_control(msg.message.server))),
            "songs":[],
            "status":False
            }
        emb = discord.Embed(title=song_pack['items'][0]['snippet']['title'], url="https://www.youtube.com/watch?v={}".format(song_pack['items'][0]['id']['videoId']))
        emb.set_thumbnail(url=song_pack['items'][0]['snippet']['thumbnails']['high']['url'])
        emb.add_field(name='Published at',value=song_pack['items'][0]['snippet']['publishedAt'])
        emb.set_footer(icon_url=msg.message.author.avatar_url,text=f'Requested by: {msg.message.author.display_name}')
        await bot.say(embed=emb)
        players[msg.message.server.id]['stream'].start()





@bot.command(pass_context=True)
async def pause(msg):
    if msg.message.server.id in players:
        if players[msg.message.server.id]['stream'] != None:
            if players[msg.message.server.id]['status'] == False:
                players[msg.message.server.id]['stream'].pause()
                players[msg.message.server.id]['status']=True
            if players[msg.message.server.id]['status'] == True:
                await bot.say("Audio already paused")

        else:
            await bot.say("No audio playing in voice channel")
    else:
        await bot.say("No audio in voice channel")
    

@bot.command(pass_context=True)
async def resume(msg):
    if msg.message.server.id in players:
        if players[msg.message.server.id]['stream'] !=None:
            if players[msg.message.server.id]['status'] == True:
                players[msg.message.server.id]['stream'].resume()
            if players[msg.message.server.id]['status'] == False:
                await bot.say("Audio already playing")
        else:
            await bot.say("No audio playing in voice channel")
    else:
        await bot.say("No audio playing in voice channel")



@bot.command(pass_context=True)
async def volume(msg,vol:float):
    if msg.message.server.id in players:
        if players[msg.message.server.id]['stream'] !=None:
            players[msg.message.server.id]['stream'].volume(vol)

#TODL: complete this volume options and make it better if possible

@bot.command(pass_context=True)
async def skip(msg):
    pass


@bot.command(pass_context=True)
async def clear_songs(msg):
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
    if msg.message.server.id in players:
        if players[msg.message.server.id]['songs']:
            song_order=discord.Embed(title='Songs')
            for i in players[msg.message.server.id]['songs']:
                song_order.add_field(name=i['author'].display_name,value=i['title'],inline=False)
            await bot.say(embed=song_order)
        else:
            await bot.say("Currently no songs in queue")



bot.run('bot token')
