import datetime
import random
import traceback
from time import perf_counter
from typing import Final, Optional

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.cron import CronTrigger
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from sqlalchemy import delete, select

from languages import LANGUAGES
from models.channels import (Medics, CargoMutes, CargoScrambleChannel, CrateMutes,
                             CrateRespawnChannel, AutoDelete)
from models.weekly_resets import Purification, Controller, Sproutlet
from translations import TRANSLATIONS

utc = datetime.timezone.utc

config = dotenv_values(".env")


def me_only(interaction: discord.Interaction) -> bool:
    return interaction.user.id == int(config["MY_USER_ID"])

MY_GUILD_ID = discord.Object(int(config["TESTING_GUILD_ID"]))


class TimerCog(commands.Cog):
    def __init__(self, bot):
        self.bot: Final[commands.Bot] = bot
        self.scheduler: Final = AsyncIOScheduler(timezone=utc)

    def cog_load(self):
        if not self.scheduler.running:
            
            # Crate alerts - every 4 hours
            self.scheduler.add_job(self.generate_alert, 'cron', name='crate_respawn_alert', args=['crate'], coalesce=True, hour='0,4,8,12,16,20', minute=0)

            # Cargo alerts - set times with trigger
            cargo_trigger = OrTrigger([
                CronTrigger(hour='11,14,21', minute=55, timezone=utc),
                CronTrigger(hour=18, minute=25, timezone=utc)
                ])
            asian_server_cargo_trigger = OrTrigger([
                CronTrigger(hour='10,13,20', minute=55, timezone=utc),
                CronTrigger(hour=17, minute=25, timezone=utc)
                ])
            self.scheduler.add_job(self.generate_alert, cargo_trigger, name='cargo_spawn_alert', args=['cargo'], coalesce=True)
            self.scheduler.add_job(self.generate_alert, asian_server_cargo_trigger, name='asian_server_cargo_spawn_alert', args=['asian_server_cargo'], coalesce=True)

            # Purification alerts - daily at 07:00 UTC
            self.scheduler.add_job(self.generate_alert, 'cron', name='purification_reset_alert', args=['purification'], coalesce=True, hour=7, minute=0)

            # Controller alerts - daily at 07:00 UTC
            self.scheduler.add_job(self.generate_alert, 'cron', name='controller_reset_alert', args=['controller'], coalesce=True, hour=7, minute=0)

            # Sproutlet alerts - Tuesday, Thursday, Saturday every hour at x:20
            self.scheduler.add_job(self.generate_alert, 'cron', name='sproutlet_alert', args=['sproutlet'], coalesce=True, minute=15, day_of_week='tue,thu,sat')

            # Medics/Trunks alert - every 8 hours
            self.scheduler.add_job(self.generate_alert, 'cron', name='medics_respawn_alert', args=['medics'], coalesce=True, hour='0,8,16', minute=0)

            # Update the # of servers every 6 minutes
            self.scheduler.add_job(self.update_stats, 'interval', name='update_stats', minutes=6)

            self.scheduler.start()


    def cog_unload(self):
        self.scheduler.remove_all_jobs()
        self.scheduler.shutdown(wait=False)

    async def find_cmd(self, bot: commands.Bot, cmd: str, group: Optional[str] = None):
        if group is None:
            command = discord.utils.find(
                lambda c: c.name.lower() == cmd.lower(),
                await bot.tree.fetch_commands(),
            )
            return command
        else:
            cmd_group = discord.utils.find(
                lambda cg: cg.name.lower() == group.lower(),
                await bot.tree.fetch_commands(),
            )
            for child in cmd_group.options:
                if child.name.lower() == cmd.lower():
                    return child


    async def update_stats(self):
        stats_chan: discord.VoiceChannel = self.bot.get_channel(int(config["COUNT_CHAN"]))
        await stats_chan.edit(name=f'🛜 {len(self.bot.guilds):,} Servers')

    
    async def send_log(self, type: str, alert_type: str, message: str, silent: bool = False) -> discord.Message:
        log_channel: discord.TextChannel = self.bot.get_channel(int(config["LOG_CHAN"]))
        log_embed = discord.Embed(description=message[:4096])
        if type == 'error':
            log_embed.color = discord.Color.red()
            log_embed.title = f"Error"
        elif type == 'warn':
            log_embed.color = discord.Color.orange()
            log_embed.title = f"Warning"
        elif type == 'info':
            log_embed.color = discord.Color.blue()
            log_embed.title = f"Info"
        log_embed.title += f" - {alert_type.upper()}"
        if alert_type == 'sproutlet':
            silent = True
        return await log_channel.send(embed=log_embed, silent=silent)


    async def purge_channel(self, alert_type: str, channel_id: int):
        async with self.bot.engine.begin() as conn:
            if alert_type == 'cargo':
                await conn.execute(delete(CargoScrambleChannel).filter_by(channel_id=channel_id))
            elif alert_type == 'crate':
                await conn.execute(delete(CrateRespawnChannel).filter_by(channel_id=channel_id))
            elif alert_type == 'purification':
                await conn.execute(delete(Purification).filter_by(channel_id=channel_id))
            elif alert_type == 'controller':
                await conn.execute(delete(Controller).filter_by(channel_id=channel_id))
            elif alert_type == 'sproutlet':
                await conn.execute(delete(Sproutlet).filter_by(channel_id=channel_id))
            elif alert_type == 'medics':
                await conn.execute(delete(Medics).filter_by(channel_id=channel_id))


    async def generate_alert(self, alert_type: str):
        start = perf_counter()
        for _ in range(5):
            try:
                guilds_sent = 0
                errors = 0
                time_now = datetime.datetime.now(tz=utc)
                print(f"[{alert_type.upper()}] Timer start: {time_now}")
                async with self.bot.engine.begin() as conn:
                    if alert_type == 'cargo':
                        qry_filter = {11: CargoMutes.twelve==False, 14: CargoMutes.fifteen==False, 18: CargoMutes.eighteen_thirty==False, 21: CargoMutes.twenty_two==False}
                        all_channels = await conn.execute(select(CargoScrambleChannel.channel_id, CargoScrambleChannel.role_id, AutoDelete.cargo).where(CargoScrambleChannel.asian_server == False).join(AutoDelete, AutoDelete.guild_id == CargoScrambleChannel.guild_id).join(CargoMutes).filter(qry_filter.get(time_now.hour)))
                    elif alert_type == 'asian_server_cargo':
                        qry_filter = {11: CargoMutes.twelve==False, 14: CargoMutes.fifteen==False, 18: CargoMutes.eighteen_thirty==False, 21: CargoMutes.twenty_two==False}
                        all_channels = await conn.execute(select(CargoScrambleChannel.channel_id, CargoScrambleChannel.role_id, AutoDelete.cargo).where(CargoScrambleChannel.asian == True).join(AutoDelete, AutoDelete.guild_id == CargoScrambleChannel.guild_id).join(CargoMutes).filter(qry_filter.get(time_now.hour)))
                    elif alert_type == 'crate':
                        qry_filter = {0: CrateMutes.zero==False, 4: CrateMutes.four==False, 8: CrateMutes.eight==False, 12: CrateMutes.twelve==False, 16: CrateMutes.sixteen==False, 20: CrateMutes.twenty==False}
                        all_channels = await conn.execute(select(CrateRespawnChannel.channel_id, CrateRespawnChannel.role_id, AutoDelete.crate).join(AutoDelete, AutoDelete.guild_id == CrateRespawnChannel.guild_id).join(CrateMutes).filter(qry_filter.get(time_now.hour)))
                    elif alert_type == 'purification':
                        day_num = datetime.datetime.now(tz=utc).isoweekday()
                        all_channels = await conn.execute(select(Purification.channel_id, Purification.role_id, Purification.auto_delete).filter(Purification.reset_day==day_num))
                    elif alert_type == 'controller':
                        day_num = datetime.datetime.now(tz=utc).isoweekday()
                        all_channels = await conn.execute(select(Controller.channel_id, Controller.role_id, Controller.auto_delete).filter(Controller.reset_day==day_num))
                    elif alert_type == 'sproutlet':
                        all_channels = await conn.execute(select(Sproutlet.channel_id, Sproutlet.role_id, Sproutlet.auto_delete).filter(Sproutlet.hour==time_now.hour))
                    elif alert_type == 'medics':
                        all_channels = await conn.execute(select(Medics.channel_id, Medics.role_id, Medics.auto_delete))
                    all_channels = all_channels.all()
                    if len(all_channels) == 0:
                        return #await self.send_log('info', alert_type, f"Sent to 0 guilds.\nBot currently in {len(self.bot.guilds):,} guilds.", silent=True)
                random.shuffle(all_channels)
                for channel_id, role_id, auto_delete in all_channels:
                    role_to_mention = None
                    perm_errors = []
                    cur_chan = self.bot.get_channel(channel_id)
                    if cur_chan is None:
                        await self.purge_channel(alert_type=alert_type, channel_id=channel_id)
                        await self.send_log('error', alert_type, f"Deleted {channel_id} due to channel not found.")
                        errors += 1
                        continue
                    if not cur_chan.permissions_for(cur_chan.guild.me).send_messages:
                        perm_errors.append('Send Messages')
                    if not cur_chan.permissions_for(cur_chan.guild.me).view_channel:
                        perm_errors.append('View Channel')
                    if not cur_chan.permissions_for(cur_chan.guild.me).embed_links:
                        perm_errors.append('Embed Links')
                    if len(perm_errors) > 0:
                        errors += 1
                        await self.purge_channel(alert_type=alert_type, channel_id=channel_id)
                        try:
                            await cur_chan.guild.system_channel.send(f"Your {alert_type} channel was deleted from the bot due to missing `{', '.join(perm_errors)}` permission.  Please re-add it with the appropriate setup command.")
                            sent_error = True
                        except:
                            sent_error = False
                        await self.send_log('error', alert_type, f"Deleted {cur_chan.name} (channel_id: {channel_id}) @ {cur_chan.guild.name} (guild_id: {cur_chan.guild.id}) due to missing `{', '.join(perm_errors)}` permission.\n{'Sent error message.' if sent_error else 'Did not send error message.'}")
                        continue
                    if role_id is not None:
                        role_to_mention = cur_chan.guild.get_role(role_id)
                    try:
                        dest = LANGUAGES.get(str(cur_chan.guild.preferred_locale).lower(), 'en')
                        embed_titles = {
                            'cargo': TRANSLATIONS[dest]['cargo_embed_title'],
                            'crate': TRANSLATIONS[dest]['crate_embed_title'],
                            'purification': TRANSLATIONS[dest]['purification_embed_title'],
                            'controller': TRANSLATIONS[dest]['controller_embed_title'],
                            'sproutlet': TRANSLATIONS[dest]['sproutlet_embed_title'],
                            'medics': TRANSLATIONS[dest]['medics_embed_title']
                            }
                        reset_embed = discord.Embed(color=discord.Color.blurple())
                        reset_embed.title = embed_titles.get(alert_type)
                        if alert_type == 'cargo':
                            cargo_timestamp = int(datetime.datetime.timestamp(time_now + datetime.timedelta(minutes=5)))
                            reset_embed.add_field(name='', value=TRANSLATIONS[dest]['cargo_scramble_alert_message'].format(f'<t:{cargo_timestamp}:R>'), inline=False)
                        elif alert_type == 'asian_cargo':
                            cargo_timestamp = int(datetime.datetime.timestamp(time_now + datetime.timedelta(minutes=5)))
                            reset_embed.add_field(name='', value=TRANSLATIONS[dest]['asian_cargo_scramble_alert_message'].format(f'<t:{cargo_timestamp}:R>'), inline=False)
                        elif alert_type == 'crate':
                            crate_timestamp = int(datetime.datetime.timestamp(time_now.replace(minute=0, second=0, microsecond=0)))
                            reset_embed.add_field(name='', value=TRANSLATIONS[dest]['crate_respawn_alert_message'].format(f'<t:{crate_timestamp}:t>'), inline=False)
                            reset_embed.set_footer(text=TRANSLATIONS[dest]['crate_respawn_footer'])
                        elif alert_type == 'purification':
                            reset_embed.add_field(name='', value=TRANSLATIONS[dest]['purification_reset_alert_message'], inline=False)
                        elif alert_type == 'controller':
                            reset_embed.add_field(name='', value=TRANSLATIONS[dest]['controller_reset_alert_message'], inline=False)
                        elif alert_type == 'sproutlet':
                            reset_embed.add_field(name='', value=TRANSLATIONS[dest]['sproutlet_alert_message'], inline=False)
                        elif alert_type == 'medics':
                            medics_timestamp = int(datetime.datetime.timestamp(time_now.replace(minute=0, second=0, microsecond=0)))
                            reset_embed.add_field(name='', value=TRANSLATIONS[dest]['medics_respawn_alert_message'].format(f'<t:{medics_timestamp}:t>'), inline=False)
                            reset_embed.set_footer(text=TRANSLATIONS[dest]['medics_respawn_footer'])
                        if auto_delete:
                            delete_delays = {'cargo': 10800, 'crate': 14400, 'purification': 28800, 'controller': 28800, 'sproutlet': 15600, 'medics': 28800}
                            msg = await cur_chan.send(content=f"{role_to_mention.mention if role_to_mention is not None else ''}", embed=reset_embed)
                            await msg.delete(delay=delete_delays.get(alert_type))
                        else:
                            await cur_chan.send(content=f"{role_to_mention.mention if role_to_mention is not None else ''}", embed=reset_embed)
                        guilds_sent += 1
                    except Exception as e:
                        traceback.print_exception(type(e), e, e.__traceback__)
                        errors += 1
                        try:
                            support_cmd = await self.find_cmd(self.bot, 'support')
                            feedback_cmd = await self.find_cmd(self.bot, 'feedback')
                            await cur_chan.guild.system_channel.send(f"Your {alert_type} alert was not sent due to `{e}`.\nIf this happens multiple times, please contact me on the support server ({support_cmd.mention}) or send a bug report ({feedback_cmd.mention}).")
                            sent_error = True
                        except:
                            sent_error = False
                        await self.send_log('error', alert_type, f"Error with {cur_chan.name} (channel_id: {channel_id}) @ {cur_chan.guild.name} (guild_id: {cur_chan.guild.id}) due to:\n{e}\n{'Sent error message.' if sent_error else 'Did not send error.'}")
                        continue
                end = perf_counter()
                elapsed = end - start
                if elapsed >= 3600:
                    elapsed = f"{(end - start)/3660:.2f} hours"
                elif elapsed >= 60:
                    elapsed = f"{(end - start)/60:.2f} minutes"
                else:
                    elapsed = f"{(end - start):.2f} seconds"
                await self.send_log('info', alert_type, f"Sent to {guilds_sent} guilds.  Errors: {errors}\nBot currently in {len(self.bot.guilds):,} guilds.\nTime taken: {elapsed}")
            except Exception as e:
                err = e
                traceback_str = ''.join(traceback.format_tb(e.__traceback__))
                traceback.print_exception(type(e), e, e.__traceback__)
                await self.send_log('error', alert_type, f"{traceback_str[:2000]}")
                continue
            else:
                break
        else:
            raise err


    @app_commands.command(name='check_timers', description='Returns all running timer jobs.')
    @app_commands.guild_only()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def check_running_timers(self, interaction: discord.Interaction):
        jobs_info = ""
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            jobs_info += f"### {job.name}\nTrigger: {job.trigger}\nNext run: <t:{int(datetime.datetime.timestamp(job.next_run_time))}:R>\n"
        await interaction.response.send_message(f"## Running jobs = {len(jobs)}\n{jobs_info}", delete_after=120, ephemeral=True)


    @app_commands.command(name='next', description='Returns the current UTC time and the next cargo/crate respawn timer.')
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.guild_only()
    async def next_crate_and_cargo_time(self, interaction: discord.Interaction):
        if interaction.guild:
            await interaction.response.defer(ephemeral=True)
            dest = LANGUAGES.get(str(interaction.guild.preferred_locale).lower())
            if dest is None:
                dest = 'en'
            time_now = datetime.datetime.now(tz=utc)
            crate_job = [job for job in self.scheduler.get_jobs() if job.name == "crate_respawn_alert"][0]
            cargo_job = [job for job in self.scheduler.get_jobs() if job.name == "cargo_spawn_alert"][0]
            asian_server_cargo = [job for job in self.scheduler.get_jobs() if job.name == "asian_server_cargo_spawn_alert"][0]
            next_crate_time_timestamp = int(datetime.datetime.timestamp(crate_job.next_run_time))
            next_cargo_time_timestamp = int(datetime.datetime.timestamp(cargo_job.next_run_time + datetime.timedelta(minutes=5)))
            next_asian_cargo_time_timestamp = int(datetime.datetime.timestamp(asian_server_cargo.next_run_time + datetime.timedelta(minutes=5)))
            await interaction.followup.send(content=TRANSLATIONS[dest]['next_respawns_message'].format(
                f"{time_now.hour:02d}",
                f"{time_now.minute:02d}",
                f"<t:{next_crate_time_timestamp}:F>",
                f"<t:{int(next_crate_time_timestamp)}:R>",
                f"<t:{next_cargo_time_timestamp}:F>",
                f"<t:{int(next_cargo_time_timestamp)}:R>",
                f"<t:{next_asian_cargo_time_timestamp}:F>",
                f"<t:{int(next_asian_cargo_time_timestamp)}:R>",), wait=True)
        else:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(TimerCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(TimerCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")