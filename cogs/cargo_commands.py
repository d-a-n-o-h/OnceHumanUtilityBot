from typing import Final, Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import create_async_engine

from languages import LANGUAGES
from models.channels import AutoDelete, CargoMutes, CargoScrambleChannel
from models.languages import GuildLanguage
from translations import TRANSLATIONS

config = dotenv_values(".env")

class CargoMuteSelect(discord.ui.Select):
    def __init__(self):
        self.engine: Final = create_async_engine(config["DATABASE_STRING"], pool_size=50, max_overflow=10, pool_recycle=30)
        hours = [12,15,18,22]
        options = []
        options.append(discord.SelectOption(label="None", value="None", default=False))
        for hour in hours:
            if hour == 18:
                hour_opt = discord.SelectOption(label=f"{hour:02}:30 UTC", value=hour, default=False)
            else:
                hour_opt = discord.SelectOption(label=f"{hour:02}:00 UTC", value=hour, default=False)
            options.append(hour_opt)
        super().__init__(placeholder="Pick the hour(s) you want to mute.", max_values=4, options=options)

    async def callback(self, interaction: discord.Interaction):
        if len(self.values) == 1 and self.values[0] == "None":
            async with self.engine.begin() as conn:
                insert_stmt = insert(CargoMutes).values(guild_id=interaction.guild_id,twelve=False,fifteen=False,twenty_two=False,eighteen_thirty=False)
                update_stmt = insert_stmt.on_conflict_do_update(constraint='cargo_mutes_unique_guildid', set_={'twelve': False, 'fifteen': False, 'twenty_two': False, 'eighteen_thirty': False})
                await conn.execute(update_stmt)
            return await interaction.response.send_message("No mutes set or all mutes removed.", delete_after=60, ephemeral=True)
        db_dict = {12: 'twelve', 15: 'fifteen', 18: 'eighteen_thirty', 22: 'twenty_two'}
        db_convert = {'twelve': False, 'fifteen': False, 'eighteen_thirty': False, 'twenty_two': False}
        muted_values = []
        for value in self.values:
            if value == "None":
                continue
            if value == 18:
                muted_values.append(f"`{int(value):02}:30`")
            else:
                muted_values.append(f"`{int(value):02}:00`")
            db_convert[db_dict[int(value)]] = True
        muted_values.sort()
        async with self.engine.begin() as conn:
            insert_stmt = insert(CargoMutes).values(guild_id=interaction.guild_id,twelve=db_convert['twelve'],fifteen=db_convert['fifteen'],twenty_two=db_convert['twenty_two'],eighteen_thirty=db_convert['eighteen_thirty'])
            update_stmt = insert_stmt.on_conflict_do_update(constraint='cargo_mutes_unique_guildid', set_={'twelve': db_convert['twelve'], 'fifteen': db_convert['fifteen'], 'twenty_two': db_convert['twenty_two'], 'eighteen_thirty': db_convert['eighteen_thirty']})
            await conn.execute(update_stmt)
        await interaction.response.send_message(f"You have muted {', '.join(muted_values)} UTC.", delete_after=60, ephemeral=True)

class CargoMuteView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(CargoMuteSelect())


