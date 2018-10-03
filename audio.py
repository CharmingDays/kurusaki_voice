import discord
import asyncio
import youtube_dl
import os
from discord.ext import commands
from discord.ext.commands import Bot


bot=commands.Bot(command_prefix='a.')

from discord import opus
OPUS_LIBS = ['libopus-0.x86.dll', 'libopus-0.x64.dll',
             'libopus-0.dll', 'libopus.so.0', 'libopus.0.dylib']


def load_opus_lib(opus_libs=OPUS_LIBS):
    if opus.is_loaded():
        return True

    for opus_lib in opus_libs:
            try:
                opus.load_opus(opus_lib)
                return
            except OSError:
                pass

    raise RuntimeError('Could not load an opus lib. Tried %s' %
                       (', '.join(opus_libs)))
load_opus_lib()

in_voice=[]


@bot.event
async def on_ready():
    print("hi")    
    
@bot.command(pass_context=True)
async def join(ctx):
    channel = ctx.message.author.voice.voice_channel
    await bot.join_voice_channel(channel)
    in_voice.append(ctx.message.server.id)


play_in=[]
players={}
songs={}
playing={}
@bot.command(pass_context=True)
async def play(ctx, *,url):
    opts = {
            'default_search': 'auto',
            'quiet': True,
        }
    def player_in(con):
        if len(songs[con.message.server.id]) == 0:
            playing[con.message.server.id]=False

        if len(songs[con.message.server.id]) != 0:
            songs[con.message.server.id].start()
    try:
        if playing[ctx.message.server.id] == True:
            voice = bot.voice_client_in(ctx.message.server)
            song=await voice.create_ytdl_player()
            songs[ctx.message.server.id]=[]
            songs[ctx.message.server.id].append(song)
    except KeyError:
        pass
    if ctx.message.server.id not in in_voice:
      channel = ctx.message.author.voice.voice_channel
      await bot.join_voice_channel(channel)
      in_voice.append(ctx.message.server.id)
      
    voice = bot.voice_client_in(ctx.message.server)
    global player
    player = await voice.create_ytdl_player(url,ytdl_options=opts,after= lambda : player_in(ctx))
    players[ctx.message.server.id] = player
    play_in.append(player)
    if players[ctx.message.server.id].is_live == True:
        await bot.say("Can not play live audio yet.")
    elif players[ctx.message.server.id].is_live == False:
        player.start()
        playing[ctx.message.server.id]=True

@bot.command(pass_context=True)
async def pause(ctx):
    players[ctx.message.server.id].pause()

@bot.command(pass_context=True)
async def resume(ctx):
    players[ctx.message.server.id].resume()
          
@bot.command(pass_context=True)
async def volume(ctx, vol:float):
    volu = float(vol)
    players[ctx.message.server.id].volume=vol

@bot.command(pass_context=True)
async def stop(ctx):
    pos=in_voice.index(ctx.message.server.id)
    del in_voice[pos]
    server=ctx.message.server
    voice_client=bot.voice_client_in(server)
    await voice_client.disconnect()



bot.run(os.environ['BOT_TOKEN'])
