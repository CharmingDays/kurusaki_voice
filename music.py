import discord,asyncio,time,datetime,names,random,pymongo,youtube_dl,string,os,functools
from discord.ext import commands
from discord.ext.commands import command



#TODO: CREATE PLAYLIST SUPPORT FOR MUSIC




ytdl_format_options= {
    'format': 'bestaudio/best',
    'outtmpl': '{}',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    "extractaudio":True,
    "audioformat":"opus",
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

stim= {
    'default_search': 'auto',
    'quiet': True,
    "no_warnings": True,
    "simulate": True,  # do not keep the video files
    "nooverwrites": True,
    "keepvideo": False,
    "noplaylist": True,
    "skip_download": False,
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}


ffmpeg_options = {
    'options': '-vn'
}

class Downloader(discord.PCMVolumeTransformer):
    def __init__(self,source,*,data,volume=0.6):
        super().__init__(source,volume)
        self.data=data
        self.title=data.get('title')
        self.url=data.get("url")
        self.thumbnail=data.get('thumbnail')
        self.duration=data.get('duration')
        self.views=data.get('view_count')

    @classmethod
    async def video_url(cls,url,ytdl,*,loop=None,stream=False):
        loop=loop or asyncio.get_event_loop()
        data= await loop.run_in_executor(None,lambda: ytdl.extract_info(url,download=not stream))
    

        if 'entries' in data:
            #Is a list
            #Take first item from a playlist
            data=data['entries'][0]

        filename=data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename,**ffmpeg_options),data=data)

    @classmethod
    async def get_info(cls,url):
        yt=youtube_dl.YoutubeDL(stim)
        down=yt.extract_info(url,download=False)
        if 'entries' in down:
            down=down['entries'][0]['title']

        return down
        



