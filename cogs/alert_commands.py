import sys
import calendar
from typing import Final, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import create_async_engine

from languages import LANGUAGES
from models.channels import (CargoMutes, CargoScrambleChannel, CrateMutes,
                             CrateRespawnChannel)
from models.weekly_resets import Controller, Purification
from translations import TRANSLATIONS

config = dotenv_values(".env")
if config["DATABASE_STRING"]:
    engine: Final = create_async_engine(config["DATABASE_STRING"])
else:
    print("Please set the DATABASE_STRING value in the .env file and restart the bot.")
    sys.exit(1)


class PurificationSelect(discord.ui.Select):
    def __init__(self):
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        options = []
        options.append(discord.SelectOption(label='None', value='None', default=False))
        for i, day in enumerate(days):
            day_opt = discord.SelectOption(label=day, value=i, default=False)
            options.append(day_opt)
        super().__init__(placeholder="Pick the day your server purification resets.", max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if len(self.values) == 1 and self.values[0] == "None":
            async with engine.begin() as conn:
                insert_stmt = insert(Purification).values(guild_id=interaction.guild_id,reset_day=None)
                update_stmt = insert_stmt.on_conflict_do_update(constraint='purification_reset_day_unique_guildid', set_={'reset_day': None})
                await conn.execute(update_stmt)
            await engine.dispose(close=True)
            return await interaction.response.send_message("Purification reset day set to `None`.", delete_after=60, ephemeral=True)
        else:
            async with engine.begin() as conn:
                insert_stmt = insert(Purification).values(guild_id=interaction.guild_id,reset_day=int(self.values[0])-1)
                update_stmt = insert_stmt.on_conflict_do_update(constraint='purification_reset_day_unique_guildid', set_={'reset_day': int(self.values[0])-1})
                await conn.execute(update_stmt)
            await engine.dispose(close=True)
        return await interaction.response.send_message(f"Purification reset day set to `{calendar.day_name[int(self.values[0])-1]}`", delete_after=20, ephemeral=True)

class PurificationView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(PurificationSelect())


class ControllerSelect(discord.ui.Select):
    def __init__(self):
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        options = []
        options.append(discord.SelectOption(label='None', value='None', default=False))
        for i, day in enumerate(days):
            day_opt = discord.SelectOption(label=day, value=i, default=False)
            options.append(day_opt)
        super().__init__(placeholder="Pick the day your server controllers resets.", max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if len(self.values) == 1 and self.values[0] == "None":
            async with engine.begin() as conn:
                insert_stmt = insert(Controller).values(guild_id=interaction.guild_id,reset_day=None)
                update_stmt = insert_stmt.on_conflict_do_update(constraint='controller_reset_day_unique_guildid', set_={'reset_day': None})
                await conn.execute(update_stmt)
            await engine.dispose(close=True)
            return await interaction.response.send_message("Controller reset day set to `None`.", delete_after=60, ephemeral=True)
        else:
            async with engine.begin() as conn:
                insert_stmt = insert(Controller).values(guild_id=interaction.guild_id,reset_day=int(self.values[0])-1)
                update_stmt = insert_stmt.on_conflict_do_update(constraint='controller_reset_day_unique_guildid', set_={'reset_day': int(self.values[0])-1})
                await conn.execute(update_stmt)
            await engine.dispose(close=True)
        return await interaction.response.send_message(f"Controller reset day set to `{calendar.day_name[int(self.values[0])-1]}`", delete_after=20, ephemeral=True)


class ControllerView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(ControllerSelect())


class AlertCog(commands.Cog):
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
            for child in cmd_group.options:
                if child.name.lower() == cmd.lower():
                    return child 

    @app_commands.command(name='test_alert', description='Sends a test alert to your channel.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild_id, i.user.id))
    async def test_alert_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        alert_success = list()
        dest = LANGUAGES.get(str(interaction.guild_locale).lower())
        if dest is None:
            dest = 'en'
        async with engine.begin() as conn:
            crate_data = await conn.execute(select(CrateRespawnChannel.channel_id,CrateRespawnChannel.role_id).filter_by(guild_id=interaction.guild_id))
            crate_data = crate_data.one_or_none()
            cargo_data = await conn.execute(select(CargoScrambleChannel.channel_id,CargoScrambleChannel.role_id).filter_by(guild_id=interaction.guild_id))
            cargo_data = cargo_data.one_or_none()
        await engine.dispose(close=True)
        if not crate_data and not cargo_data:
            return await interaction.followup.send(content=TRANSLATIONS[dest]['no_channels_set_alert'], wait=True, ephemeral=True)
        else:
            if crate_data:
                crate_cmd = await self.find_cmd(self.bot, cmd='crate_setup')
                (channel_id, role_id) = crate_data
                output_channel: discord.TextChannel = self.bot.get_channel(channel_id)
                if output_channel is None:
                    msg = await interaction.followup.send(content=f"Crate Respawn output channel not found.  Deleted from the database.", wait=True, ephemeral=True)
                    async with engine.begin() as conn:
                        await conn.execute(delete(CrateRespawnChannel).filter_by(guild_id=interaction.guild_id))
                    await engine.dispose(close=True)
                    await msg.delete(delay=60)
                    return
                role: discord.Role = interaction.guild.get_role(role_id)
                if output_channel and (not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel or not output_channel.permissions_for(output_channel.guild.me).embed_links):
                    await interaction.followup.send(content=TRANSLATIONS[dest]['crate_channel_alert_error'].format(crate_cmd.mention), ephemeral=True)
                else:
                    crate_embed = discord.Embed(color=discord.Color.blurple(),title=TRANSLATIONS[dest]['test_crate_embed_title'])
                    crate_embed.add_field(name='', value=TRANSLATIONS[dest]['crate_cmd_notify'].format(crate_cmd.mention), inline=False)
                    await output_channel.send(content=f"{role.mention if role else ''}", embed=crate_embed)
                    alert_success.append("Crate Respawn")
            if cargo_data:
                cargo_cmd = await self.find_cmd(self.bot, cmd='cargo_setup')
                (channel_id, role_id) = cargo_data
                output_channel: discord.TextChannel = self.bot.get_channel(channel_id)
                if output_channel is None:
                    msg = await interaction.followup.send(content=f"Cargo Scramble output channel not found.  Deleted from the database.", wait=True, ephemeral=True)
                    async with engine.begin() as conn:
                        await conn.execute(delete(CargoScrambleChannel).filter_by(guild_id=interaction.guild_id))
                    await engine.dispose(close=True)
                    await msg.delete(delay=60)
                    return
                role: discord.Role = interaction.guild.get_role(role_id)
                if output_channel and (not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel):
                    await interaction.followup.send(content=TRANSLATIONS[dest]['cargo_channel_alert_error'].format(cargo_cmd.mention), ephemeral=True)
                else:
                    cargo_embed = discord.Embed(color=discord.Color.blurple(),title=TRANSLATIONS[dest]['test_cargo_embed_title'])
                    cargo_embed.add_field(name='', value=TRANSLATIONS[dest]['cargo_cmd_notify'].format(cargo_cmd.mention), inline=False)
                    await output_channel.send(content=f"{role.mention if role else ''}", embed=cargo_embed)
                    alert_success.append("Cargo Spawn")
        await interaction.followup.send(content=TRANSLATIONS[dest]['test_alert_success'].format(', '.join(alert_success), 's' if cargo_data is not None and crate_data is not None else ''), wait=True, ephemeral=True)


    # @app_commands.command(name='purification_reset', description='Set the day your server purification limit resets.')
    # @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    # @app_commands.default_permissions(administrator=True)
    # @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    # async def purification_reset_alerts(self, interaction: discord.Interaction):
    #     view = PurificationView()
    #     return await interaction.response.send_message(content="", view=view, ephemeral=True, delete_after=120)
    

    # @app_commands.command(name='controller_reset', description='Set the day your server controller limit resets.')
    # @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    # @app_commands.default_permissions(administrator=True)
    # @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    # async def controller_reset_alerts(self, interaction: discord.Interaction):
    #     view = ControllerView()
    #     return await interaction.response.send_message(content="", view=view, ephemeral=True, delete_after=120)


    @app_commands.command(name='remove_data', description='Remove your guild and channel ID from the database.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 3600, key=lambda i: (i.guild_id, i.user.id))
    async def remove_data(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        dest = LANGUAGES.get(str(interaction.guild_locale).lower())
        if dest is None:
            dest = 'en'
        async with engine.begin() as conn:
            await conn.execute(delete(CrateRespawnChannel).filter_by(guild_id=interaction.guild_id))
            await conn.execute(delete(CargoScrambleChannel).filter_by(guild_id=interaction.guild_id))
            await conn.execute(delete(CrateMutes).filter_by(guild_id=interaction.guild_id))
            await conn.execute(delete(CargoMutes).filter_by(guild_id=interaction.guild_id))
        await engine.dispose(close=True)
        return await interaction.followup.send(content=TRANSLATIONS[dest]['remove_data_success'])
        

async def setup(bot: commands.Bot):
    await bot.add_cog(AlertCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(AlertCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")