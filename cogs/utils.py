import asyncio
import datetime
import os
import sys
import unicodedata
from typing import Literal, Optional

import asqlite
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import ExtensionAlreadyLoaded
from dotenv import dotenv_values
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import create_async_engine

from modals.channels import ReportingChannel


utc = datetime.timezone.utc
config = dotenv_values(".env")
if config["DATABASE_STRING"]:
    engine = create_async_engine(config["DATABASE_STRING"])
elif config["DATABASE"]:
    engine = create_async_engine(f"sqlite+asqlite:///{config['DATABASE']}")
else:
    print("Please set the DATABASE or DATABASE_STRING value in the .env file and restart the bot.")
    sys.exit(1)


def me_only(interaction: discord.Interaction) -> bool:
    return interaction.user.id == int(config["MY_USER_ID"]) # type: ignore

MY_GUILD_ID = discord.Object(int(config["TESTING_GUILD_ID"])) # type: ignore

class UtilsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
    
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            if not interaction.response.is_done():
                return await interaction.response.send_message(f"That command is on cooldown.  Please try again in {round(error.retry_after, 2)} seconds.", ephemeral=True, delete_after=error.retry_after)
            else:
                print(error)
        else:
            if not interaction.response.is_done():
                return await interaction.response.send_message(f"There was an error with your request:\n`{error}`", ephemeral=True, delete_after=60)
            else:
                print(error)

    @app_commands.command(name='utility', description='Utility command for testing.')
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def utility_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("Utility")

    @app_commands.command(name='manual_send', description='Manually send out an alert to subscribed channels.')
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def manual_alert_page(self, interaction: discord.Interaction, verify: Literal['no', 'yes']):
        if verify == 'no':
            return await interaction.response.send_message("Manual alert not sent.")
        await interaction.response.defer(ephemeral=True)
        guilds_sent = 0
        time_now = datetime.datetime.now(tz=utc)
        print(f"Timer! {time_now}")
        reset_embed = discord.Embed(color=discord.Color.dark_gold(),title="Once Human Gear/Weapon Crates Reset")
        time_now = time_now.replace(minute=0, second=0, microsecond=0)
        timestamp_now = datetime.datetime.timestamp(time_now)
        reset_embed.add_field(name='', value=f"This is the <t:{int(timestamp_now)}:t> reset announcement.")
        setup_cmd = await self.find_cmd(self.bot, cmd='setup')
        reset_embed.add_field(name='', value=f"Use {setup_cmd.mention} to change the channel or change/add a role to ping.", inline=False) # type: ignore
        reset_embed.set_footer(text="This alert was sent manually due to an error with the automation.")
        async with engine.begin() as conn:
            all_channels = await conn.execute(select(ReportingChannel.channel_id,ReportingChannel.role_id))
            all_channels = all_channels.all()
        await engine.dispose(close=True)
        for i, (channel_id, role_id) in enumerate(all_channels):
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
            print(f"{i+1}/{len(all_channels)}", channel_id)
            try:
                await cur_chan.send(content=f"{role_to_mention.mention if role_to_mention is not None else ''}", embed=reset_embed)
                await asyncio.sleep(0.1)
                guilds_sent += 1
            except Exception as e:
                print(f"Error: {e}")
                continue
        print(f"Sent to {guilds_sent} out of {len(self.bot.guilds)}.")
        await interaction.followup.send(content=f"Sent to {guilds_sent} out of {len(self.bot.guilds)}.")


    @app_commands.command(name='errors', description='Lists out the channels without permissions.')
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def list_errors(self, interaction: discord.Interaction):
        await interaction.response.defer()
        send_errors = 0
        view_errors = 0
        channel_set_errors = 0
        errors_string = ""
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
        await interaction.response.send_message("Problems found...")
        for guild in self.bot.guilds:
            if guild.id not in all_guilds_list:
                channel_set_errors += 1
                errors_string += f"No channel set | guild\_id: {guild.id} ({self.fix_unicode(guild.name)})\n" # type: ignore
        for channel_id in all_channels_list:
            cur_chan = self.bot.get_channel(channel_id)
            if cur_chan:
                if not cur_chan.permissions_for(cur_chan.guild.me).send_messages:
                    send_errors += 1
                    errors_string += f"Can't send messages in #{cur_chan.name} | guild\_id: {cur_chan.guild.id} ({self.fix_unicode(cur_chan.guild.name)}).\n" # type: ignore
                if not cur_chan.permissions_for(cur_chan.guild.me).view_channel:
                    view_errors += 1
                    errors_string += f"Can't view channel #{cur_chan.name} | guild\_id: `{cur_chan.guild.id}` ({self.fix_unicode(cur_chan.guild.name)}).\n" # type: ignore
        await interaction.followup.send(content=f"Send errors: `{send_errors}`\nView errors: `{view_errors}`\nNo channel set: `{channel_set_errors}`\n")
                

    @app_commands.command(name='reload', description='Reloads the cogs.')
    @app_commands.describe(cog="The cog to be reloaded.")
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def reload(self, interaction: discord.Interaction, cog: str):
        if os.path.exists(f"cogs/{cog.lower()}.py"):
            try:
                await self.bot.reload_extension(f"cogs.{cog.lower()}")
                await interaction.response.send_message(f"Reloaded `{cog.upper()}` cog.", ephemeral=True, delete_after=10)
            except Exception as e:
                await interaction.response.send_message(f"Error reloading `{cog.upper()}` cog.: {e}", ephemeral=True)


    @app_commands.command(name='reloadall', description='Reloads all the cogs, starts cogs that aren\'t loaded.')
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def reloadall(self, interaction: discord.Interaction):
        await interaction.response.defer()
        for subdir, _, files in os.walk("cogs"):
            files = [
                file for file in files if file.endswith(".py") and "template" not in file
            ]
            for file in files:
                if len(subdir.split("cogs\\")) >= 2:
                    try:
                        sub = subdir.split("cogs\\")[1]
                        await self.bot.load_extension(f"cogs.{sub}.{file[:-3]}")
                        await interaction.followup.send(content=f"Loaded `cogs.{sub}.{file[:-3]}` cog.")
                    except ExtensionAlreadyLoaded:
                        sub = subdir.split("cogs\\")[1]
                        await self.bot.reload_extension(f"cogs.{sub}.{file[:-3]}")
                        await interaction.followup.send(content=f"Reloaded `cogs.{sub}.{file[:-3]}` cog.")
                else:
                    try:
                        await self.bot.load_extension(f"{subdir}.{file[:-3]}")
                        await interaction.followup.send(content=f"Loaded `{subdir}.{file[:-3]}` cog.")
                    except ExtensionAlreadyLoaded:
                        await self.bot.reload_extension(f"{subdir}.{file[:-3]}")
                        await interaction.followup.send(content=f"Reloaded `{subdir}.{file[:-3]}` cog.")


    @app_commands.command(name='load', description='Loads the specified cog.')
    @app_commands.describe(cog="The cog to be loaded.")
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def load(self, interaction: discord.Interaction, cog: str):
        try:
            await self.bot.load_extension(f"cogs.{cog}")
            await interaction.response.send_message(f"Loaded `{cog.upper()}` cog.", ephemeral=True, delete_after=10)
        except Exception as e:
            await interaction.response.send_message(f"Error loading `{cog.upper()}` cog.\n{e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilsCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(UtilsCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")