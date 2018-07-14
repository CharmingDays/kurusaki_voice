import discord
import asyncio
import youtube_dl
import os






players={}
@bot.command(pass_context=True)
async def play(ctx, url):
    global play_server
    play_server = ctx.message.server
    voice = bot.voice_client_in(play_server)
    global player
    player = await voice.create_ytdl_player(url)
    players[play_server.id] = player
    if player.is_live == True:
        await bot.say("Can not play live audio yet.")
    elif player.is_live == False:
        player.start()
        embed = discord.Embed(title="Currently Playing", color=0xDEADBF)
        embed.add_field(name='Title', value=player.title, inline=False)
        embed.add_field(name='Duration', value=player.duration, inline=False)
        embed.add_field(name='Views', value=player.views, inline=False)
        await bot.say(embed=embed)


async def pause(ctx):
    player.pause()

@bot.command(pass_context=True)
async def resume(ctx):
    player.resume()
          
@bot.command(pass_context=True)
async def volume(ctx, vol):
    vol = float(vol)
    vol = player.volume = vol

@bot.command(pass_context=True)
async def stop(ctx):
    server=ctx.message.server
    voice_client=bot.voice_client_in(server)
    await voice_client.disconnect()



bot.run(os.environ['BOT_TOKEN'])
