import asyncio
import logging
import typing
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import imageio_ffmpeg

logger = logging.getLogger("discord_bot.music")

# YTDL Configuration with YouTube Bot Verification Bypass
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios', 'mweb'],
        }
    }
}

FFMPEG_BEFORE_OPTIONS = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
FFMPEG_OPTIONS = '-vn'

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

def get_ffmpeg_path():
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        logger.error(f"Failed to resolve imageio-ffmpeg path: {e}")
        return "ffmpeg"

class YTDLSource:
    @classmethod
    async def extract_info(cls, query: str) -> dict:
        loop = asyncio.get_event_loop()

        def _extract():
            try:
                return ytdl.extract_info(query, download=False)
            except Exception as e:
                logger.warning(f"Primary YTDL extraction failed: {e}. Trying secondary Android/iOS client...")
                fallback_opts = dict(YTDL_OPTIONS)
                fallback_opts['extractor_args'] = {'youtube': {'player_client': ['android_creator', 'android', 'ios']}}
                with yt_dlp.YoutubeDL(fallback_opts) as fallback_ytdl:
                    return fallback_ytdl.extract_info(query, download=False)

        data = await loop.run_in_executor(None, _extract)
        if data and 'entries' in data and data['entries']:
            data = data['entries'][0]
        return data

    @classmethod
    def create_audio_source(cls, stream_url: str, volume: float = 0.5) -> discord.PCMVolumeTransformer:
        ffmpeg_exe = get_ffmpeg_path()
        audio = discord.FFmpegPCMAudio(
            stream_url,
            executable=ffmpeg_exe,
            before_options=FFMPEG_BEFORE_OPTIONS,
            options=FFMPEG_OPTIONS
        )
        return discord.PCMVolumeTransformer(audio, volume=volume)

