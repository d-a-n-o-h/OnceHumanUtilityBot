import asyncio
import datetime
import logging
import logging.handlers
import sys
import traceback
from typing import Final, Literal, Optional

import discord
from discord.ext import commands
from dotenv import dotenv_values
from sqlalchemy.ext.asyncio import create_async_engine

from cogs import EXTENSIONS
from languages import LANGUAGES
from translations import TRANSLATIONS

config = dotenv_values(".env")
utc = datetime.timezone.utc

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)

class NoResumedFilter(logging.Filter):
    def filter(self, record):
        return not "has successfully RESUMED session" in record.getMessage()
logger.addFilter(NoResumedFilter())

class NoMCFilter(logging.Filter):
    def filter(self, record):
        return not "Privileged message content" in record.getMessage()
logger.addFilter(NoMCFilter())

handler = logging.handlers.RotatingFileHandler(
    filename='discord.log',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,  # Rotate through 5 files
)
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)


class OHTimerBot(commands.AutoShardedBot):

    def __init__(self):
        self.uptime_timestamp = f"<t:{int(datetime.datetime.timestamp(datetime.datetime.now(tz=utc)))}:R>"
        self.last_update = f"<t:1728370200:f>"
        intents = discord.Intents.default()
        self.initial_extensions = EXTENSIONS
        if config["DATABASE_STRING"]:
            self.engine: Final = create_async_engine(config["DATABASE_STRING"], pool_size=50, max_overflow=10, pool_recycle=30)
        else:
            print("Please set the DATABASE_STRING value in the .env file and restart the bot.")
            sys.exit(1)
        
        
        super().__init__(
            intents=intents,
            command_prefix=commands.when_mentioned_or("<><><>")
            )
        
        if config["TESTING_GUILD_ID"]:
            self.testing_guild_id: Final[int] = int(config["TESTING_GUILD_ID"])
        else:
            self.testing_guild = None

    async def setup_hook(self) -> None:
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
            except Exception as e:
                traceback.print_exception(type(e), e, e.__traceback__)
                print(f"Failed to load extension {extension}.")

        
    async def on_ready(self):
        print(f"Logged in as {self.user.name} (ID# {self.user.id})")


bot = OHTimerBot()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    dest = LANGUAGES.get(str(interaction.guild_locale).lower(), 'en')
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        retry_time = round(error.retry_after, 0)
        if not interaction.response.is_done():
            await interaction.response.send_message(content=TRANSLATIONS[dest]['app_command_cooldown_error'].format(f'{retry_time:,}'), ephemeral=True, delete_after=(error.retry_after/2))
        else:
            msg = await interaction.followup.send(content=TRANSLATIONS[dest]['app_command_cooldown_error'].format(f'{retry_time:,}'), wait=True)
            await msg.delete(delay=(error.retry_after/2))
    else:
        if not interaction.response.is_done():
            await interaction.response.send_message(content=TRANSLATIONS[dest]['feedback_error'].format(error), ephemeral=True, delete_after=60)
        else:
            msg = await interaction.followup.send(content=TRANSLATIONS[dest]['feedback_error'].format(error), wait=True)
            await msg.delete(delay=60)
    traceback.print_exception(type(error), error, error.__traceback__)


@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    await ctx.message.delete()
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        msg = await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        await asyncio.sleep(5)
        await msg.delete()
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    msg = await ctx.send(f"Synced the tree to {ret}/{len(guilds)} guilds.")
    await asyncio.sleep(5)
    await msg.delete()


if config["BOT_TOKEN"]:
    bot.run(config["BOT_TOKEN"])
else:
    print("Please set the BOT_TOKEN value in the .env file and restart the bot.")
    sys.exit(1)