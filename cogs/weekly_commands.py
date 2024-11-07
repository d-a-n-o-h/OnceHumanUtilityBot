import calendar
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from sqlalchemy.dialects.postgresql import insert

from models.weekly_resets import Controller, Purification, Sproutlet
from languages import LANGUAGES
from translations import TRANSLATIONS

config = dotenv_values(".env")

@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.default_permissions(administrator=True)
class WeeklysCog(commands.GroupCog, name='weekly'):
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
                
    async def day_to_number(self, day: str) -> int:
        day = day.lower()
        days_to_num = {
            'monday': 1,
            'tuesday': 2,
            'wednesday': 3,
            'thursday': 4,
            'friday': 5,
            'saturday': 6, 
            'sunday': 7,
            'none': None
            }
        return days_to_num[day]


    @app_commands.command(name='purification_setup', description='Setup for Purification reset alerts.')
    @app_commands.describe(output_channel="The text/announcement channel you want notifications in.")
    @app_commands.describe(role_to_mention="The role you want mentioned in the alert. Blank = None")
    @app_commands.describe(day="Which day your server does the purification reset.")
    @app_commands.describe(auto_delete="'On' if you want the message to delete itself before the next one is sent.")
    async def purification_alert_setup(self, interaction: discord.Interaction, output_channel: discord.TextChannel, day: Literal['None', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'], role_to_mention: Optional[discord.Role] = None, auto_delete: Optional[Literal['On', 'Off']] = 'Off'):
        # return await interaction.response.send_message("Still working on it!", ephemeral=True, delete_after=15)
        await interaction.response.defer(ephemeral=True)
        day_num = await self.day_to_number(day)
        if auto_delete == "On":
            auto_delete = True
        elif auto_delete == "Off":
            auto_delete = False
        dest = LANGUAGES.get(str(interaction.guild_locale).lower(), 'en')
        if not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel or not output_channel.permissions_for(output_channel.guild.me).embed_links:
            return await interaction.followup.send(content=TRANSLATIONS[dest]['purification_channel_alert_error'].format(output_channel.mention), suppress_embeds=True)
        if not type(output_channel) == discord.TextChannel:
            purification_setup_cmd = await self.find_cmd(self.bot, cmd='purification_setup', group='weekly')
            return await interaction.followup.send(content=TRANSLATIONS[dest]['check_channel_type_error'].format(purification_setup_cmd.mention))
        if role_to_mention:
            role_id = role_to_mention.id
        else:
            role_id = None
        async with self.bot.engine.begin() as conn:
            insert_stmt = insert(Purification).values(guild_id=interaction.guild_id,channel_id=output_channel.id,role_id=role_id,reset_day=day_num,auto_delete=auto_delete)
            update = insert_stmt.on_conflict_do_update(constraint='purification_reset_day_unique_guildid', set_={'channel_id': output_channel.id, 'role_id': role_id, 'reset_day': day_num, 'auto_delete': auto_delete})
            await conn.execute(update)
        await output_channel.send(content=TRANSLATIONS[dest]['setup_purification_channel_ping'].format(interaction.user.mention))
        msg = await interaction.followup.send(content=TRANSLATIONS[dest]['setup_purification_success'].format(output_channel.mention, calendar.day_name[day_num-1] if day != "None" else 'None', role_to_mention.mention if role_to_mention else '`None`'), suppress_embeds=True, wait=True)
        await msg.delete(delay=60)
    

    @app_commands.command(name='controller_setup', description='Setup for Controller reset alerts.')
    @app_commands.describe(output_channel="The text/announcement channel you want notifications in.")
    @app_commands.describe(role_to_mention="The role you want mentioned in the alert. Blank = None")
    @app_commands.describe(day="Which day your server does the controller reset.")
    @app_commands.describe(auto_delete="'On' if you want the message to delete itself before the next one is sent.")
    async def controller_alert_setup(self, interaction: discord.Interaction, output_channel: discord.TextChannel, day: Literal['None', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'], role_to_mention: Optional[discord.Role] = None, auto_delete: Optional[Literal['On', 'Off']] = 'Off'):
        # return await interaction.response.send_message("Still working on it!", ephemeral=True, delete_after=15)
        await interaction.response.defer(ephemeral=True)
        day_num = await self.day_to_number(day)
        auto_dict = {"On": True, "Off": False}
        dest = LANGUAGES.get(str(interaction.guild_locale).lower(), 'en')
        if not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel or not output_channel.permissions_for(output_channel.guild.me).embed_links:
            return await interaction.followup.send(content=TRANSLATIONS[dest]['controller_channel_alert_error'].format(output_channel.mention), suppress_embeds=True)
        if not type(output_channel) == discord.TextChannel:
            controller_setup_cmd = await self.find_cmd(self.bot, cmd='controller_setup', group='weekly')
            return await interaction.followup.send(content=TRANSLATIONS[dest]['check_channel_type_error'].format(controller_setup_cmd.mention))
        if role_to_mention:
            role_id = role_to_mention.id
        else:
            role_id = None
        async with self.bot.engine.begin() as conn:
            insert_stmt = insert(Controller).values(guild_id=interaction.guild_id,channel_id=output_channel.id,role_id=role_id,reset_day=day_num,auto_delete=auto_dict.get(auto_delete))
            update = insert_stmt.on_conflict_do_update(constraint='controller_reset_day_unique_guildid', set_={'channel_id': output_channel.id, 'role_id': role_id, 'reset_day': day_num, 'auto_delete': auto_dict.get(auto_delete)})
            await conn.execute(update)
        await output_channel.send(content=TRANSLATIONS[dest]['setup_controller_channel_ping'].format(interaction.user.mention))
        msg = await interaction.followup.send(content=TRANSLATIONS[dest]['setup_controller_success'].format(output_channel.mention, calendar.day_name[day_num-1] if isinstance(day_num, int) else 'None', role_to_mention.mention if role_to_mention else '`None`'), suppress_embeds=True, wait=True)
        await msg.delete(delay=60)


    @app_commands.command(name='sproutlet_setup', description='Setup for Sproutlet reset alerts.')
    @app_commands.describe(output_channel="The text/announcement channel you want notifications in.")
    @app_commands.describe(role_to_mention="The role you want mentioned in the alert. Blank = None")
    @app_commands.describe(hour="The hour your server resets IN UTC TIME.")
    @app_commands.describe(auto_delete="'On' if you want the message to delete itself before the next one is sent.")
    async def sproutlet_alert_setup(self, interaction: discord.Interaction, output_channel: discord.TextChannel, hour: Literal[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23], role_to_mention: Optional[discord.Role] = None, auto_delete: Optional[Literal['On', 'Off']] = 'Off'):
        await interaction.response.defer(ephemeral=True)
        auto_dict = {"On": True, "Off": False}
        dest = LANGUAGES.get(str(interaction.guild_locale).lower(), 'en')
        if not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel or not output_channel.permissions_for(output_channel.guild.me).embed_links:
            return await interaction.followup.send(content=TRANSLATIONS[dest]['sproutlet_channel_alert_error'].format(output_channel.mention), suppress_embeds=True)
        if not type(output_channel) == discord.TextChannel:
            sproutlet_setup_cmd = await self.find_cmd(self.bot, cmd='sproutlet_setup', group='weekly')
            return await interaction.followup.send(content=TRANSLATIONS[dest]['check_channel_type_error'].format(sproutlet_setup_cmd.mention))
        if role_to_mention:
            role_id = role_to_mention.id
        else:
            role_id = None
        async with self.bot.engine.begin() as conn:
            insert_stmt = insert(Sproutlet).values(guild_id=interaction.guild_id,channel_id=output_channel.id,role_id=role_id,hour=int(hour),auto_delete=auto_dict.get(auto_delete))
            update = insert_stmt.on_conflict_do_update(constraint='sproutlet_unique_guildid', set_={'channel_id': output_channel.id, 'role_id': role_id, 'hour': int(hour), 'auto_delete': auto_dict.get(auto_delete)})
            await conn.execute(update)
        await output_channel.send(content=TRANSLATIONS[dest]['setup_sproutlet_channel_ping'].format(interaction.user.mention))
        msg = await interaction.followup.send(content=TRANSLATIONS[dest]['setup_sproutlet_success'].format(output_channel.mention, f'`{hour}:15 UTC`', role_to_mention.mention if role_to_mention else '`None`'), suppress_embeds=True, wait=True)
        await msg.delete(delay=60)


async def setup(bot: commands.Bot):
    await bot.add_cog(WeeklysCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(WeeklysCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")