class Song:
    def __init__(self, title: str, stream_url: str, web_url: str, duration: int, thumbnail: str, requester: discord.Member):
        self.title = title
        self.stream_url = stream_url
        self.web_url = web_url
        self.duration = duration
        self.thumbnail = thumbnail
        self.requester = requester

    def formatted_duration(self) -> str:
        if not self.duration:
            return "Live Stream"
        minutes, seconds = divmod(int(self.duration), 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

class GuildMusicQueue:
    def __init__(self, bot: commands.Bot, guild_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.queue: list[Song] = []
        self.current: typing.Optional[Song] = None
        self.volume: float = 0.5
        self.voice_client: typing.Optional[discord.VoiceClient] = None
        self.text_channel: typing.Optional[discord.TextChannel] = None
        self.disconnect_timer: typing.Optional[asyncio.Task] = None

    def cancel_disconnect_timer(self):
        if self.disconnect_timer and not self.disconnect_timer.done():
            self.disconnect_timer.cancel()
            self.disconnect_timer = None

    def start_disconnect_timer(self):
        self.cancel_disconnect_timer()
        self.disconnect_timer = asyncio.create_task(self._auto_disconnect_after_delay())

    async def _auto_disconnect_after_delay(self):
        await asyncio.sleep(300) # 5 minutes idle
        if self.voice_client and self.voice_client.is_connected() and not self.voice_client.is_playing():
            if self.text_channel:
                try:
                    await self.text_channel.send("💤 Left voice channel due to 5 minutes of inactivity.")
                except Exception:
                    pass
            await self.voice_client.disconnect()
            self.voice_client = None

    def play_next_song(self, error=None):
        if error:
            logger.error(f"Player error in guild {self.guild_id}: {error}")

        self.current = None

        if self.queue:
            next_song = self.queue.pop(0)
            self.current = next_song
            try:
                source = YTDLSource.create_audio_source(next_song.stream_url, self.volume)
                self.voice_client.play(source, after=lambda e: self.bot.loop.call_soon_threadsafe(self.play_next_song, e))

                if self.text_channel:
                    embed = discord.Embed(
                        title="🎶 Now Playing",
                        description=f"[{next_song.title}]({next_song.web_url})",
                        color=discord.Color.purple()
                    )
                    embed.add_field(name="Duration", value=next_song.formatted_duration(), inline=True)
                    embed.add_field(name="Requested By", value=next_song.requester.mention, inline=True)
                    if next_song.thumbnail:
                        embed.set_thumbnail(url=next_song.thumbnail)
                    asyncio.run_coroutine_threadsafe(self.text_channel.send(embed=embed), self.bot.loop)
            except Exception as e:
                logger.error(f"Error starting playback of next song: {e}")
                if self.text_channel:
                    asyncio.run_coroutine_threadsafe(
                        self.text_channel.send(f"❌ Failed to play `{next_song.title}`: {e}"),
                        self.bot.loop
                    )
                self.play_next_song()
        else:
            self.start_disconnect_timer()

class MusicCog(commands.Cog, name="Music"):
    """High-quality Music Player slash commands with YouTube streaming and queue support."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_queues: dict[int, GuildMusicQueue] = {}

    def get_queue(self, guild: discord.Guild) -> GuildMusicQueue:
        if guild.id not in self.guild_queues:
            self.guild_queues[guild.id] = GuildMusicQueue(self.bot, guild.id)
        return self.guild_queues[guild.id]

    async def ensure_voice(self, interaction: discord.Interaction) -> typing.Optional[discord.VoiceClient]:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be connected to a voice channel to use music commands!", ephemeral=True)
            return None

        user_channel = interaction.user.voice.channel
        guild_queue = self.get_queue(interaction.guild)

        if interaction.guild.voice_client:
            if interaction.guild.voice_client.channel != user_channel:
                await interaction.response.send_message(f"❌ I'm already in `{interaction.guild.voice_client.channel.name}`!", ephemeral=True)
                return None
            guild_queue.voice_client = interaction.guild.voice_client
            return interaction.guild.voice_client
        else:
            try:
                vc = await user_channel.connect()
                guild_queue.voice_client = vc
                return vc
            except discord.Forbidden:
                await interaction.response.send_message("❌ I lack permissions to join or speak in your voice channel!", ephemeral=True)
                return None
            except Exception as e:
                await interaction.response.send_message(f"❌ Could not connect to voice channel: {e}", ephemeral=True)
                return None

    @app_commands.command(name="play", description="Play audio from a YouTube link or search query.")
    @app_commands.describe(query="YouTube URL or search keywords (e.g. 'Chill lofi hip hop')")
    async def play(self, interaction: discord.Interaction, query: str):
        vc = await self.ensure_voice(interaction)
        if not vc:
            return

        await interaction.response.defer()

        guild_queue = self.get_queue(interaction.guild)
        guild_queue.text_channel = interaction.channel
        guild_queue.cancel_disconnect_timer()

        try:
            data = await YTDLSource.extract_info(query)
            if not data:
                await interaction.followup.send("❌ Could not find any audio matching your search query.")
                return

            song = Song(
                title=data.get('title', 'Unknown Track'),
                stream_url=data.get('url'),
                web_url=data.get('webpage_url', query),
                duration=data.get('duration', 0),
                thumbnail=data.get('thumbnail'),
                requester=interaction.user
            )

            if vc.is_playing() or vc.is_paused():
                guild_queue.queue.append(song)
                embed = discord.Embed(
                    title="📝 Added to Queue",
                    description=f"[{song.title}]({song.web_url})",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Position in Queue", value=f"`#{len(guild_queue.queue)}`", inline=True)
                embed.add_field(name="Duration", value=song.formatted_duration(), inline=True)
                embed.add_field(name="Requested By", value=interaction.user.mention, inline=True)
                if song.thumbnail:
                    embed.set_thumbnail(url=song.thumbnail)
                await interaction.followup.send(embed=embed)
            else:
                guild_queue.current = song
                source = YTDLSource.create_audio_source(song.stream_url, guild_queue.volume)
                vc.play(source, after=lambda e: self.bot.loop.call_soon_threadsafe(guild_queue.play_next_song, e))

                embed = discord.Embed(
                    title="🎶 Now Playing",
                    description=f"[{song.title}]({song.web_url})",
                    color=discord.Color.purple()
                )
                embed.add_field(name="Duration", value=song.formatted_duration(), inline=True)
                embed.add_field(name="Requested By", value=interaction.user.mention, inline=True)
                if song.thumbnail:
                    embed.set_thumbnail(url=song.thumbnail)
                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error processing play command: {e}")
            await interaction.followup.send(f"❌ An error occurred while processing your request: {e}")

    @app_commands.command(name="pause", description="Pause current music playback.")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            await interaction.response.send_message("❌ Nothing is currently playing!", ephemeral=True)
            return
        vc.pause()
        await interaction.response.send_message("⏸️ Playback paused.")

    @app_commands.command(name="resume", description="Resume paused music playback.")
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_paused():
            await interaction.response.send_message("❌ Playback is not paused!", ephemeral=True)
            return
        vc.resume()
        await interaction.response.send_message("▶️ Playback resumed.")

    @app_commands.command(name="skip", description="Skip the current track.")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or (not vc.is_playing() and not vc.is_paused()):
            await interaction.response.send_message("❌ Nothing is currently playing to skip!", ephemeral=True)
            return
        vc.stop() # triggers play_next_song after callback
        await interaction.response.send_message("⏭️ Skipped current track.")

    @app_commands.command(name="stop", description="Stop music, clear queue, and leave voice channel.")
    async def stop(self, interaction: discord.Interaction):
        guild_queue = self.get_queue(interaction.guild)
        guild_queue.queue.clear()
        guild_queue.current = None
        guild_queue.cancel_disconnect_timer()

        vc = interaction.guild.voice_client
        if vc:
            if vc.is_playing() or vc.is_paused():
                vc.stop()
            await vc.disconnect()
            guild_queue.voice_client = None
            await interaction.response.send_message("⏹️ Playback stopped, queue cleared, and disconnected from voice channel.")
        else:
            await interaction.response.send_message("❌ Bot is not connected to a voice channel.", ephemeral=True)

    @app_commands.command(name="leave", description="Disconnect bot from voice channel.")
    async def leave(self, interaction: discord.Interaction):
        await self.stop(interaction)

    @app_commands.command(name="queue", description="Display the current song queue.")
    async def queue(self, interaction: discord.Interaction):
        guild_queue = self.get_queue(interaction.guild)
        embed = discord.Embed(
            title="🎶 Music Queue",
            color=discord.Color.gold()
        )

        if guild_queue.current:
            embed.add_field(
                name="Now Playing",
                value=f"[{guild_queue.current.title}]({guild_queue.current.web_url}) | `{guild_queue.current.formatted_duration()}` (Requested by {guild_queue.current.requester.mention})",
                inline=False
            )
        else:
            embed.description = "No track currently playing."

        if guild_queue.queue:
            upcoming_list = []
            for idx, song in enumerate(guild_queue.queue[:10], start=1):
                upcoming_list.append(f"`#{idx}` [{song.title}]({song.web_url}) (`{song.formatted_duration()}`) - {song.requester.mention}")
            
            queue_str = "\n".join(upcoming_list)
            if len(guild_queue.queue) > 10:
                queue_str += f"\n\n*...and {len(guild_queue.queue) - 10} more track(s)*"
            embed.add_field(name="Up Next", value=queue_str, inline=False)
        else:
            if guild_queue.current:
                embed.add_field(name="Up Next", value="No upcoming tracks in queue. Add more with `/play`!", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nowplaying", description="Show details for the currently playing track.")
    async def nowplaying(self, interaction: discord.Interaction):
        guild_queue = self.get_queue(interaction.guild)
        if not guild_queue.current:
            await interaction.response.send_message("❌ Nothing is currently playing!", ephemeral=True)
            return

        song = guild_queue.current
        embed = discord.Embed(
            title="🎶 Currently Playing",
            description=f"[{song.title}]({song.web_url})",
            color=discord.Color.purple()
        )
        embed.add_field(name="Duration", value=song.formatted_duration(), inline=True)
        embed.add_field(name="Requested By", value=song.requester.mention, inline=True)
        embed.add_field(name="Volume", value=f"`{int(guild_queue.volume * 100)}%`", inline=True)
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="volume", description="Set audio playback volume (1-100%).")
    @app_commands.describe(level="Volume level from 1 to 100")
    async def volume(self, interaction: discord.Interaction, level: app_commands.Range[int, 1, 100]):
        guild_queue = self.get_queue(interaction.guild)
        guild_queue.volume = level / 100.0

        vc = interaction.guild.voice_client
        if vc and vc.source and hasattr(vc.source, 'volume'):
            vc.source.volume = guild_queue.volume

        await interaction.response.send_message(f"🔊 Playback volume set to `{level}%`.")

async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot))
