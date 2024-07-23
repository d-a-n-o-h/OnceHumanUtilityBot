import datetime
import sys
from typing import Optional

import asqlite
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values

utc = datetime.timezone.utc
config = dotenv_values(".env")
if config["DATABASE"]:
    db_name = config["DATABASE"]
else:
    print("Please set the DATABASE value in the .env file and restart the bot.")
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
            if not interaction.response.is_done():
                return await interaction.response.send_message(f"There was an error with your request:\n`{error}`", ephemeral=True, delete_after=60)


    @app_commands.command(name='test_alert', description='Sends a test alert to your channel.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 900, key=lambda i: (i.guild_id, i.user.id))
    async def utility_command(self, interaction: discord.Interaction):
        async with asqlite.connect(db_name) as conn:
            async with conn.cursor() as cursor:
                data = {"guild_id": interaction.guild_id}
                this_guild = await cursor.execute("SELECT channel_id, role_id FROM channels WHERE guild_id=:guild_id;", data)
                chan_id, role_id = await this_guild.fetchone()
        chan = interaction.guild.get_channel(chan_id) # type: ignore
        role = interaction.guild.get_role(role_id) # type: ignore
        test_embed = discord.Embed(color=discord.Color.blurple(),title="Test Alert")
        setup_cmd = await self.find_cmd(self.bot, cmd='setup')
        test_embed.add_field(name='', value=f"Use {setup_cmd.mention} to change the channel or change/add a role to ping.", inline=False) # type: ignore
        await chan.send(content=f"{role.mention if role else ''}", embed=test_embed) # type: ignore
        return await interaction.response.send_message("Sent test embed to your channel.", ephemeral=True, delete_after=10)

    
    @app_commands.command(name='check', description='Shows which channel/role the bot will send alerts to.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def check_info(self, interaction: discord.Interaction):
        async with asqlite.connect(db_name) as conn:
            async with conn.cursor() as cursor:
                data = {"guild_id": interaction.guild_id}
                guild_data = await cursor.execute("SELECT channel_id, role_id FROM channels WHERE guild_id=:guild_id;", data)
                guild_data = await guild_data.fetchone()
        if guild_data:
            if guild_data[1]:
                role = interaction.guild.get_role(int(guild_data[1])) # type: ignore
            else:
                role = None
            channel = interaction.guild.get_channel(int(guild_data[0])) # type: ignore
            return await interaction.response.send_message(f"Alerts go to {channel.mention if channel else '`None`'}.\nRole notified is {role.mention if role else '`None`'}.", silent=True, ephemeral=True, delete_after=60)
        else:
            setup_cmd = await self.find_cmd(self.bot, cmd="setup")
            return await interaction.response.send_message(f"You have not {setup_cmd.mention} your guild yet.", ephemeral=True, delete_after=10) # type: ignore
        
    
    @app_commands.command(name='remove_data', description='Remove your guild and channel ID from the database.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 3600, key=lambda i: (i.guild_id, i.user.id))
    async def remove_data(self, interaction: discord.Interaction):
        async with asqlite.connect(db_name) as conn:
            async with conn.cursor() as cursor:
                data = {"guild_id": interaction.guild_id}
                await cursor.execute("DELETE FROM channels WHERE guild_id=:guild_id;", data)
                await conn.commit()
        return await interaction.response.send_message("Your guild ID and channel ID have been removed from the database.\n## Your guild will no longer get alerts.")
        

    @app_commands.command(name='setup', description='Basic setup command for the bot.')
    @app_commands.describe(output_channel="The text channel you want notifications in.")
    @app_commands.describe(role_to_mention="The role you want mentioned in the alert. Blank = None")
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.has_permissions(administrator=True)
    async def output_setup(self, interaction: discord.Interaction, output_channel: discord.TextChannel, role_to_mention: Optional[discord.Role] = None):
        if not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel:
            return await interaction.response.send_message(f"The bot is not able to send messages in the channel you have chosen, {output_channel.mention}.\nPlease edit the channel settings to allow the bot user or role to send messages there.\nIf you need assistance, please join the support server: https://discord.mycodeisa.meme.", ephemeral=True, delete_after=300, suppress_embeds=True)
        async with asqlite.connect(db_name) as conn:
            async with conn.cursor() as cursor:
                if role_to_mention is not None:
                    data = {
                        "guild_id": interaction.guild_id,
                        "channel_id": output_channel.id,
                        "role_id": role_to_mention.id}
                elif role_to_mention is None:
                    data = {
                        "guild_id": interaction.guild_id,
                        "channel_id": output_channel.id,
                        "role_id": None}
                await cursor.execute("INSERT OR IGNORE INTO channels (guild_id,channel_id,role_id) VALUES (:guild_id, :channel_id, :role_id);", data)
                await conn.commit()
                await cursor.execute("UPDATE channels SET channel_id=:channel_id, role_id=:role_id WHERE guild_id=:guild_id;", data)
                await conn.commit()
        await output_channel.send(f"{interaction.user.mention}, this channel is where respawn alerts will be sent!")
        return await interaction.response.send_message(f"Your output channel has been set to {output_channel.mention}!\nThe role that will be mentioned is {role_to_mention.mention if role_to_mention else '`None`'}.\nIf you do not get an alert when you expect it, please join the support server and let me know.  https://discord.mycodeisa.meme", ephemeral=True, delete_after=30, suppress_embeds=True)
        


async def setup(bot: commands.Bot):
    await bot.add_cog(CommandsCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(CommandsCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")