import asyncio
import datetime
import sys
from typing import Literal, Optional

import discord
from discord.ext import commands
from dotenv import dotenv_values

config = dotenv_values(".env")
utc = datetime.timezone.utc


class OHTimerBot(commands.Bot):

    def __init__(self):
        self.initial_extensions = (
            'cogs.bot_commands',
            'cogs.bot_events',
            'cogs.timer',
            'cogs.utils'
            )
        self.uptime_timestamp = f"<t:{int(datetime.datetime.timestamp(datetime.datetime.now(tz=utc)))}:R>" 
        intents = discord.Intents.default()

        super().__init__(
            intents=intents,
            command_prefix=commands.when_mentioned_or("<>")
            )
        
        if config["TESTING_GUILD_ID"]:
            self.testing_guild_id = int(config["TESTING_GUILD_ID"])
        else:
            self.testing_guild = None
        if config["DATABASE_STRING"]:
            self.db_string = config["DATABASE_STRING"]
        else:
            print("Please set the DATABASE_STRING value in the .env file and restart the bot.")
            sys.exit(1)

    async def setup_hook(self) -> None:
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
            except Exception as e:
                print(f"Failed to load extension {extension}.")

        if self.testing_guild_id:
            guild = discord.Object(self.testing_guild_id)
            await self.tree.sync(guild=guild)
        await self.tree.sync()
        
    async def on_ready(self):
        print(f"Logged in as {self.user.name} (ID# {self.user.id})")  # type: ignore


bot = OHTimerBot()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        print(error)
        if not interaction.response.is_done():
            return await interaction.response.send_message(f"That command is on cooldown.  Please try again in `{round(error.retry_after, 2)}` seconds.", ephemeral=True, delete_after=error.retry_after)
        else:
            msg = await interaction.followup.send(content=f"That command is on cooldown.  Please try again in `{round(error.retry_after, 2)}` seconds.", wait=True)
            await msg.delete(delay=error.retry_after)
    else:
        if not interaction.response.is_done():
            return await interaction.response.send_message(f"There was an error with your request:\n`{error}`", ephemeral=True, delete_after=60)
        else:
            msg = await interaction.followup.send(content=f"There was an error with your request:\n`{error}`", wait=True)
            await msg.delete(delay=60)


@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
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