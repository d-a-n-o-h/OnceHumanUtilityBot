import datetime
import random
import unicodedata
from time import perf_counter
from typing import List, Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from googletrans import Translator
from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert

from languages import LANGUAGES
from models.channels import (Medics, CargoMutes, CargoScrambleChannel, CrateMutes,
                             CrateRespawnChannel, AutoDelete)
from models.weekly_resets import Purification, Controller, Sproutlet
from translations import TRANSLATIONS
from models.command_uses import CommandUses
from models.guild_blacklist import GuildBlacklist

utc = datetime.timezone.utc
config = dotenv_values(".env")


def me_only(interaction: discord.Interaction) -> bool:
    return interaction.user.id == int(config["MY_USER_ID"])

MY_GUILD_ID = discord.Object(int(config["TESTING_GUILD_ID"]))


@app_commands.check(me_only)
@app_commands.guilds(MY_GUILD_ID)
@app_commands.guild_only()
class UtilsCog(commands.GroupCog, name='utils'):
    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()

    async def day_to_number(self, day: str) -> int:
        day = day.lower()
        days_to_num = {
            'monday': 1,
            'tuesday': 2,
            'wednesday': 3,
            'thursday': 4,
            'friday': 5,
            'saturday': 6, 
            'sunday': 7,
            'none': None
            }
        return days_to_num[day]

    async def send_log(self, type: str, alert_type: str, message: str, silent: bool = False):
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
        msg = await log_channel.send(embed=log_embed, silent=silent)
        return await msg.delete(delay=7200)

    def fix_unicode(self, str):
        fixed = unicodedata.normalize("NFKD", str).encode("ascii", "ignore").decode()
        return fixed

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


    @app_commands.command(name='utility', description='UTILITY!')
    async def utility_cmd(self, interaction: discord.Interaction, filter: int):
        await interaction.response.defer()
        async with self.bot.engine.begin() as conn:
            muted_guilds = await conn.execute(select(CrateMutes.guild_id))
            muted_guilds = muted_guilds.all()
            muted_guilds = [g_id[0] for g_id in muted_guilds]
            for guild in self.bot.guilds:
                if guild.id not in muted_guilds:
                    crate_insert = insert(CrateMutes).values(guild_id=guild.id,zero=False,four=False,eight=False,twelve=False,sixteen=False,twenty=False)
                    crate_update = crate_insert.on_conflict_do_update(constraint='crate_mutes_unique_guildid', set_={'zero': False, 'four': False, 'eight': False, 'twelve': False, 'sixteen': False, 'twenty': False})
                    await conn.execute(crate_update)
                    await interaction.followup.send(f"Added guild_id {guild.id}.")
            await interaction.followup.send(f"Done.")

        

    @app_commands.command(name='mute_stats', description='How many guilds have muted an alert separated by time.')
    async def mute_stats(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with self.bot.engine.begin() as conn:
            total_cargo = await conn.execute(select(func.count(CargoScrambleChannel.guild_id)))
            total_cargo = total_cargo.scalar_one_or_none()
            total_crate = await conn.execute(select(func.count(CrateRespawnChannel.guild_id)))
            total_crate = total_crate.scalar_one_or_none()
            cargo_mutes_count = await conn.execute(select(func.count(CargoMutes.guild_id)).where(or_(CargoMutes.twelve==True,CargoMutes.fifteen==True,CargoMutes.twenty_two==True,CargoMutes.eighteen_thirty==True)))
            cargo_mutes_count = cargo_mutes_count.scalar_one_or_none()
            crate_mutes_count = await conn.execute(select(func.count(CrateMutes.guild_id)).where(or_(CrateMutes.zero==True,CrateMutes.four==True,CrateMutes.eight==True,CrateMutes.twelve==True,CrateMutes.sixteen==True,CrateMutes.twenty==True)))
            crate_mutes_count = crate_mutes_count.scalar_one_or_none()
            cargo_twelve = await conn.execute(select(func.count(CargoMutes.guild_id)).where(CargoMutes.twelve==True))
            cargo_twelve = cargo_twelve.scalar_one_or_none()
            cargo_fifteen = await conn.execute(select(func.count(CargoMutes.guild_id)).where(CargoMutes.fifteen==True))
            cargo_fifteen = cargo_fifteen.scalar_one_or_none()
            cargo_twenty_two = await conn.execute(select(func.count(CargoMutes.guild_id)).where(CargoMutes.twenty_two==True))
            cargo_twenty_two = cargo_twenty_two.scalar_one_or_none()
            cargo_eighteen_thirty = await conn.execute(select(func.count(CargoMutes.guild_id)).where(CargoMutes.eighteen_thirty==True))
            cargo_eighteen_thirty = cargo_eighteen_thirty.scalar_one_or_none()
            crate_zero = await conn.execute(select(func.count(CrateMutes.guild_id)).where(CrateMutes.zero==True))
            crate_zero = crate_zero.scalar_one_or_none()
            crate_four = await conn.execute(select(func.count(CrateMutes.guild_id)).where(CrateMutes.four==True))
            crate_four = crate_four.scalar_one_or_none()
            crate_eight = await conn.execute(select(func.count(CrateMutes.guild_id)).where(CrateMutes.eight==True))
            crate_eight = crate_eight.scalar_one_or_none()
            crate_twelve = await conn.execute(select(func.count(CrateMutes.guild_id)).where(CrateMutes.twelve==True))
            crate_twelve = crate_twelve.scalar_one_or_none()
            crate_sixteen = await conn.execute(select(func.count(CrateMutes.guild_id)).where(CrateMutes.sixteen==True))
            crate_sixteen = crate_sixteen.scalar_one_or_none()
            crate_twenty = await conn.execute(select(func.count(CrateMutes.guild_id)).where(CrateMutes.twenty==True))
            crate_twenty = crate_twenty.scalar_one_or_none()
        msg = await interaction.edit_original_response(content=f"# Total Count\n## Cargo: `{cargo_mutes_count}`/`{total_cargo}` (`{round((cargo_mutes_count/total_cargo)*100, 2)}%`)\n## Crate: `{crate_mutes_count}`/`{total_crate}` (`{round((crate_mutes_count/total_crate)*100, 2)}%`)\n\n### Cargo\n- 12:00: `{cargo_twelve}`\n- 15:00: `{cargo_fifteen}`\n- 18:30: `{cargo_eighteen_thirty}`\n- 22:00: `{cargo_twenty_two}`\n\n### Crate\n- 00:00: `{crate_zero}`\n- 04:00: `{crate_four}`\n- 08:00: `{crate_eight}`\n- 12:00: `{crate_twelve}`\n- 16:00: `{crate_sixteen}`\n- 20:00: `{crate_twenty}`")
        await msg.delete(delay=30)

                
    @app_commands.command(name='stats', description='Stats about the bot.')
    async def stats(self, interaction: discord.Interaction):
        async with self.bot.engine.begin() as conn:
            command_usage = await conn.execute(select(CommandUses).order_by(CommandUses.last_used.desc()).filter_by(admin=False).limit(7))
            command_usage = command_usage.fetchall()
        stats_embed = discord.Embed(title="Bot Stats", color=discord.Color.gold())
        stats_embed.description = f"Up since: {self.bot.uptime_timestamp}\nLatency: `{round(self.bot.latency * 1000, 1)}ms`\nShards: `{len(self.bot.shards)}`"
        stats_embed.set_thumbnail(url=self.bot.user.avatar.url)
        stats_embed.set_footer(text=f"{len(self.bot.guilds):,} Guilds")
        for cmd in command_usage:
            last_used_timestamp = int(datetime.datetime.timestamp(cmd.last_used))
            stats_embed.add_field(name=cmd.name, value=f"Uses: {cmd.num_uses:,} || Last used: <t:{last_used_timestamp}:R>", inline=False)
        await interaction.response.send_message(embed=stats_embed, delete_after=60)


    @app_commands.command(name='bl_setup', description='Setup the guild_blacklist database.')
    async def bl_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guilds_added = 0
        async with self.bot.engine.begin() as conn:
            for guild in self.bot.guilds:
                cur_strikes = await conn.execute(select(GuildBlacklist.strikes).filter_by(guild_id=guild.id))
                cur_strikes = cur_strikes.scalar()
                if cur_strikes is not None:
                    continue
                insert_stmt = insert(GuildBlacklist).values(guild_id=guild.id)
                update = insert_stmt.on_conflict_do_nothing(constraint='guild_blacklist_unique_guild_id')
                await conn.execute(update)
                guilds_added += 1
        msg = await interaction.edit_original_response(content=f"{guilds_added} guilds added.")
        await msg.delete(delay=10)


    @app_commands.command(name='manual_send', description='Manually send out an alert to subscribed channels.')
    async def manual_alert_page(self, interaction: discord.Interaction, verify: Literal['no', 'yes'], alert_type: Literal['cargo', 'crate', 'purification', 'controller', 'sproutlet', 'medics']):
        if verify == 'no':
            return await interaction.response.send_message("Manual alert not sent.", ephemeral=True, delete_after=10)
        await interaction.response.defer(ephemeral=True)
        start = perf_counter()
        for _ in range(5):
            try:
                guilds_sent = 0
                errors = 0
                time_now = datetime.datetime.now(tz=utc)
                print(f"[{alert_type.upper()} Manual] Timer start: {time_now}")
                async with self.bot.engine.begin() as conn:
                    if alert_type == 'cargo':
                        qry_filter = {11: CargoMutes.twelve==False, 14: CargoMutes.fifteen==False, 18: CargoMutes.eighteen_thirty==False, 21: CargoMutes.twenty_two==False}
                        all_channels = await conn.execute(select(CargoScrambleChannel.channel_id, CargoScrambleChannel.role_id, AutoDelete.cargo).join(AutoDelete, AutoDelete.guild_id == CargoScrambleChannel.guild_id).join(CargoMutes).filter(qry_filter.get(time_now.hour)))
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
                        return await self.send_log('info', alert_type+" - Manual", f"Sent to 0 guilds.\nBot currently in {len(self.bot.guilds):,} guilds.", silent=True)
                random.shuffle(all_channels)
                for channel_id, role_id, auto_delete in all_channels:
                    perm_errors = []
                    role_to_mention = None
                    cur_chan = self.bot.get_channel(channel_id)
                    if cur_chan is None:
                        await self.purge_channel(alert_type=alert_type, channel_id=channel_id)
                        await self.send_log('error', alert_type+" - Manual", f"Deleted {channel_id} due to channel not found.")
                        errors += 1
                        try:
                            await cur_chan.guild.system_channel.send(f"Your {alert_type} channel was deleted from the bot due to the bot not being able to find the channel.  Please re-add it with the appropriate setup command.")
                            continue
                        except:
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
                        await self.send_log('error', alert_type+" - Manual", f"Deleted {cur_chan.name} (channel_id: {channel_id}) @ {cur_chan.guild.name} (guild_id: {cur_chan.guild.id}) due to missing `{', '.join(perm_errors)}` permission.")
                        try:
                            await cur_chan.guild.system_channel.send(f"Your {alert_type} channel was deleted from the bot due to missing `{', '.join(perm_errors)}` permission.  Please re-add it with the appropriate setup command.")
                            print(f"Sent error message for {cur_chan.name} to {cur_chan.guild.name} - {cur_chan.guild.system_channel.name}")
                            continue
                        except:
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
                        reset_embed.add_field(name='', value='-# This alert was sent manually due to an error with the automatic send.')
                        if auto_delete:
                            delete_delays = {'cargo': 10800, 'crate': 14400, 'purification': 28800, 'controller': 28800, 'sproutlet': 15600, 'medics': 28800}
                            msg = await cur_chan.send(content=f"{role_to_mention.mention if role_to_mention is not None else ''}", embed=reset_embed)
                            await msg.delete(delay=delete_delays.get(alert_type))
                        else:
                            await cur_chan.send(content=f"{role_to_mention.mention if role_to_mention is not None else ''}", embed=reset_embed)
                        guilds_sent += 1
                    except Exception as e:
                        await self.purge_channel(alert_type=alert_type, channel_id=channel_id)
                        errors += 1
                        await self.send_log('error', alert_type+" - Manual", f"Deleted {cur_chan.name} (channel_id: {channel_id}) @ {cur_chan.guild.name} (guild_id: {cur_chan.guild.id}) due to:\n{e}")
                        try:
                            await cur_chan.guild.system_channel.send(f"Your {alert_type} channel was deleted from the bot due to `{e}`.  Please re-add it with the appropriate setup command.")
                            continue
                        except:
                            continue
                end = perf_counter()
                elapsed = end - start
                if elapsed >= 3600:
                    elapsed = f"{(end - start)/3660:.2f} hours"
                elif elapsed >= 60:
                    elapsed = f"{(end - start)/60:.2f} minutes"
                else:
                    elapsed = f"{(end - start):.2f} seconds"
                if alert_type == 'sproutlet':
                    silent = True
                else:
                    silent = False
                await self.send_log('info', alert_type+" - Manual", f"Sent to {guilds_sent} guilds.  Errors: {errors}\nBot currently in {len(self.bot.guilds):,} guilds.\nTime taken: {elapsed}", silent=silent)
            except Exception as e:
                err = e
                continue
            else:
                break
        else:
            raise err
        await interaction.edit_original_response(content="Done")


    @app_commands.command(name='errors', description='Lists out the channels without permissions.')
    async def list_errors(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        send_errors = 0
        view_errors = 0
        channel_set_errors = 0
        all_channels_list = list()
        all_guilds_list = list()
        async with self.bot.engine.begin() as conn:
            all_channels = await conn.execute(select(CrateRespawnChannel.channel_id))
            all_channels = all_channels.all()
            all_guilds = await conn.execute(select(CrateRespawnChannel.guild_id))
            all_guilds = all_guilds.all()
        for guild in all_guilds:
            all_guilds_list.append(guild[0])
        for channel in all_channels:
            all_channels_list.append(channel[0])
        for guild in self.bot.guilds:
            if guild.id not in all_guilds_list:
                channel_set_errors += 1
        for channel_id in all_channels_list:
            cur_chan = self.bot.get_channel(channel_id)
            if cur_chan:
                if not cur_chan.permissions_for(cur_chan.guild.me).send_messages:
                    send_errors += 1
                if not cur_chan.permissions_for(cur_chan.guild.me).view_channel:
                    view_errors += 1
        msg = await interaction.followup.send(content=f"Send errors: `{send_errors}`\nView errors: `{view_errors}`\nNo channel set: `{channel_set_errors}`\n", wait=True)
        await msg.delete(delay=60)
        
    
    async def reload_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        return [app_commands.Choice(name=ext.split(".")[1], value=ext.split(".")[1]) for ext in self.bot.initial_extensions if current.lower() in ext.lower()]


    @app_commands.command(name='reload', description='Reloads the cogs.')
    @app_commands.autocomplete(extension=reload_autocomplete)
    @app_commands.describe(extension="The extension to be reloaded.")
    async def reload(self, interaction: discord.Interaction, extension: str):
        if "cogs."+extension.lower() in self.bot.initial_extensions:
            try:
                await self.bot.reload_extension("cogs."+extension.lower())
                await interaction.response.send_message(f"Reloaded `{extension.upper()}` extension.", ephemeral=True, delete_after=7)
            except Exception as e:
                await interaction.response.send_message(f"Error reloading `{extension.upper()}` extension: {e}", ephemeral=True, delete_after=30)
        else:
            cog_list = '\n'.join(sorted([f"- {cog.split('.')[1]}" for cog in self.bot.initial_extensions]))
            await interaction.response.send_message(f"`{extension}` cog not found!\nLoaded cogs:\n{cog_list}", ephemeral=True, delete_after=30)


    @app_commands.command(name='reloadall', description='Reloads all the cogs, starts cogs that aren\'t loaded.')
    async def reloadall(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        successful_reload = []
        for extension in self.bot.initial_extensions:
            try:
                await self.bot.reload_extension(extension)
                successful_reload.append(extension.upper()[5:])
            except Exception as e:
                await interaction.followup.send(content=f"Error reloading `{extension.upper()[5:]}` extension: {e}")
                return print(f"Failed to load extension {extension.upper()[5:]}.\n{e}")
        msg = await interaction.followup.send(content=f"Reloaded: `{', '.join(successful_reload)}` extensions.", wait=True)
        await msg.delete(delay=15)
        


    @app_commands.command(name='load', description='Loads the specified extension.')
    @app_commands.describe(extension="The extension to be loaded.")
    async def load(self, interaction: discord.Interaction, extension: str):
        try:
            await self.bot.load_extension(f"cogs.{extension}")
            await interaction.response.send_message(f"Loaded `{extension.upper()}` extension.", ephemeral=True, delete_after=10)
        except Exception as e:
            await interaction.response.send_message(f"Error loading `{extension.upper()}` extension.\n{e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilsCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(UtilsCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")