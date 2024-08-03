import datetime
import random
import sys
import unicodedata
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from googletrans import Translator  # type: ignore
from sqlalchemy import delete, select  # type: ignore
from sqlalchemy.dialects.postgresql import insert  # type: ignore
from sqlalchemy.ext.asyncio import create_async_engine  # type: ignore

from languages import LANGUAGES
from modals.channels import ReportingChannel
from modals.command_uses import CommandUses
from modals.guild_blacklist import GuildBlacklist

utc = datetime.timezone.utc
config = dotenv_values(".env")

if config["DATABASE_STRING"]:
    engine = create_async_engine(config["DATABASE_STRING"])
else:
    print("Please set the DATABASE_STRING value in the .env file and restart the bot.")
    sys.exit(1)


def me_only(interaction: discord.Interaction) -> bool:
    return interaction.user.id == int(config["MY_USER_ID"]) # type: ignore

MY_GUILD_ID = discord.Object(int(config["TESTING_GUILD_ID"])) # type: ignore

class ReportBtn(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=5)
        self.bot = bot

    @discord.ui.button(label='Report Inaccurate', style=discord.ButtonStyle.danger)
    async def report_timer_inaccurtate_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        time_now = datetime.datetime.now(tz=utc)
        time_now = time_now.replace(minute=0, second=0, microsecond=0)
        timestamp_now = datetime.datetime.timestamp(time_now)
        await interaction.response.defer(ephemeral=True)
        alert_channel = self.bot.get_channel(1268194573595836436) # type: ignore
        await interaction.followup.send(content="Thanks for the report!", ephemeral=True, wait=True)
        await alert_channel.send(f"Reported inaccurate timer @ <t:{int(timestamp_now)}:t>:\nGuild ID: {interaction.guild_id}\nUser ID: {interaction.user.id}")
        button.disabled = True
        button.label = "Report Received"
        button.style = discord.ButtonStyle.success
        await interaction.edit_original_response(view=self)

    async def interaction_check(self, interaction: discord.Interaction[discord.Client]) -> bool:
        if isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator == True:
            return True
        else:
            await interaction.response.send_message("Sorry, only admins can push that button.", ephemeral=True, delete_after=20)
            return False
        
    async def on_timeout(self) -> None:
        for child in self.children:
            if type(child) == discord.ui.Button:
                child.disabled = True
        
        return await super().on_timeout()

     

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
            for child in cmd_group.options:  # type: ignore
                if child.name.lower() == cmd.lower():
                    return child

                
    @app_commands.command(name='utility', description='UTILITY!')
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)   
    async def utility_command(self, interaction: discord.Interaction, string: str):
        dest = LANGUAGES.get(str(interaction.guild_locale).lower())
        time_now = datetime.datetime.now(tz=utc)
        reset_embed = discord.Embed(color=discord.Color.blurple(),title=self.translator.translate("Once Human Gear/Weapon Crates Reset", dest=dest).text)
        time_now = time_now.replace(minute=0, second=0, microsecond=0)
        timestamp_now = f"<t:{int(datetime.datetime.timestamp(time_now))}:t>"
        reset_embed.add_field(name='', value=self.translator.translate(f"This is the <t:{int(datetime.datetime.timestamp(time_now))}:t> reset announcement.", dest=dest).text)
        reset_embed.set_footer(text=self.translator.translate("Log out to the main menu and log back in to see the reset chests.", dest=dest).text)
        await interaction.response.send_message(embed=reset_embed)

                
    @app_commands.command(name='stats', description='Stats about the bot.')
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)   
    async def stats(self, interaction: discord.Interaction):
        async with engine.begin() as conn:
            command_usage = await conn.execute(select(CommandUses).order_by(CommandUses.last_used.desc()).filter_by(admin=False))
            command_usage = command_usage.fetchall()
        stats_embed = discord.Embed(title="Bot Stats", color=discord.Color.gold())
        stats_embed.description = f"Up since: {self.bot.uptime_timestamp}"
        stats_embed.set_thumbnail(url=self.bot.user.avatar.url)
        stats_embed.set_footer(text=f"{len(self.bot.guilds):,} Guilds")
        for cmd in command_usage:
            last_used_timestamp = int(datetime.datetime.timestamp(cmd.last_used))
            stats_embed.add_field(name=cmd.name, value=f"Uses: {cmd.num_uses:,} || Last used: <t:{last_used_timestamp}:R>", inline=False)
        await interaction.response.send_message(embed=stats_embed, delete_after=120)


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
                    all_channels = await conn.execute(select(ReportingChannel.channel_id, ReportingChannel.role_id))
                    all_channels = all_channels.all()
                await engine.dispose(close=True)
                random.shuffle(all_channels)
                for channel_id, role_id in all_channels:
                    cur_chan = self.bot.get_channel(channel_id)
                    if not cur_chan:
                        async with engine.begin() as conn:
                            await conn.execute(delete(ReportingChannel).filter_by(channel_id=channel_id))
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
                            await conn.execute(delete(ReportingChannel).filter_by(channel_id=channel_id))
                        await engine.dispose(close=True)
                        continue
                print(f"Sent to {guilds_sent} guilds.\nBot currently in {len(self.bot.guilds)} guilds.")
            except Exception as e:
                err = e
                continue
            else:
                break
        else:
            raise err # type: ignore
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
            all_channels = await conn.execute(select(ReportingChannel.channel_id))
            all_channels = all_channels.all()
            all_guilds = await conn.execute(select(ReportingChannel.guild_id))
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