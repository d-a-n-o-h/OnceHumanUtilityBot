import asyncio
import datetime
import sys
from typing import Optional

import asqlite
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
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

class TimerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=utc)

    def cog_load(self):
        if not self.scheduler.running:
            self.scheduler.add_job(self.reset_alert, 'cron', hour='0,4,8,12,16,20', minute=0)
            self.scheduler.start()

    def cog_unload(self):
        self.scheduler.remove_all_jobs()
        self.scheduler.shutdown(wait=False)

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

    async def reset_alert(self):
        guilds_sent = 0
        time_now = datetime.datetime.now(tz=utc)
        print(f"Timer! {time_now}")
        reset_embed = discord.Embed(color=discord.Color.blurple(),title="Once Human Gear/Weapon Crates Reset")
        time_now = time_now.replace(minute=0, second=0, microsecond=0)
        timestamp_now = datetime.datetime.timestamp(time_now)
        reset_embed.add_field(name='', value=f"This is the <t:{int(timestamp_now)}:t> reset announcement.")
        setup_cmd = await self.find_cmd(self.bot, cmd='setup')
        reset_embed.add_field(name='', value=f"Use {setup_cmd.mention} to change the channel or change/add a role to ping.", inline=False) # type: ignore
        async with asqlite.connect(db_name) as conn:
            async with conn.cursor() as cursor:
                all_channels = await cursor.execute("SELECT channel_id, role_id FROM channels;")
                all_channels = await all_channels.fetchall()
        for i, (channel_id, role_id) in enumerate(all_channels):
            cur_chan = self.bot.get_channel(channel_id)
            if not cur_chan:
                async with asqlite.connect(db_name) as conn:
                    async with conn.cursor() as cursor:
                        data = {"channel_id": channel_id}
                        await cursor.execute("DELETE FROM channels WHERE channel_id=:channel_id;", data)
                        await conn.commit()
                continue
            if cur_chan.guild:
                role_to_mention = cur_chan.guild.get_role(role_id)
            else:
                role_to_mention = None
            print(f"{i+1}/{len(all_channels)}", channel_id)
            try:
                await cur_chan.send(content=f"{role_to_mention.mention if role_to_mention is not None else ''}", embed=reset_embed)
                await asyncio.sleep(0.1)
                guilds_sent += 1
            except Exception as e:
                print(f"Error: {e}")
                continue
        print(f"Sent to {guilds_sent} out of {len(self.bot.guilds)}.")


    @app_commands.command(name='next', description='Returns the current UTC time and the next respawn timer.')
    @app_commands.guild_install()
    async def what_time_is_it(self, interaction: discord.Interaction):
        time_now = datetime.datetime.now(tz=utc)
        next_time_timestamp = datetime.datetime.timestamp(self.scheduler.get_jobs()[0].next_run_time)
        await interaction.response.send_message(f"It's `{time_now.hour:02d}:{time_now.minute:02d} UTC`.\nCrates respawn at `00:00`, `04:00`, `08:00`, `12:00`, `16:00`, and `20:00` UTC.\n\nNext respawn <t:{int(next_time_timestamp)}:F> or roughly <t:{int(next_time_timestamp)}:R>.", ephemeral=True, delete_after=60)



async def setup(bot: commands.Bot):
    await bot.add_cog(TimerCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(TimerCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")