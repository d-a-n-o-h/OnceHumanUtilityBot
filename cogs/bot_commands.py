import asyncio
import datetime
import sys
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from sqlalchemy import delete, select # type: ignore
from sqlalchemy.dialects.postgresql import insert # type: ignore
from sqlalchemy.ext.asyncio import create_async_engine # type: ignore

from modals.channels import ReportingChannel

utc = datetime.timezone.utc
config = dotenv_values(".env")

if config["DATABASE_STRING"]:
    engine = create_async_engine(config["DATABASE_STRING"])
else:
    print("Please set the DATABASE_STRING value in the .env file and restart the bot.")
    sys.exit(1)

class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
                msg = await interaction.followup.send(content=f"That command is on cooldown.  Please try again in {round(error.retry_after, 2)} seconds.", wait=True)
                await asyncio.sleep(error.retry_after)
                await msg.delete()
        else:
            if not interaction.response.is_done():
                return await interaction.response.send_message(f"There was an error with your request:\n`{error}`", ephemeral=True, delete_after=60)
            else:
                print(error)
                msg = await interaction.followup.send(content=f"There was an error with your request:\n`{error}`", wait=True)
                await asyncio.sleep(60)
                await msg.delete()


    @app_commands.command(name='test_alert', description='Sends a test alert to your channel.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def test_alert_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with engine.begin() as conn:
            this_guild = await conn.execute(select(ReportingChannel.channel_id,ReportingChannel.role_id).filter_by(guild_id=interaction.guild_id))
            this_guild = this_guild.one_or_none()
        await engine.dispose(close=True)
        if not this_guild:
            msg = await interaction.followup.send(content="No channel set!", wait=True)
            return
        (chan_id, role_id) = this_guild
        chan = interaction.guild.get_channel(chan_id) # type: ignore
        if chan is None:
            await interaction.followup.send(content="No channel assigned.", wait=True)
            return
        role = interaction.guild.get_role(role_id) # type: ignore
        test_embed = discord.Embed(color=discord.Color.blurple(),title="Test Alert")
        setup_cmd = await self.find_cmd(self.bot, cmd='setup')
        test_embed.add_field(name='', value=f"Use {setup_cmd.mention} to change the channel or change/add a role to ping.", inline=False) # type: ignore
        try:
            await chan.send(content=f"{role.mention if role else ''}", embed=test_embed) # type: ignore
        except Exception as e:
            return await interaction.followup.send(content=f"There was an error trying to send the test to the {chan.mention} channel.  Please verify the bot **user** has permissions to view the channel and send messages there and try again.\n{e}")
        await interaction.followup.send(content="Sent test embed to your channel.", wait=True)
    
    @app_commands.command(name='check', description='Shows which channel/role the bot will send alerts to.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def check_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with engine.begin() as conn:
            guild_data = await conn.execute(select(ReportingChannel.channel_id,ReportingChannel.role_id).filter_by(guild_id=interaction.guild_id))
            guild_data = guild_data.one_or_none()
        await engine.dispose(close=True)
        if guild_data:
            if guild_data[1]:
                role = interaction.guild.get_role(int(guild_data[1])) # type: ignore
            else:
                role = None
            channel = interaction.guild.get_channel(int(guild_data[0])) # type: ignore
            await interaction.followup.send(content=f"Alerts go to {channel.mention if channel else '`None`'}.\nRole notified is {role.mention if role else '`None`'}.", wait=True)
            return
        else:
            setup_cmd = await self.find_cmd(self.bot, cmd="setup")
            await interaction.followup.send(content=f"You have not {setup_cmd.mention} your guild yet.", wait=True) # type: ignore
            return
        
    
    @app_commands.command(name='remove_data', description='Remove your guild and channel ID from the database.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 3600, key=lambda i: (i.guild_id, i.user.id))
    async def remove_data(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        async with engine.begin() as conn:
            await conn.execute(delete(ReportingChannel).filter_by(guild_id=interaction.guild_id))
        await engine.dispose(close=True)
        return await interaction.followup.send(content="Your guild ID and channel ID have been removed from the database.\n## Your guild will no longer get alerts.")
        

    @app_commands.command(name='setup', description='Basic setup command for the bot.')
    @app_commands.describe(output_channel="The text channel you want notifications in.")
    @app_commands.describe(role_to_mention="The role you want mentioned in the alert. Blank = None")
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    async def output_setup(self, interaction: discord.Interaction, output_channel: discord.TextChannel, role_to_mention: Optional[discord.Role] = None):
        await interaction.response.defer(ephemeral=True)
        if not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel:
            return await interaction.followup.send(content=f"The bot is not able to send messages in the channel you have chosen, {output_channel.mention}.\nPlease edit the channel settings to allow the bot user or role to send messages there.\nIf you need assistance, please join the support server: https://discord.mycodeisa.meme.", suppress_embeds=True)
        if role_to_mention:
            role_id = role_to_mention.id
        else:
            role_id = None
        async with engine.begin() as conn:
            insert_stmt = insert(ReportingChannel).values(guild_id=interaction.guild_id,channel_id=output_channel.id,role_id=role_id)
            update = insert_stmt.on_conflict_do_update(constraint='channels_unique_guildid', set_={'role_id': role_id})
            await conn.execute(update)
        await engine.dispose(close=True)
        await output_channel.send(f"{interaction.user.mention}, this channel is where respawn alerts will be sent!")
        return await interaction.followup.send(content=f"Your output channel has been set to {output_channel.mention}!\nThe role that will be mentioned is {role_to_mention.mention if role_to_mention else '`None`'}.\nIf you do not get an alert when you expect it, please join the support server and let me know.  https://discord.mycodeisa.meme", suppress_embeds=True)
        


async def setup(bot: commands.Bot):
    await bot.add_cog(CommandsCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(CommandsCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")