
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from sqlalchemy.dialects.postgresql import insert

from languages import LANGUAGES
from models.channels import CrateMutes, CrateRespawnChannel, AutoDelete
from translations import TRANSLATIONS

config = dotenv_values(".env")


class CrateMuteSelect(discord.ui.Select):
    def __init__(self):
        hours = [0,4,8,12,16,20]
        options = []
        options.append(discord.SelectOption(label="None", value="None", default=False))
        for hour in hours:
            hour_opt = discord.SelectOption(label=f"{hour:02}:00 UTC", value=hour, default=False)
            options.append(hour_opt)
        super().__init__(placeholder="Pick the hour(s) you want to mute.", max_values=6, options=options)

    async def callback(self, interaction: discord.Interaction):
        if len(self.values) == 1 and self.values[0] == "None":
            async with self.bot.engine.begin() as conn:
                insert_stmt = insert(CrateMutes).values(guild_id=interaction.guild_id,zero=False,four=False,eight=False,twelve=False,sixteen=False,twenty=False)
                update_stmt = insert_stmt.on_conflict_do_update(constraint='crate_mutes_unique_guildid', set_={'zero': False, 'four': False, 'eight': False, 'twelve': False, 'sixteen': False, 'twenty': False})
                await conn.execute(update_stmt)
            return await interaction.response.send_message("No mutes set or all mutes removed.", delete_after=60, ephemeral=True)
        db_dict = {0: "zero", 4: "four", 8: "eight", 12: "twelve", 16: "sixteen", 20: "twenty"}
        db_convert = {'zero': False, 'four': False, 'eight': False, 'twelve': False, 'sixteen': False, 'twenty': False, }
        muted_values = []
        for value in self.values:
            if value == "None":
                continue
            muted_values.append(f"`{int(value):02}:00`")
            db_convert[db_dict[int(value)]] = True
        muted_values.sort()
        async with self.bot.engine.begin() as conn:
            insert_stmt = insert(CrateMutes).values(guild_id=interaction.guild_id,zero=db_convert['zero'],four=db_convert['four'],eight=db_convert['eight'],twelve=db_convert['twelve'],sixteen=db_convert['sixteen'],twenty=db_convert['twenty'])
            update_stmt = insert_stmt.on_conflict_do_update(constraint='crate_mutes_unique_guildid', set_={'zero': db_convert['zero'], 'four': db_convert['four'], 'eight': db_convert['eight'], 'twelve': db_convert['twelve'], 'sixteen': db_convert['sixteen'], 'twenty': db_convert['twenty'], })
            await conn.execute(update_stmt)
        await interaction.response.send_message(f"You have muted {', '.join(muted_values)} UTC.", delete_after=60, ephemeral=True)

class CrateMuteView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(CrateMuteSelect())


@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.default_permissions(administrator=True)
class CrateCog(commands.GroupCog, name='crate'):
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


    @app_commands.command(name='mute', description='Mute crate alerts at specific times.')
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def mute_crate_alerts(self, interaction: discord.Interaction):
        view = CrateMuteView()
        return await interaction.response.send_message(content=f"Pick the hour(s) you want to mute for `WEAPON/GEAR CRATE RESPAWN ALERTS`.\nFind a timezone converter online if you don't know what your local time is in UTC.\nNothing will be selected until you click away from the menu.\nPicking `None` by itself will remove all mutes you have set.\n\n-# This menu is reusable and will delete after 2 minutes.", view=view, delete_after=120, ephemeral=True)
        

    @app_commands.command(name='setup', description='Setup for Weapon/Gear Crate respawn alerts.')
    @app_commands.describe(output_channel="The text/announcement channel you want notifications in.")
    @app_commands.describe(role_to_mention="The role you want mentioned in the alert. Blank = None")
    async def crate_alert_setup(self, interaction: discord.Interaction, output_channel: discord.TextChannel, role_to_mention: Optional[discord.Role] = None):
        await interaction.response.defer(ephemeral=True)
        dest = LANGUAGES.get(str(interaction.guild_locale).lower())
        if dest is None:
            dest = 'en'
        if not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel or not output_channel.permissions_for(output_channel.guild.me).embed_links:
            return await interaction.followup.send(content=TRANSLATIONS[dest]['crate_channel_alert_error'].format(output_channel.mention), suppress_embeds=True)
        if not type(output_channel) == discord.TextChannel:
            crate_cmd = await self.find_cmd(self.bot, cmd='setup', group='crate')
            return await interaction.followup.send(content=TRANSLATIONS[dest]['check_channel_type_error'].format(crate_cmd.mention))
        if role_to_mention:
            role_id = role_to_mention.id
        else:
            role_id = None
        async with self.bot.engine.begin() as conn:
            insert_stmt = insert(CrateRespawnChannel).values(guild_id=interaction.guild_id,channel_id=output_channel.id,role_id=role_id,added_by=interaction.user.id)
            update = insert_stmt.on_conflict_do_update(constraint='craterespawn_channels_unique_guildid', set_={'channel_id': output_channel.id, 'role_id': role_id, 'added_by': interaction.user.id})
            await conn.execute(update)
            autodelete_insert = insert(AutoDelete).values(crate=False,cargo=False,guild_id=interaction.guild_id)
            autodelete_insert = autodelete_insert.on_conflict_do_nothing(constraint='auto_delete_unique_guildid')
            await conn.execute(autodelete_insert)
        await output_channel.send(content=TRANSLATIONS[dest]['setup_crate_channel_ping'].format(interaction.user.mention))
        return await interaction.followup.send(content=TRANSLATIONS[dest]['setup_crate_success'].format(output_channel.mention, role_to_mention.mention if role_to_mention else '`None`'), suppress_embeds=True)
    

    @app_commands.command(name='auto_delete', description='Toggle Weapon/Gear Crate alerts to auto delete before the next post.')
    async def crate_auto_delete_toggle(self, interaction: discord.Interaction, auto_delete: Literal["On", "Off"]):
        if auto_delete == "On":
            auto_delete = True
        elif auto_delete == "Off":
            auto_delete = False
        async with self.bot.engine.begin() as conn:
            insert_stmt = insert(AutoDelete).values(guild_id=interaction.guild_id,crate=auto_delete)
            update = insert_stmt.on_conflict_do_update(constraint='auto_delete_unique_guildid', set_={'crate': auto_delete})
            await conn.execute(update)
        if auto_delete:
            enabled = "ENABLED"
        else:
            enabled = "DISABLED"
        return await interaction.response.send_message(f"**{enabled}** automatic delete of previous Weapon/Gear Crate respawn alerts.", ephemeral=True, delete_after=30)


async def setup(bot: commands.Bot):
    await bot.add_cog(CrateCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(CrateCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")