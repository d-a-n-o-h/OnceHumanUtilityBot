import asyncio
import datetime
import sys

import asqlite
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import dotenv_values

utc = datetime.timezone.utc
times = [
        datetime.time(hour=4, minute=0, tzinfo=utc),
        datetime.time(hour=8, minute=0, tzinfo=utc),
        datetime.time(hour=12, minute=0, tzinfo=utc),
        datetime.time(hour=16, minute=0, tzinfo=utc),
        datetime.time(hour=20, minute=0, tzinfo=utc),
        datetime.time(hour=0, minute=0, tzinfo=utc),
    ]
config = dotenv_values(".env")
if config["DATABASE"]:
    db_name = config["DATABASE"]
else:
    print("Please set the DATABASE value in the .env file and restart the bot.")
    sys.exit(0)

class TimerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reset_alert.start()

    def cog_unload(self):
        for task in asyncio.all_tasks():
            name = task.get_name()
            if "TimerCog.reset_alert" in name:
                task.cancel()
        self.reset_alert.cancel()

    @tasks.loop(time=times)
    async def reset_alert(self):
        time_now = datetime.datetime.now(tz=utc)
        print(f"Timer! {time_now}")
        async with asqlite.connect(db_name) as conn:
            async with conn.cursor() as cursor:
                all_channels = await cursor.execute("SELECT channel_id, role_id FROM channels;")
                all_channels = await all_channels.fetchall()
                for channel in all_channels:
                    cur_chan = self.bot.get_channel(channel[0])
                    if cur_chan and isinstance(cur_chan, discord.TextChannel):
                        role_to_mention = cur_chan.guild.get_role(channel[1])
                        reset_embed = discord.Embed(color=discord.Color.blurple(),title="Once Human Gear/Weapon Crates Reset Announcement")
                        time_now = time_now.replace(minute=0, second=0, microsecond=0)
                        timestamp_now = datetime.datetime.timestamp(time_now)
                        reset_embed.add_field(name='', value=f"This is the <t:{int(timestamp_now)}:t> reset announcement.")
                        await cur_chan.send(content=f"{role_to_mention.mention if role_to_mention else ''}", embed=reset_embed)
                    

    @reset_alert.before_loop
    async def before_reset_alert(self):
        await self.bot.wait_until_ready()


    @app_commands.command(name='next', description='Returns the current UTC time and the next respawn timer.')
    async def what_time_is_it(self, interaction: discord.Interaction):
        time_now = datetime.datetime.now(tz=utc)
        hour = time_now.hour
        minute = time_now.minute
        if self.reset_alert.next_iteration is not None:
            next_time_timestamp = datetime.datetime.timestamp(self.reset_alert.next_iteration)
        await interaction.response.send_message(f"It's `{hour:02d}:{minute:02d} UTC`.\nChests respawn at `02:00`, `06:00`, `10:00`, `14:00`, `18:00`, and `22:00` UTC.\n\nNext respawn <t:{int(next_time_timestamp)}:F>.", ephemeral=True, delete_after=60)


async def setup(bot: commands.Bot):
    await bot.add_cog(TimerCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    for task in asyncio.all_tasks():
        name = task.get_name()
        if "TimerCog.reset_alert" in name:
            task.cancel()
    await bot.remove_cog(TimerCog(bot))  # type: ignore
    print(f"{__name__[5:].upper()} unloaded")