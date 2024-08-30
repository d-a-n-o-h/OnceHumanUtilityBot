import datetime
import random
import sys
import calendar
import unicodedata
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from googletrans import Translator
from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import create_async_engine

from languages import LANGUAGES
from models.channels import (CargoMutes, CargoScrambleChannel, CrateMutes,
                             CrateRespawnChannel, AutoDelete)
from models.command_uses import CommandUses
from models.guild_blacklist import GuildBlacklist

utc = datetime.timezone.utc
config = dotenv_values(".env")

if config["DATABASE_STRING"]:
    engine = create_async_engine(config["DATABASE_STRING"])
else:
    print("Please set the DATABASE_STRING value in the .env file and restart the bot.")
    sys.exit(1)


def me_only(interaction: discord.Interaction) -> bool:
    return interaction.user.id == int(config["MY_USER_ID"])

MY_GUILD_ID = discord.Object(int(config["TESTING_GUILD_ID"]))


class UtilsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()

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
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)   
    async def utility_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with engine.begin() as conn:
            muted_channels = await conn.execute(select(CrateRespawnChannel.channel_id, CrateRespawnChannel.role_id, AutoDelete.crate).join(AutoDelete, AutoDelete.guild_id == CrateRespawnChannel.guild_id).join(CrateMutes).filter(CrateMutes.zero==False))
            muted_channels = muted_channels.all()
        await interaction.edit_original_response(content=f"{len(muted_channels)}: {muted_channels}")
        

    @app_commands.command(name='mute_stats', description='How many guilds have muted an alert separated by time.')
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def mute_stats(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with engine.begin() as conn:
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
        await engine.dispose(close=True)
        msg = await interaction.edit_original_response(content=f"# Total Count\n## Cargo: `{cargo_mutes_count}`/`{total_cargo}` (`{round((cargo_mutes_count/total_cargo)*100, 2)}%`)\n## Crate: `{crate_mutes_count}`/`{total_crate}` (`{round((crate_mutes_count/total_crate)*100, 2)}%`)\n\n### Cargo\n- 12:00: `{cargo_twelve}`\n- 15:00: `{cargo_fifteen}`\n- 18:30: `{cargo_eighteen_thirty}`\n- 22:00: `{cargo_twenty_two}`\n\n### Crate\n- 00:00: `{crate_zero}`\n- 04:00: `{crate_four}`\n- 08:00: `{crate_eight}`\n- 12:00: `{crate_twelve}`\n- 16:00: `{crate_sixteen}`\n- 20:00: `{crate_twenty}`")
        await msg.delete(delay=30)

                
    @app_commands.command(name='stats', description='Stats about the bot.')
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)   
    async def stats(self, interaction: discord.Interaction):
        async with engine.begin() as conn:
            command_usage = await conn.execute(select(CommandUses).order_by(CommandUses.last_used.desc()).filter_by(admin=False).limit(7))
            command_usage = command_usage.fetchall()
        await engine.dispose(close=True)
        stats_embed = discord.Embed(title="Bot Stats", color=discord.Color.gold())
        stats_embed.description = f"Up since: {self.bot.uptime_timestamp}\nLatency: `{round(self.bot.latency * 1000, 1)}ms`\nShards: `{len(self.bot.shards)}`"
        stats_embed.set_thumbnail(url=self.bot.user.avatar.url)
        stats_embed.set_footer(text=f"{len(self.bot.guilds):,} Guilds")
        for cmd in command_usage:
            last_used_timestamp = int(datetime.datetime.timestamp(cmd.last_used))
            stats_embed.add_field(name=cmd.name, value=f"Uses: {cmd.num_uses:,} || Last used: <t:{last_used_timestamp}:R>", inline=False)
        await interaction.response.send_message(embed=stats_embed, delete_after=60)


    @app_commands.command(name='bl_setup', description='Setup the guild_blacklist database.')
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def bl_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guilds_added = 0
        async with engine.begin() as conn:
            for guild in self.bot.guilds:
                cur_strikes = await conn.execute(select(GuildBlacklist.strikes).filter_by(guild_id=guild.id))
                cur_strikes = cur_strikes.scalar()
                if cur_strikes is not None:
                    continue
                insert_stmt = insert(GuildBlacklist).values(guild_id=guild.id)
                update = insert_stmt.on_conflict_do_nothing(constraint='guild_blacklist_unique_guild_id')
                await conn.execute(update)
                guilds_added += 1
        await engine.dispose(close=True)
        msg = await interaction.edit_original_response(content=f"{guilds_added} guilds added.")
        await msg.delete(delay=10)


    @app_commands.command(name='manual_send', description='Manually send out an alert to subscribed channels.')
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def manual_alert_page(self, interaction: discord.Interaction, verify: Literal['no', 'yes']):
        if verify == 'no':
            return await interaction.response.send_message("Manual alert not sent.", ephemeral=True, delete_after=10)
        await interaction.response.defer(ephemeral=True)
        for _ in range(5):
            try:
                guilds_sent = 0
                time_now = datetime.datetime.now(tz=utc)
                print(f"Timer! {time_now}")
                async with engine.begin() as conn:
                    all_channels = await conn.execute(select(CrateRespawnChannel.channel_id, CrateRespawnChannel.role_id))
                    all_channels = all_channels.all()
                await engine.dispose(close=True)
                random.shuffle(all_channels)
                for channel_id, role_id in all_channels:
                    cur_chan = self.bot.get_channel(channel_id)
                    if not cur_chan:
                        async with engine.begin() as conn:
                            await conn.execute(delete(CrateRespawnChannel).filter_by(channel_id=channel_id))
                        await engine.dispose(close=True)
                        continue
                    if cur_chan.guild:
                        role_to_mention = cur_chan.guild.get_role(role_id)
                    else:
                        role_to_mention = None
                    try:
                        dest = LANGUAGES.get(str(cur_chan.guild.preferred_locale).lower())
                        reset_embed = discord.Embed(color=discord.Color.blurple(),title=self.translator.translate("Once Human Gear/Weapon Crates Reset", dest=dest).text)
                        time_now = time_now.replace(minute=0, second=0, microsecond=0)
                        reset_embed.add_field(name='', value=self.translator.translate(f"This is the <t:{int(datetime.datetime.timestamp(time_now))}:t> reset announcement.", dest=dest).text)
                        reset_embed.add_field(name='', value=self.translator.translate(f"This was sent manually due to an error with the automatic alert.", dest=dest).text)
                        reset_embed.set_footer(text=self.translator.translate("Log out to the main menu and log back in to see the reset chests.", dest=dest).text)
                        await cur_chan.send(content=f"{role_to_mention.mention if role_to_mention is not None else ''}", embed=reset_embed)
                        guilds_sent += 1
                    except Exception as e:
                        print(f"({channel_id}) Error: {e}")
                        async with engine.begin() as conn:
                            await conn.execute(delete(CrateRespawnChannel).filter_by(channel_id=channel_id))
                        await engine.dispose(close=True)
                        continue
                print(f"Sent to {guilds_sent} guilds.\nBot currently in {len(self.bot.guilds)} guilds.")
            except Exception as e:
                err = e
                continue
            else:
                break
        else:
            raise err
        msg = await interaction.followup.send(content=f"Sent to {guilds_sent} out of {len(self.bot.guilds)}.", wait=True)
        await msg.delete(delay=10)


    @app_commands.command(name='errors', description='Lists out the channels without permissions.')
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def list_errors(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        send_errors = 0
        view_errors = 0
        channel_set_errors = 0
        all_channels_list = list()
        all_guilds_list = list()
        async with engine.begin() as conn:
            all_channels = await conn.execute(select(CrateRespawnChannel.channel_id))
            all_channels = all_channels.all()
            all_guilds = await conn.execute(select(CrateRespawnChannel.guild_id))
            all_guilds = all_guilds.all()
        await engine.dispose(close=True)
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
                

    @app_commands.command(name='reload', description='Reloads the cogs.')
    @app_commands.describe(extension="The extension to be reloaded.")
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def reload(self, interaction: discord.Interaction, extension: str):
        if "cogs."+extension.lower() in self.bot.initial_extensions:
            try:
                await self.bot.reload_extension("cogs."+extension.lower())
                await interaction.response.send_message(f"Reloaded `{extension.upper()}` extension.", ephemeral=True, delete_after=10)
            except Exception as e:
                await interaction.response.send_message(f"Error reloading `{extension.upper()}` extension: {e}", ephemeral=True)
        else:
            await interaction.response.send_message(f"{self.bot.initial_extensions} || {self.__cog_name__}")


    @app_commands.command(name='reloadall', description='Reloads all the cogs, starts cogs that aren\'t loaded.')
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
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
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
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