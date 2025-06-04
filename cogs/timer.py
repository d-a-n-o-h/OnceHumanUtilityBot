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
from sqlalchemy import delete, select, update

from languages import LANGUAGES
from models.channels import (AutoDelete, CargoMutes, CargoScrambleChannel,
                             CrateMutes, CrateRespawnChannel, Medics,
                             PremiumMessage)
from models.events import Lunar
from models.languages import GuildLanguage
from models.weekly_resets import Controller, Purification, Sproutlet
from translations import TRANSLATIONS

config = dotenv_values(".env")


def me_only(interaction: discord.Interaction) -> bool:
    return interaction.user.id == int(config["MY_USER_ID"])

MY_GUILD_ID = discord.Object(int(config["TESTING_GUILD_ID"]))
LUNAR_EVENT_LENGTH = 3600


class TimerCog(commands.Cog):
    def __init__(self, bot):
        self.bot: Final[commands.Bot] = bot
        self.scheduler: Final = AsyncIOScheduler(timezone=datetime.timezone.utc)

    def cog_load(self):
        if not self.scheduler.running:
            
            # Crate alerts - every 4 hours
            self.scheduler.add_job(self.generate_alert, 'cron', name='crate_respawn_alert', args=['crate'], coalesce=True, hour='0,4,8,12,16,20', minute=0)

            # Cargo alerts - set times with trigger
            cargo_trigger = OrTrigger([
                CronTrigger(hour='11,14,21', minute=55, timezone=datetime.timezone.utc),
                CronTrigger(hour=18, minute=25, timezone=datetime.timezone.utc)
                ])
            asian_server_cargo_trigger = OrTrigger([
                CronTrigger(hour='10,13,20', minute=55, timezone=datetime.timezone.utc),
                CronTrigger(hour=17, minute=25, timezone=datetime.timezone.utc)
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

            # Lunar event alert - every minute
            self.scheduler.add_job(self.generate_alert, 'cron', name='lunar_alert', args=['lunar'], coalesce=True, second=0)

            # Update the # of servers every 6 minutes
            self.scheduler.add_job(self.update_stats, 'interval', name='update_stats', minutes=6)

            self.scheduler.start()

    def cog_unload(self):
        self.scheduler.remove_all_jobs()
        self.scheduler.shutdown(wait=False)

    async def get_language(self, guild: discord.Guild) -> str:
        async with self.bot.engine.begin() as conn:
            lang = await conn.execute(select(GuildLanguage.lang).filter_by(guild_id=guild.id))
            lang = lang.one_or_none()
        if lang is not None:
            lang = lang.lang
        if lang is None:
            lang = LANGUAGES.get(str(guild.preferred_locale).lower(), 'en')
        return lang

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
        if stats_chan.name == f'🛜 {len(self.bot.guilds):,} Servers':
            pass
        await stats_chan.edit(name=f'🛜 {len(self.bot.guilds):,} Servers')

    async def send_log(self, type: str, alert_type: str, message: str, silent: bool = False) -> discord.Message:
        log_channel: discord.TextChannel = self.bot.get_channel(int(config["LOG_CHAN"]))
        log_embed = discord.Embed(description=message[:-4096])
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
            elif alert_type == 'lunar':
                await conn.execute(delete(Lunar).filter_by(channel_id=channel_id))
        await self.send_log('error', alert_type, f"Deleted {channel_id} due to channel not found.")

    async def generate_alert(self, alert_type: str):
        start = perf_counter()
        for _ in range(5):
            try:
                sku_list = list()
                skus = await self.bot.fetch_skus()
                for sku in skus:
                    if sku.id == 1372073760546488391:
                        sku_list.append(sku)
                ent_list = [ent.guild_id async for ent in self.bot.entitlements(skus=sku_list,exclude_ended=True)]
                guilds_sent = 0
                errors = 0
                time_now = discord.utils.utcnow()
                if alert_type != "lunar":
                    print(f"[{alert_type.upper()}] Timer start: {time_now}")
                async with self.bot.engine.begin() as conn:
                    if alert_type == 'cargo':
                        qry_filter = {11: CargoMutes.twelve==False, 14: CargoMutes.fifteen==False, 18: CargoMutes.eighteen_thirty==False, 21: CargoMutes.twenty_two==False}
                        all_channels = await conn.execute(select(CargoScrambleChannel.channel_id, CargoScrambleChannel.role_id, AutoDelete.cargo).where(CargoScrambleChannel.asian_server == False).join(AutoDelete, AutoDelete.guild_id == CargoScrambleChannel.guild_id).join(CargoMutes).filter(qry_filter.get(time_now.hour)))
                    elif alert_type == 'asian_server_cargo':
                        qry_filter = {11: CargoMutes.twelve==False, 14: CargoMutes.fifteen==False, 18: CargoMutes.eighteen_thirty==False, 21: CargoMutes.twenty_two==False}
                        all_channels = await conn.execute(select(CargoScrambleChannel.channel_id, CargoScrambleChannel.role_id, AutoDelete.cargo).where(CargoScrambleChannel.asian_server == True).join(AutoDelete, AutoDelete.guild_id == CargoScrambleChannel.guild_id).join(CargoMutes).filter(qry_filter.get(time_now.hour)))
                    elif alert_type == 'crate':
                        qry_filter = {0: CrateMutes.zero==False, 4: CrateMutes.four==False, 8: CrateMutes.eight==False, 12: CrateMutes.twelve==False, 16: CrateMutes.sixteen==False, 20: CrateMutes.twenty==False}
                        all_channels = await conn.execute(select(CrateRespawnChannel.channel_id, CrateRespawnChannel.role_id, AutoDelete.crate).join(AutoDelete, AutoDelete.guild_id == CrateRespawnChannel.guild_id).join(CrateMutes).filter(qry_filter.get(time_now.hour)))
                    elif alert_type == 'purification':
                        day_num = discord.utils.utcnow().isoweekday()
                        all_channels = await conn.execute(select(Purification.channel_id, Purification.role_id, Purification.auto_delete).filter(Purification.reset_day==day_num))
                    elif alert_type == 'controller':
                        day_num = discord.utils.utcnow().isoweekday()
                        all_channels = await conn.execute(select(Controller.channel_id, Controller.role_id, Controller.auto_delete).filter(Controller.reset_day==day_num))
                    elif alert_type == 'sproutlet':
                        all_channels = await conn.execute(select(Sproutlet.channel_id, Sproutlet.role_id, Sproutlet.auto_delete).filter(Sproutlet.hour==time_now.hour))
                    elif alert_type == 'medics':
                        all_channels = await conn.execute(select(Medics.channel_id, Medics.role_id, Medics.auto_delete))
                    elif alert_type == 'lunar':
                        all_channels = await conn.execute(select(Lunar.channel_id, Lunar.role_id, Lunar.auto_delete).filter((Lunar.last_alert+LUNAR_EVENT_LENGTH)<=int(time_now.timestamp())))
                    all_channels = all_channels.all()
                    if len(all_channels) == 0:
                        return #await self.send_log('info', alert_type, f"Sent to 0 guilds.\nBot currently in {len(self.bot.guilds):,} guilds.", silent=True)
                random.shuffle(all_channels)
                for channel_id, role_id, auto_delete in all_channels:
                    swapped_alert = False
                    role_to_mention = None
                    perm_errors = []
                    cur_chan = self.bot.get_channel(channel_id)
                    if cur_chan is None:
                        await self.purge_channel(alert_type=alert_type, channel_id=channel_id)
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
                        await self.send_log('error', alert_type, f"Deleted {cur_chan.name} (channel_id: {channel_id}) @ {discord.utils.escape_markdown(cur_chan.guild.name)} (guild_id: {cur_chan.guild.id}) due to missing `{', '.join(perm_errors)}` permission.\n{'Sent error message.' if sent_error else 'Did not send error message.'}")
                        continue
                    if role_id is not None:
                        role_to_mention = cur_chan.guild.get_role(role_id)
                    try:
                        dest = await self.get_language(cur_chan.guild)
                        if cur_chan.guild.id in ent_list:
                            is_premium = True
                        else:
                            is_premium = False
                        embed_titles = {
                            'cargo': TRANSLATIONS[dest]['cargo_embed_title'],
                            'crate': TRANSLATIONS[dest]['crate_embed_title'],
                            'purification': TRANSLATIONS[dest]['purification_embed_title'],
                            'controller': TRANSLATIONS[dest]['controller_embed_title'],
                            'sproutlet': TRANSLATIONS[dest]['sproutlet_embed_title'],
                            'medics': TRANSLATIONS[dest]['medics_embed_title'],
                            'lunar': TRANSLATIONS[dest]['lunar_embed_title'],
                            }
                        reset_embed = discord.Embed(color=discord.Color.blurple())
                        reset_embed.title = embed_titles.get(alert_type)
                        # reset_embed.description="Custom messages are now supported, for more info check out the [📢 Bot Updates](https://discord.com/channels/1264596246644002898/1267474310948327526/1372099827529285672)!\n- Bot Support Server Link: https://discord.mycodeisa.meme"
                        if not is_premium:
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
                            elif alert_type == 'lunar':
                                reset_embed.add_field(name='', value=TRANSLATIONS[dest]['lunar_alert_message'], inline=False)
                        else:
                            use_default = False
                            async with self.bot.engine.begin() as conn:
                                if alert_type == 'asian_cargo':
                                    alert_type = 'cargo'
                                    swapped_alert = True
                                premium_message = await conn.execute(select(PremiumMessage.message).filter_by(guild_id=cur_chan.guild.id,alert_type=alert_type))
                                premium_message = premium_message.all()
                                if len(premium_message) > 0:
                                    premium_message: str = premium_message[0][0]
                                    #await self.send_log('info', alert_type, message=f"{premium_message} / type: {type(premium_message)}")
                                else:
                                    use_default = True
                            if swapped_alert:
                                alert_type = 'asian_cargo'
                            generic_timestamp = int(datetime.datetime.timestamp(time_now))
                            if alert_type == 'cargo':
                                cargo_timestamp = int(datetime.datetime.timestamp(time_now + datetime.timedelta(minutes=5)))
                                reset_embed.add_field(name='', value=premium_message.replace("%time%", f'<t:{cargo_timestamp}:R>'), inline=False)
                                if use_default:
                                    reset_embed.add_field(name='', value=TRANSLATIONS[dest]['cargo_scramble_alert_message'].format(f'<t:{cargo_timestamp}:R>'), inline=False)
                            elif alert_type == 'asian_cargo':
                                cargo_timestamp = int(datetime.datetime.timestamp(time_now + datetime.timedelta(minutes=5)))
                                reset_embed.add_field(name='', value=premium_message.replace("%time%", f'<t:{cargo_timestamp}:R>'), inline=False)                                
                                if use_default:
                                    reset_embed.add_field(name='', value=TRANSLATIONS[dest]['asian_cargo_scramble_alert_message'].format(f'<t:{cargo_timestamp}:R>'), inline=False)
                            elif alert_type == 'crate':
                                crate_timestamp = int(datetime.datetime.timestamp(time_now.replace(minute=0, second=0, microsecond=0)))
                                reset_embed.add_field(name='', value=premium_message.replace("%time%", f'<t:{crate_timestamp}:R>'), inline=False)
                                if use_default:
                                    reset_embed.add_field(name='', value=TRANSLATIONS[dest]['crate_respawn_alert_message'].format(f'<t:{crate_timestamp}:t>'), inline=False)
                                reset_embed.set_footer(text=TRANSLATIONS[dest]['crate_respawn_footer'])
                            elif alert_type == 'purification':
                                reset_embed.add_field(name='', value=premium_message.replace("%time%", f'<t:{generic_timestamp}:R>'), inline=False)
                                if use_default:
                                    reset_embed.add_field(name='', value=TRANSLATIONS[dest]['purification_reset_alert_message'], inline=False)
                            elif alert_type == 'controller':
                                reset_embed.add_field(name='', value=premium_message.replace("%time%", f'<t:{generic_timestamp}:R>'), inline=False)
                                if use_default:
                                    reset_embed.add_field(name='', value=TRANSLATIONS[dest]['controller_reset_alert_message'], inline=False)
                            elif alert_type == 'sproutlet':
                                reset_embed.add_field(name='', value=premium_message.replace("%time%", f'<t:{generic_timestamp}:R>'), inline=False)
                                if use_default:
                                    reset_embed.add_field(name='', value=TRANSLATIONS[dest]['sproutlet_alert_message'], inline=False)
                            elif alert_type == 'medics':
                                medics_timestamp = int(datetime.datetime.timestamp(time_now.replace(minute=0, second=0, microsecond=0)))
                                reset_embed.add_field(name='', value=premium_message.replace("%time%", f'<t:{medics_timestamp}:R>'), inline=False)
                                if use_default:
                                    reset_embed.add_field(name='', value=TRANSLATIONS[dest]['medics_respawn_alert_message'].format(f'<t:{medics_timestamp}:t>'), inline=False)
                                reset_embed.set_footer(text=TRANSLATIONS[dest]['medics_respawn_footer'])
                            elif alert_type == 'lunar':
                                reset_embed.add_field(name='', value=premium_message.replace("%time%", f'<t:{generic_timestamp}:R>'), inline=False)
                                if use_default:
                                    reset_embed.add_field(name='', value=TRANSLATIONS[dest]['lunar_alert_message'], inline=False)

                        if auto_delete:
                            delete_delays = {'cargo': 10800, 'asian_cargo': 10800, 'crate': 14400, 'purification': 28800, 'controller': 28800, 'sproutlet': 15600, 'medics': 28800, 'lunar': 2690}
                            await cur_chan.send(content=f"{role_to_mention.mention if role_to_mention is not None else ''}", embed=reset_embed, delete_after=float(delete_delays.get(alert_type)))
                            guilds_sent += 1
                        else:
                            await cur_chan.send(content=f"{role_to_mention.mention if role_to_mention is not None else ''}", embed=reset_embed)
                            guilds_sent += 1
                        async with self.bot.engine.begin() as conn:
                            update_stmt = update(Lunar).where(Lunar.channel_id==channel_id).values(last_alert=int(time_now.timestamp()))
                            await conn.execute(update_stmt)
                    except Exception as e:
                        traceback.print_exception(type(e), e, e.__traceback__)
                        errors += 1
                        try:
                            support_cmd = await self.find_cmd(self.bot, 'support')
                            feedback_cmd = await self.find_cmd(self.bot, 'feedback')
                            if '503 Service Unavailable' in e:
                                e = "An error with Discord's servers."
                            await cur_chan.guild.system_channel.send(f"Your {alert_type} alert was not sent due to `{e}`.\nIf this happens multiple times, please contact me on the support server ({support_cmd.mention}) or send a bug report ({feedback_cmd.mention}).")
                            sent_error = True
                        except:
                            sent_error = False
                        await self.send_log('error', alert_type, f"Error with {cur_chan.name} (channel_id: {channel_id}) @ {discord.utils.escape_markdown(cur_chan.guild.name)} (guild_id: {cur_chan.guild.id}) due to:\n{e}\n\n{'Sent error message.' if sent_error else 'Did not send error.'}")
                        continue
                end = perf_counter()
                elapsed = end - start
                if elapsed >= 3600:
                    elapsed = f"{(end - start)/3660:.2f} hours"
                elif elapsed >= 60:
                    elapsed = f"{(end - start)/60:.2f} minutes"
                else:
                    elapsed = f"{(end - start):.2f} seconds"
                if guilds_sent >= 5 and alert_type != "lunar":
                    await self.send_log('info', alert_type, f"Sent to {guilds_sent} guilds.  Errors: {errors}\nBot currently in {len(self.bot.guilds):,} guilds.\nTime taken: {elapsed}")
            except Exception as e:
                err = e
                traceback_str = ''.join(traceback.format_tb(e.__traceback__))
                traceback.print_exception(type(e), e, e.__traceback__)
                await self.send_log('error', alert_type, f"{traceback_str[-2000:]}")
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
            dest = await self.get_language(interaction.guild)
            time_now = discord.utils.utcnow()
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