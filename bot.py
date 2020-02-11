
import discord, requests as rq,asyncio,time,datetime,os,random,youtube_dl
from discord.ext import commands





def get_prefix(bot, msg):
    """A callable Prefix for our bot. This could be edited to allow per server prefixes."""

    # Notice how you can use spaces in prefixes. Try to keep them simple though.
    # prefixes = ['k.','k!','s.'] #NOTE:Heroku
    prefixes = ['k.','k!','bot.','a.'] #NOTE: Local

    return commands.when_mentioned_or(*prefixes)(bot, msg)

bot=commands.Bot(command_prefix=get_prefix,description='Multipurpose Discord Bot')

exts=['API.music','API.text_channel']


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,name='TWICE LIKEY'))
    print(bot.user.name)

@bot.event
async def on_user_update(before,after):
    if before.id == 188386433336082432:
        if before.avatar != after.avatar:
            me=bot.get_user(185181025104560128)
            await me.send(f"New profile changed, {after.avatar_url}")




data1=[]

@bot.command(hidden=True)
async def test(msg,*chan:discord.TextChannel):
    await msg.send("OK")

@commands.is_owner()
@bot.command(name='eval',hidden=True)
async def _eval(msg,*,cmd):
    await msg.send(eval(cmd))









# for i in exts:
#     bot.load_extension(i)



# bot.run(os.environ['TOKEN'])
