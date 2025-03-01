from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from sqlalchemy import delete, select

from languages import LANGUAGES
from models.channels import (AutoDelete, CargoMutes, CargoScrambleChannel,
                             CrateMutes, CrateRespawnChannel, Medics)
from models.languages import GuildLanguage
from models.weekly_resets import Controller, Purification, Sproutlet
from translations import TRANSLATIONS

config = dotenv_values(".env")


class AlertCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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


    @app_commands.command(name='test_alert', description='Sends a test alert to your channel.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild_id, i.user.id))
    async def test_alert_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        alert_success = list()
        dest = await self.get_language(interaction.guild)
        async with self.bot.engine.begin() as conn:
            crate_data = await conn.execute(select(CrateRespawnChannel.channel_id, CrateRespawnChannel.role_id).filter_by(guild_id=interaction.guild_id))
            crate_data = crate_data.one_or_none()
            cargo_data = await conn.execute(select(CargoScrambleChannel.channel_id, CargoScrambleChannel.role_id).filter_by(guild_id=interaction.guild_id))
            cargo_data = cargo_data.one_or_none()
        if not crate_data and not cargo_data:
            return await interaction.followup.send(content=TRANSLATIONS[dest]['no_channels_set_alert'], wait=True, ephemeral=True)
        else:
            if crate_data:
                crate_cmd = await self.find_cmd(self.bot, cmd='setup', group='crate')
                (channel_id, role_id) = crate_data
                output_channel: discord.TextChannel = self.bot.get_channel(channel_id)
                if output_channel is None:
                    msg = await interaction.followup.send(content=f"Crate Respawn output channel not found.  Deleted from the database.", wait=True, ephemeral=True)
                    async with self.bot.engine.begin() as conn:
                        await conn.execute(delete(CrateRespawnChannel).filter_by(guild_id=interaction.guild_id))
                    await msg.delete(delay=60)
                    return
                role: discord.Role = interaction.guild.get_role(role_id)
                if output_channel and (not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel or not output_channel.permissions_for(output_channel.guild.me).embed_links):
                    await interaction.followup.send(content=TRANSLATIONS[dest]['crate_channel_alert_error'].format(crate_cmd.mention), ephemeral=True)
                else:
                    crate_embed = discord.Embed(color=discord.Color.blurple(),title=TRANSLATIONS[dest]['test_crate_embed_title'])
                    crate_embed.add_field(name='', value=TRANSLATIONS[dest]['crate_cmd_notify'].format(crate_cmd.mention), inline=False)
                    msg = await output_channel.send(content=f"{role.mention if role else ''}", embed=crate_embed)
                    alert_success.append("Crate Respawn")
                    await msg.delete(delay=60)
            if cargo_data:
                cargo_cmd = await self.find_cmd(self.bot, cmd='setup', group='cargo')
                (channel_id, role_id) = cargo_data
                output_channel: discord.TextChannel = self.bot.get_channel(channel_id)
                if output_channel is None:
                    msg = await interaction.followup.send(content=f"Cargo Scramble output channel not found.  Deleted from the database.", wait=True, ephemeral=True)
                    async with self.bot.engine.begin() as conn:
                        await conn.execute(delete(CargoScrambleChannel).filter_by(guild_id=interaction.guild_id))
                    await msg.delete(delay=60)
                    return
                role: discord.Role = interaction.guild.get_role(role_id)
                if output_channel and (not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel):
                    await interaction.followup.send(content=TRANSLATIONS[dest]['cargo_channel_alert_error'].format(cargo_cmd.mention), ephemeral=True)
                else:
                    cargo_embed = discord.Embed(color=discord.Color.blurple(),title=TRANSLATIONS[dest]['test_cargo_embed_title'])
                    cargo_embed.add_field(name='', value=TRANSLATIONS[dest]['cargo_cmd_notify'].format(cargo_cmd.mention), inline=False)
                    msg = await output_channel.send(content=f"{role.mention if role else ''}", embed=cargo_embed)
                    alert_success.append("Cargo Spawn")
                    await msg.delete(delay=60)
        msg = await interaction.followup.send(content=TRANSLATIONS[dest]['test_alert_success'].format(', '.join(alert_success), 's' if cargo_data is not None and crate_data is not None else ''), wait=True, ephemeral=True)
        await msg.delete(delay=60)


    @app_commands.command(name='remove_data', description='Remove your guild and channel ID from the database.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 3600, key=lambda i: (i.guild_id, i.user.id))
    async def remove_data(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        dest = await self.get_language(interaction.guild)
        async with self.bot.engine.begin() as conn:
            await conn.execute(delete(CrateRespawnChannel).filter_by(guild_id=interaction.guild_id))
            await conn.execute(delete(CargoScrambleChannel).filter_by(guild_id=interaction.guild_id))
            await conn.execute(delete(CrateMutes).filter_by(guild_id=interaction.guild_id))
            await conn.execute(delete(CargoMutes).filter_by(guild_id=interaction.guild_id))
            await conn.execute(delete(AutoDelete).filter_by(guild_id=interaction.guild_id))
            await conn.execute(delete(Purification).filter_by(guild_id=interaction.guild_id))
            await conn.execute(delete(Controller).filter_by(guild_id=interaction.guild_id))
            await conn.execute(delete(Sproutlet).filter_by(guild_id=interaction.guild_id))
            await conn.execute(delete(Medics).filter_by(guild_id=interaction.guild_id))
        return await interaction.followup.send(content=TRANSLATIONS[dest]['remove_data_success'])
        

async def setup(bot: commands.Bot):
    await bot.add_cog(AlertCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(AlertCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")