class MusicPlayer(commands.Cog):
    def __init__(self,client):
        self.bot=client
        self.player={
            "audio_files":[],
            "guildId":{
                "player":'player object', #NOTE: get current songs from player
                'queue':[{'title':'the sound of silence','author':'`user object`'},{'title':"Hello - Adle",'author':'`user object`'}],
                'play':'True or False',
                'name':'current audio file name',
                'author':'user obj'
            }
        }
        self.database='pymongoconnection'
        self.music_data={
            "guildID":{
                "playlist":[],
                'volume':'default is .6'
            }
        }


    @commands.Cog.listener('on_voice_state_update')
    async def music_voice(self,user,before,after):
        if after.channel == None and user.id == self.bot.user.id:
            self.player[user.guild.id]['queue'].clear()


    async def filename_generator(self):
        chars=list(string.ascii_letters+string.digits)
        name=''
        for i in range(random.randint(9,25)):
            name+=random.choice(chars)
        
        if name not in self.player['audio_files']:
            return name

        else:
            return await self.filename_generator()



    async def queue(self,msg,song):
        title=await Downloader.get_info(song)
        self.player[msg.guild.id]['queue'].append({'title':title,'author':msg})
        await msg.send(f"**{title} added to queue**".title(),delete_after=60)



    async def voice_check(self,msg):
        """
        function used to make bot leave voice channel if music not being played for longer than 2 minutes
        """
        if msg.voice_client != None:
            await asyncio.sleep(120)
            if msg.voice_client != None and msg.voice_client.is_playing() == False and msg.voice_client.is_paused() == False:
                await msg.voice_client.disconnect()


    async def clear_data(self,msg):
        name=self.player[msg.guild.id]['name']
        os.remove(name)
        self.player['audio_files'].remove(name)


    async def done(self,msg):
        await self.clear_data(msg)
        if self.player[msg.guild.id]['queue']:
            queue_data=self.player[msg.guild.id]['queue'].pop(0)
            return await self.start_song(msg=queue_data['author'],song=queue_data['title'])

        else:
            self.player[msg.guild.id]['play']=False
            await self.voice_check(msg)
    

    async def start_song(self,msg,song):
        new_opts=ytdl_format_options.copy()
        audio_name=await self.filename_generator()

        self.player['audio_files'].append(audio_name)
        new_opts['outtmpl']=new_opts['outtmpl'].format(audio_name)

        ytdl=youtube_dl.YoutubeDL(new_opts)
        download=await Downloader.video_url(song,ytdl=ytdl,loop=self.bot.loop)

        self.player[msg.guild.id]['name']=audio_name

        emb=discord.Embed(title='Now Playing',description=download.title,url=download.url)
        emb.set_thumbnail(url=download.thumbnail)
        emb.set_footer(text=f'Requested by {msg.author.name}',icon_url=msg.author.avatar_url)
        loop=asyncio.get_event_loop()
        msg.voice_client.play(download,after=lambda a: loop.create_task(self.done(msg)))
        await msg.send(embed=emb,delete_after=download.duration)
        self.player[msg.guild.id]['player']=download
        self.player[msg.guild.id]['author']=msg
        return msg.voice_client




    @command()
    async def play(self,msg,*,song):
        if msg.guild.id in self.player:
            if self.player[msg.guild.id]['play'] == True:
                return await self.queue(msg,song)

            if self.player[msg.guild.id]['queue']:
                return await self.queue(msg,song)

            if self.player[msg.guild.id]['play'] == False and not self.player[msg.guild.id]['queue']:
                return await self.start_song(msg,song)


        else:
            self.player[msg.guild.id]={
                'player':None,
                'queue':[],
                'play':True,
                'author':msg,
                'name':None
            }
            return await self.start_song(msg,song)


    @play.before_invoke
    async def before_play(self,msg):
        """
        Check voice_client
            - User voice = None:
                please join a voice channel
            - bot voice == None:
                joins the user's voice channel
            - user and bot voice NOT SAME:
                - music NOT Playing AND queue EMPTY
                    join user's voice channel
                - items in queue:
                    please join the same voice channel as the bot to add song to queue
        """
    
        if msg.author.voice == None:
            return await msg.send('**Please join a voice channel to play music**'.title())

        if msg.voice_client == None: 
            return await msg.author.voice.channel.connect()


        if msg.voice_client.channel != msg.author.voice.channel:
            if msg.voice_client.is_playing() == False and not self.player[msg.guild.id]['queue']: #NOTE: Check player and queue 
                return await msg.voice_client.move_to(msg.author.voice.channel)
                #NOTE: move bot to user's voice channel if queue does not exist
            
            if self.player[msg.guild.id]['queue']:
                #NOTE: user must join same voice channel if queue exist
                return await msg.send("Please join the same voice channel as the bot to add song to queue")
            
        
    @command()
    async def repeat(self,msg):
        """
        repeat the currently playing
        """


    @command()
    async def skip(self,msg):
        if msg.author.voice != None:
            if msg.author.voice.channel != msg.voice_client.channel:
                return await msg.send("Please join the same voice channel as the bot")

        if msg.author.voice == None:
            return await msg.send("Please join the same voice channel as the bot")

        if msg.voice_client == None:
            return await msg.send("**No music currently playing**".title(),delete_after=60)
        
        else:
            if not self.player[msg.guild.id]['queue'] and self.player[msg.guild.id]['play'] == False:
                return await msg.send("**No songs in queue to skip**".title(),delete_after=60)

        
        await msg.send("**Skipping song...**".title(),delete_after=20)
        msg.voice_client.stop()

    
    @commands.has_permissions(manage_channels=True)
    @command()
    async def stop(self,msg):
        if msg.author.voice != None and msg.voice_client != None:
            if  msg.voice_client.is_playing() == True or self.player[msg.guild.id]['queue']:
                self.player[msg.guild.id]['queue'].clear()
                msg.voice_client.stop()
                return await msg.voice_client.disconnect()






    @command(name='queue',aliases=['song-list','q','current-songs'])
    async def _queue(self,msg):
        if msg.voice_client != None:
            if msg.guild.id in self.player:
                if self.player[msg.guild.id]['queue']:
                    emb=discord.Embed(title='queue')
                    emb.set_footer(text=f'Command used by {msg.author.name}',icon_url=msg.author.avatar_url)
                    for i in self.player[msg.guild.id]['queue']:
                        emb.add_field(name=f"**{i['author'].author.name}**",value=i['title'],inline=False)
                    return await msg.send(embed=emb,delete_after=120)


        return await msg.send("No songs in queue")


    @command(name='current-song',aliases=['song?'])
    async def current_song(self,msg):
        if msg.voice_client != None and msg.voice_client.is_playing() == True:
            emb=discord.Embed(title='Currently Playing',description=self.player[msg.guild.id]['player'].title)
            emb.set_footer(text=f"{self.player[msg.guild.id]['author'].author.name}",icon_url=msg.author.avatar_url)
            emb.set_thumbnail(url=self.player[msg.guild.id]['player'].thumbnail)
            return await msg.send(embed=emb,delete_after=120)
        
        return await msg.send(f"**No songs currently playing**".title(),delete_after=30)



    @command(aliases=['move-to','move'])
    async def join(self, msg, *, channel: discord.VoiceChannel=None):
        """
        skip if:
            - admin perms
            - no perms:
                current song not by skip requester
                    make vote
                current song my skip requester
                    skip current one

                only 1 person in voice and song not by skip requester
                
        """

        if msg.voice_client == None:
            if channel == None:
                return await msg.author.voice.channel.connect()
            else:
                return await channel.connect()
        
        else:
            if self.player[msg.guild.id]['play'] == False and not self.player[msg.guild.id]['queue']:
                return await msg.author.voice.channel.connect()


    @join.before_invoke
    async def before_join(self,msg):
        if msg.author.voice == None:
            return await msg.send("You are not in a voice channel")



    @join.error
    async def join_error(self,msg,error):
        if isinstance(error,commands.errors.BadArgument):
            return msg.send(error)

        # if error.args[0] == 'Command raised an exception: Exception: queue':
        #     return await msg.send("**Please join the same voice channel as the bot to add song to queue**".title())

        if error.args[0] == 'Command raised an exception: Exception: playing':
            return await msg.send("**Please join the same voice channel as the bot to add song to queue**".title())

    @commands.has_permissions(manage_channels=True)
    @command(aliases=['vol'])
    async def volume(self,msg,vol:float):
        if msg.author.voice != None:
            if msg.voice_client != None:
                if msg.voice_client.channel == msg.author.voice.channel and msg.voice_client.is_playing() == True:
                    msg.voice_client.source.volume=vol
                    return f"Volume {vol}"


        
        return await msg.send("**Please join the same voice channel as the bot to use the command**".title(),delete_after=30)
    
    @volume.error
    async def volume_error(self,msg,error):
        if isinstance(error,commands.errors.MissingPermissions):
            return await msg.send("Manage channels or admin perms required to change volume",delete_after=30)



def setup(bot):
    bot.add_cog(MusicPlayer(bot))








#TODO: REUSE SAME PLAYER FOR EACH SERVER FOR BETTER CONTROL AND VOLUME CONTROL 

#TODO: OR RESTORE DEAFULT VALUES LIKE VOLUME INTO NEW PLAYER AT RELAUNCH
