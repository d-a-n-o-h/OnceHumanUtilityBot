from typing import Optional, Literal

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from sqlalchemy.dialects.postgresql import insert

from languages import LANGUAGES
from models.channels import Medics
from translations import TRANSLATIONS

config = dotenv_values(".env")

@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.default_permissions(administrator=True)
class MedicsCog(commands.GroupCog, name='medics'):
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


    @app_commands.command(name='setup', description='Setup for Medic/Trunk alerts.')
    @app_commands.describe(output_channel="The text/announcement channel you want notifications in.")
    @app_commands.describe(role_to_mention="The role you want mentioned in the alert. Blank = None")
    async def cargoscramble_alert_setup(self, interaction: discord.Interaction, output_channel: discord.TextChannel, role_to_mention: Optional[discord.Role] = None, auto_delete: Optional[Literal['On', 'Off']] = 'Off'):
        await interaction.response.defer(ephemeral=True)
        auto_dict = {"On": True, "Off": False}
        dest = LANGUAGES.get(str(interaction.guild_locale).lower(), 'en')
        if not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel or not output_channel.permissions_for(output_channel.guild.me).embed_links:
            return await interaction.followup.send(content=TRANSLATIONS[dest]['medics_channel_alert_error'].format(output_channel.mention), suppress_embeds=True)
        if not type(output_channel) == discord.TextChannel:
            medics_cmd = await self.find_cmd(self.bot, cmd='setup', group='medic')
            return await interaction.followup.send(content=TRANSLATIONS[dest]['check_channel_type_error'].format(medics_cmd.mention))
        if role_to_mention:
            role_id = role_to_mention.id
        else:
            role_id = None
        async with self.bot.engine.begin() as conn:
            insert_stmt = insert(Medics).values(auto_delete=auto_dict.get(auto_delete),guild_id=interaction.guild_id,channel_id=output_channel.id,role_id=role_id,added_by=interaction.user.id)
            update = insert_stmt.on_conflict_do_update(constraint='medics_unique_guildid', set_={'auto_delete': auto_dict.get(auto_delete), 'channel_id': output_channel.id, 'role_id': role_id, 'added_by': interaction.user.id})
            await conn.execute(update)
        await output_channel.send(content=TRANSLATIONS[dest]['setup_medics_channel_ping'].format(interaction.user.mention))
        return await interaction.followup.send(content=TRANSLATIONS[dest]['setup_medics_success'].format(output_channel.mention, role_to_mention.mention if role_to_mention else '`None`'), suppress_embeds=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MedicsCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(MedicsCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")