@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.default_permissions(administrator=True)
class CargoCog(commands.GroupCog, name='cargo'):
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


    @app_commands.command(name='mute', description='Mute cargo alerts at specific times.')
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def mute_cargo_alerts(self, interaction: discord.Interaction):
        view = CargoMuteView()
        return await interaction.response.send_message(content=f"Pick the hour(s) you want to mute for `CARGO SCRAMBLE SPAWN ALERTS`.\nFind a timezone converter online if you don't know what your local time is in UTC.\nNothing will be selected until you click away from the menu.\nPicking `None` by itself will remove all mutes you have set.\n\n-# This menu is reusable and will delete after 2 minutes.", view=view, delete_after=120, ephemeral=True)        
    

    @app_commands.command(name='setup', description='Setup for Cargo Scramble alerts.')
    @app_commands.describe(output_channel="The text/announcement channel you want notifications in.")
    @app_commands.describe(role_to_mention="The role you want mentioned in the alert. Blank = None")
    @app_commands.describe(asian_server="Toggle to send the alert an hour earlier for Asian servers.")
    async def cargoscramble_alert_setup(self, interaction: discord.Interaction, output_channel: discord.TextChannel, role_to_mention: Optional[discord.Role] = None, asian_server: Optional[bool] = False):
        await interaction.response.defer(ephemeral=True)
        dest = await self.get_language(interaction.guild)
        if not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel or not output_channel.permissions_for(output_channel.guild.me).embed_links:
            return await interaction.followup.send(content=TRANSLATIONS[dest]['cargo_channel_alert_error'].format(output_channel.mention), suppress_embeds=True)
        if not type(output_channel) == discord.TextChannel:
            cargo_cmd = await self.find_cmd(self.bot, cmd='setup', group='cargo')
            return await interaction.followup.send(content=TRANSLATIONS[dest]['check_channel_type_error'].format(cargo_cmd.mention))
        if role_to_mention:
            role_id = role_to_mention.id
        else:
            role_id = None
        async with self.bot.engine.begin() as conn:
            insert_stmt = insert(CargoScrambleChannel).values(guild_id=interaction.guild_id,channel_id=output_channel.id,role_id=role_id,added_by=interaction.user.id,asian_server=asian_server)
            update = insert_stmt.on_conflict_do_update(constraint='cargoscramble_channels_unique_guildid', set_={'channel_id': output_channel.id, 'role_id': role_id, 'added_by': interaction.user.id, 'asian_server': asian_server})
            await conn.execute(update)
            autodelete_insert = insert(AutoDelete).values(crate=False,cargo=False,guild_id=interaction.guild_id)
            autodelete_insert = autodelete_insert.on_conflict_do_nothing(constraint='auto_delete_unique_guildid')
            await conn.execute(autodelete_insert)
            cargo_insert = insert(CargoMutes).values(guild_id=interaction.guild_id,twelve=False,fifteen=False,twenty_two=False,eighteen_thirty=False)
            cargo_update = cargo_insert.on_conflict_do_nothing(constraint='cargo_mutes_unique_guildid')
            await conn.execute(cargo_update)
        try:
            success_embed = discord.Embed(color=discord.Color.green(), description=TRANSLATIONS[dest]['setup_cargo_channel_ping'].format(interaction.user.mention))
            await output_channel.send(embed=success_embed)
        except Exception as e:
            return await interaction.followup.send(content=f"{e}", suppress_embeds=True)
        return await interaction.followup.send(content=TRANSLATIONS[dest]['setup_cargo_success'].format(output_channel.mention, role_to_mention.mention if role_to_mention else '`None`'), suppress_embeds=True)


    @app_commands.command(name='auto_delete', description='Toggle Cargo Scramble alerts to auto delete before the next post.')
    async def crate_auto_delete_toggle(self, interaction: discord.Interaction, auto_delete: Literal["On", "Off"]):
        auto_dict = {"On": True, "Off": False}
        async with self.bot.engine.begin() as conn:
            insert_stmt = insert(AutoDelete).values(guild_id=interaction.guild_id,cargo=auto_dict.get(auto_delete))
            update = insert_stmt.on_conflict_do_update(constraint='auto_delete_unique_guildid', set_={'cargo': auto_dict.get(auto_delete)})
            await conn.execute(update)
        if auto_delete == "On":
            enabled = "ENABLED"
        else:
            enabled = "DISABLED"
        return await interaction.response.send_message(f"**{enabled}** automatic delete of previous Cargo Scramble spawn alerts.", ephemeral=True, delete_after=30)

async def setup(bot: commands.Bot):
    await bot.add_cog(CargoCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(CargoCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")