from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from models.events import Lunar

config = dotenv_values(".env")


@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.default_permissions(administrator=True)
class GameEventsCog(commands.GroupCog, name='events'):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name='clear', description='Clear all event timers from your server.')
    @app_commands.checks.cooldown(2, 60, key=lambda i: (i.guild_id, i.user.id))
    async def clear_event_timers(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with self.bot.engine.begin() as conn:
            await conn.execute(delete(Lunar).where(Lunar.guild_id==interaction.guild_id))
        await interaction.followup.send(content=f"All event timers removed.")


    @app_commands.command(name='lunar', description='Run at 21:00 server to set the timer for the Lunar event.')
    @app_commands.describe(role_to_mention='The role you want mentioned with the timer.')
    @app_commands.describe(alert_channel='Channel for alerts.  Leave blank for this one.')
    @app_commands.describe(auto_delete='Set to True to delete previous alerts before sending a new one.')
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def lunar_event_set(self, interaction: discord.Interaction, alert_channel: Optional[discord.TextChannel] = None, role_to_mention: Optional[discord.Role] = None, auto_delete: Optional[Literal['On', 'Off']] = 'Off'):
        await interaction.response.defer(ephemeral=True)
        auto_dict = {"On": True, "Off": False}
        if role_to_mention:
            role_id = role_to_mention.id
        else:
            role_id = None
        if alert_channel:
            output_channel = alert_channel
        else:
            output_channel = interaction.channel
        async with self.bot.engine.begin() as conn:
            insert_stmt = insert(Lunar).values(last_alert=int(discord.utils.utcnow().timestamp()),guild_id=interaction.guild_id,channel_id=output_channel.id,role_id=role_id,added_by=interaction.user.id,auto_delete=auto_dict.get(auto_delete))
            update = insert_stmt.on_conflict_do_update(constraint='event_timers_unique_guild_id', set_={'last_alert': int(discord.utils.utcnow().timestamp()), 'channel_id': output_channel.id, 'role_id': role_id, 'added_by': interaction.user.id, 'auto_delete': auto_dict.get(auto_delete)})
            await conn.execute(update)
        await output_channel.send(f"{interaction.user.mention}, this is where your `Lunar Event` alerts will go.", delete_after=30)
        msg = await interaction.followup.send(content=f"Lunar timer started.\nAlert channel: {alert_channel.mention if alert_channel else interaction.channel.mention}\nAlert role: {role_to_mention.mention if role_to_mention else '`None`'}", silent=True, wait=True)
        await msg.delete(delay=30)


async def setup(bot: commands.Bot):
    await bot.add_cog(GameEventsCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(GameEventsCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")