import asyncio
import datetime
import random
import sys
from typing import Optional

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import create_async_engine

from modals.channels import ReportingChannel

utc = datetime.timezone.utc

config = dotenv_values(".env")

if config["DATABASE_STRING"]:
    engine = create_async_engine(config["DATABASE_STRING"])
elif config["DATABASE"]:
    engine = create_async_engine(f"sqlite+asqlite:///{config['DATABASE']}")
else:
    print("Please set the DATABASE or DATABASE_STRING value in the .env file and restart the bot.")
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
            command = discord.utils.find(lambda c: c.name.lower() == cmd.lower(), await bot.tree.fetch_commands())
            return command
        else:
            cmd_group = discord.utils.find(lambda cg: cg.name.lower() == group.lower(), await bot.tree.fetch_commands())
            for child in cmd_group.options:  # type: ignore
                if child.name.lower() == cmd.lower():
                    return child

    async def reset_alert(self):
        for _ in range(5):
            try:
                guilds_sent = 0
                time_now = datetime.datetime.now(tz=utc)
                print(f"Timer! {time_now}")
                reset_embed = discord.Embed(color=discord.Color.blurple(),title="Once Human Gear/Weapon Crates Reset")
                time_now = time_now.replace(minute=0, second=0, microsecond=0)
                timestamp_now = datetime.datetime.timestamp(time_now)
                reset_embed.add_field(name='', value=f"This is the <t:{int(timestamp_now)}:t> reset announcement.")
                setup_cmd = await self.find_cmd(self.bot, cmd='setup')
                reset_embed.add_field(name='', value=f"Use {setup_cmd.mention} to change the channel or change/add a role to ping.", inline=False) # type: ignore
                reset_embed.set_footer(text="Log out to the main menu and log back in to see the reset chests.")
                async with engine.begin() as conn:
                    all_channels = await conn.execute(select(ReportingChannel.channel_id, ReportingChannel.role_id))
                    all_channels = all_channels.all()
                await engine.dispose(close=True)
                random.shuffle(all_channels) # type: ignore
                for i, (channel_id, role_id) in enumerate(all_channels):
                    cur_chan = self.bot.get_channel(channel_id)
                    if not cur_chan:
                        async with engine.begin() as conn:
                            await conn.execute(delete(ReportingChannel).filter_by(channel_id=channel_id))
                        await engine.dispose(close=True)
                        continue
                    if cur_chan.guild:
                        role_to_mention = cur_chan.guild.get_role(role_id)
                    else:
                        role_to_mention = None
                    try:
                        await cur_chan.send(content=f"{role_to_mention.mention if role_to_mention is not None else ''}", embed=reset_embed)
                        guilds_sent += 1
                    except Exception as e:
                        print(f"({channel_id}) Error: {e}")
                        async with engine.begin() as conn:
                            await conn.execute(delete(ReportingChannel).filter_by(channel_id=channel_id))
                        await engine.dispose(close=True)
                        continue
                print(f"Sent to {guilds_sent} guilds.\nBot currently in {len(self.bot.guilds)} guilds.")
            except Exception as e:
                err = e
                continue
            else:
                break
        else:
            raise err # type: ignore


    @app_commands.command(name='next', description='Returns the current UTC time and the next respawn timer.')
    @app_commands.guild_install()
    async def what_time_is_it(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        time_now = datetime.datetime.now(tz=utc)
        next_time_timestamp = datetime.datetime.timestamp(self.scheduler.get_jobs()[0].next_run_time)
        msg = await interaction.followup.send(content=f"It's `{time_now.hour:02d}:{time_now.minute:02d} UTC`.\nCrates respawn at `00:00`, `04:00`, `08:00`, `12:00`, `16:00`, and `20:00` UTC.\n\nNext respawn <t:{int(next_time_timestamp)}:F> or roughly <t:{int(next_time_timestamp)}:R>.", wait=True)
        await asyncio.sleep(60)
        await msg.delete()


async def setup(bot: commands.Bot):
    await bot.add_cog(TimerCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(TimerCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")