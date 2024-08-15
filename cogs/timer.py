import datetime
import random
import sys
from time import perf_counter
from typing import Final

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.triggers.combining import OrTrigger  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from sqlalchemy import delete, select  # type: ignore
from sqlalchemy.ext.asyncio import create_async_engine  # type: ignore

from languages import LANGUAGES
from translations import TRANSLATIONS
from modals.channels import CrateRespawnChannel, CargoScrambleChannel

utc = datetime.timezone.utc

config = dotenv_values(".env")

if config["DATABASE_STRING"]:
    engine: Final = create_async_engine(config["DATABASE_STRING"])
else:
    print("Please set the DATABASE or DATABASE_STRING value in the .env file and restart the bot.")
    sys.exit(1)

def me_only(interaction: discord.Interaction) -> bool:
    return interaction.user.id == int(config["MY_USER_ID"]) # type: ignore

MY_GUILD_ID = discord.Object(int(config["TESTING_GUILD_ID"])) # type: ignore


class TimerCog(commands.Cog):
    def __init__(self, bot):
        self.bot: Final[commands.Bot] = bot
        self.scheduler: Final = AsyncIOScheduler(timezone=utc)

    def cog_load(self):
        if not self.scheduler.running:
            cargo_trigger = OrTrigger([
                CronTrigger(hour='11,14,21', minute=55, timezone=utc),
                CronTrigger(hour=18, minute=25, timezone=utc)
                ])
            self.scheduler.add_job(self.generate_alert, 'cron', name='crate_respawn_alert', args=['crate'], coalesce=False, hour='0,4,8,12,16,20', minute=0)
            self.scheduler.add_job(self.generate_alert, cargo_trigger, name='cargo_spawn_alert', args=['cargo'], coalesce=False)
            self.scheduler.add_job(self.update_stats, 'interval', name='update_stats', minutes=6)
            self.scheduler.start()

    def cog_unload(self):
        self.scheduler.remove_all_jobs()
        self.scheduler.shutdown(wait=False)


    async def update_stats(self):
        stats_chan: discord.VoiceChannel = self.bot.get_channel(int(config["COUNT_CHAN"])) # type: ignore
        await stats_chan.edit(name=f'{len(self.bot.guilds)} Servers')


    async def generate_alert(self, alert_type: str):
        start = perf_counter()
        for _ in range(5):
            try:
                guilds_sent = 0
                errors = 0
                time_now = datetime.datetime.now(tz=utc)
                print(f"[{alert_type.upper()}] Timer start: {time_now}")
                async with engine.begin() as conn:
                    if alert_type == 'cargo':
                        all_channels = await conn.execute(select(CargoScrambleChannel.channel_id, CargoScrambleChannel.role_id))
                    elif alert_type == 'crate':
                        all_channels = await conn.execute(select(CrateRespawnChannel.channel_id, CrateRespawnChannel.role_id))
                    all_channels = all_channels.all()
                await engine.dispose(close=True)
                random.shuffle(all_channels)
                for channel_id, role_id in all_channels:
                    cur_chan = self.bot.get_channel(channel_id)
                    if cur_chan is None:
                        async with engine.begin() as conn:
                            if alert_type == 'cargo':
                                await conn.execute(delete(CargoScrambleChannel).filter_by(channel_id=channel_id))
                            elif alert_type == 'crate':
                                await conn.execute(delete(CrateRespawnChannel).filter_by(channel_id=channel_id))
                        await engine.dispose(close=True)
                        print(f"Channel not found: {channel_id}.  Deleted.")
                        errors += 1
                        continue
                    if (not cur_chan.permissions_for(cur_chan.guild.me).send_messages or not cur_chan.permissions_for(cur_chan.guild.me).view_channel): # type: ignore
                        async with engine.begin() as conn:
                            if alert_type == 'cargo':
                                await conn.execute(delete(CargoScrambleChannel).filter_by(channel_id=channel_id))
                            elif alert_type == 'crate':
                                await conn.execute(delete(CrateRespawnChannel).filter_by(channel_id=channel_id))
                        await engine.dispose(close=True)
                        errors += 1
                        print(f"Deleted {cur_chan.name} (channel_id: {channel_id}) @ {cur_chan.guild.name} (guild_id: {cur_chan.guild.id}) due to missing permissions.") # type: ignore
                        continue
                    if role_id is not None: # type: ignore
                        role_to_mention = cur_chan.guild.get_role(role_id) # type: ignore
                    else:
                        role_to_mention = None
                    try:
                        dest = LANGUAGES.get(str(cur_chan.guild.preferred_locale).lower()) # type: ignore
                        if dest is None:
                            dest = 'en'
                        if alert_type == 'cargo':
                            cargo_timestamp = int(datetime.datetime.timestamp(time_now + datetime.timedelta(minutes=5)))
                            reset_embed = discord.Embed(color=discord.Color.blurple(),title="Once Human Cargo Scramble Spawn")
                            reset_embed.add_field(name='', value=TRANSLATIONS[dest]['cargo_scramble_alert_message'].format(f'<t:{cargo_timestamp}:R>'))
                        elif alert_type == 'crate':
                            crate_timestamp = int(datetime.datetime.timestamp(time_now.replace(minute=0, second=0, microsecond=0)))
                            reset_embed = discord.Embed(color=discord.Color.blurple(),title="Once Human Gear/Weapon Crates Reset")
                            reset_embed.add_field(name='', value=TRANSLATIONS[dest]['crate_respawn_alert_message'].format(f'<t:{crate_timestamp}:t>'))
                            reset_embed.set_footer(text=TRANSLATIONS[dest]['crate_respawn_footer'])
                        await cur_chan.send(content=f"{role_to_mention.mention if role_to_mention is not None else ''}", embed=reset_embed) # type: ignore
                        guilds_sent += 1
                    except Exception as e:
                        print(f"Deleted {cur_chan.name} (channel_id: {channel_id}) @ {cur_chan.guild.name} (guild_id: {cur_chan.guild.id}) due to {e}") # type: ignore
                        async with engine.begin() as conn:
                            if alert_type == 'cargo':
                                await conn.execute(delete(CargoScrambleChannel).filter_by(channel_id=channel_id))
                            elif alert_type == 'crate':
                                await conn.execute(delete(CrateRespawnChannel).filter_by(channel_id=channel_id))
                        await engine.dispose(close=True)
                        errors += 1
                        continue
                end = perf_counter()
                elapsed = end - start
                if elapsed >= 3600:
                    elapsed = f"{(end - start)/3660:.2f} hours"
                elif elapsed >= 60:
                    elapsed = f"{(end - start)/60:.2f} minutes"
                else:
                    elapsed = f"{(end - start):.2f} seconds"
                print(f"[{alert_type.upper()}] Sent to {guilds_sent} guilds.  Errors: {errors}\n[{alert_type.upper()}] Bot currently in {len(self.bot.guilds)} guilds.\n[{alert_type.upper()}] Time taken: {elapsed}")
            except Exception as e:
                err = e
                continue
            else:
                break
        else:
            raise err # type: ignore


    @app_commands.command(name='check_timers', description='Returns all running timer jobs.')
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def check_running_timers(self, interaction: discord.Interaction):
        jobs_info = ""
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            jobs_info += f"### {job.name}\nTrigger: {job.trigger}\nNext run: <t:{int(datetime.datetime.timestamp(job.next_run_time))}:R>\n"
        await interaction.response.send_message(f"## Running jobs = {len(jobs)}\n{jobs_info}", delete_after=120, ephemeral=True)


    @app_commands.command(name='next', description='Returns the current UTC time and the next respawn timer.')
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.guild_install()
    async def what_time_is_it(self, interaction: discord.Interaction):
        if interaction.guild:
            await interaction.response.defer(ephemeral=True)
            dest = LANGUAGES.get(str(interaction.guild.preferred_locale).lower())
            if dest is None:
                dest = 'en'
            time_now = datetime.datetime.now(tz=utc)
            crate_job = [job for job in self.scheduler.get_jobs() if job.name=="crate_respawn_alert"][0]
            cargo_job = [job for job in self.scheduler.get_jobs() if job.name=="cargo_spawn_alert"][0]
            next_crate_time_timestamp = int(datetime.datetime.timestamp(crate_job.next_run_time))
            next_cargo_time_timestamp = int(datetime.datetime.timestamp(cargo_job.next_run_time + datetime.timedelta(minutes=5)))
            await interaction.followup.send(content=TRANSLATIONS[dest]['next_respawns_message'].format(f"{time_now.hour:02d}", f"{time_now.minute:02d}", f"<t:{next_crate_time_timestamp}:F>", f"<t:{int(next_crate_time_timestamp)}:R>", f"<t:{next_cargo_time_timestamp}:F>", f"<t:{int(next_cargo_time_timestamp)}:R>"), wait=True)
            #await msg.delete(delay=60)
        else:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(TimerCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(TimerCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")