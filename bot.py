import discord,asyncio,youtube_dl
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()


exts=['lava'] #Add your Cog extensions here


def get_prefix(bot, msg):
    """A callable Prefix for our bot. This could be edited to allow per server prefixes."""

    prefixes = ['s.'] #Your bot prefix(s)

    return commands.when_mentioned_or(*prefixes)(bot, msg)

bot=commands.Bot(command_prefix=get_prefix,description='Multipurpose Discord Bot')






@bot.event
async def on_ready():
    song_name='TWICE - What is love?'  #Status name
    activity_type=discord.ActivityType.listening #Status type
    await bot.change_presence(activity=discord.Activity(type=activity_type,name=song_name))

    for i in exts:
        bot.load_extension(i)
    print(bot.user.name)







bot.run(os.environ['TOKEN'])