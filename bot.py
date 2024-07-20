import datetime
import os
import sys
from typing import Literal, Optional

import asqlite
import discord
from discord.ext import commands
from discord.ext.commands import ExtensionAlreadyLoaded
from dotenv import dotenv_values

config = dotenv_values(".env")
utc = datetime.timezone.utc

if config["DATABASE"]:
    db_name = config["DATABASE"]
else:
    print("Please set the DATABASE value in the .env file and restart the bot.")
    sys.exit(0)
if config["BOT_TOKEN"]:
    token = config["BOT_TOKEN"]
else:
    print("Please set the BOT_TOKEN value in the .env file and restart the bot.")
    sys.exit(0)
    

intents = discord.Intents.default()
intents.message_content = True

class OHTimerBot(commands.Bot):
    def __init__(self, *args, testing_guild_id: Optional[int] = None,  **kwargs):
        super().__init__(*args, **kwargs)
        self.testing_guild_id = testing_guild_id

    async def setup_hook(self) -> None:
        for subdir, _, files in os.walk("cogs"):
            files = [
                file for file in files if file.endswith(".py") and "template" not in file
            ]
            for file in files:
                if len(subdir.split("cogs\\")) >= 2:
                    try:
                        sub = subdir.split("cogs\\")[1]
                        await bot.load_extension(f"cogs.{sub}.{file[:-3]}")
                    except ExtensionAlreadyLoaded:
                        sub = subdir.split("cogs\\")[1]
                        await bot.reload_extension(f"cogs.{sub}.{file[:-3]}")
                else:
                    try:
                        await bot.load_extension(f"{subdir}.{file[:-3]}")
                    except ExtensionAlreadyLoaded:
                        await bot.reload_extension(f"{subdir}.{file[:-3]}")
        if not os.path.exists(db_name):
            with open(db_name, 'w') as f:
                f.write("")
            async with asqlite.connect(db_name) as conn:
                async with conn.cursor() as cursor:
                    await cursor.executescript("""
                                            BEGIN;
                                            CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id BIGINT UNIQUE, channel_id BIGINT UNIQUE);
                                            COMMIT;
                                            """)
        if self.testing_guild_id:
            guild = discord.Object(self.testing_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        
    async def on_ready(self):
        print(f"Logged in as {self.user.name} (ID# {self.user.id})")  # type: ignore

bot = OHTimerBot(intents=intents, command_prefix="<>")

@bot.command()
@commands.is_owner()
async def reload(ctx: commands.Context, cog: str):
    await ctx.message.delete()
    if os.path.exists(f"cogs/{cog.lower()}.py"):
        try:
            await bot.reload_extension(f"cogs.{cog.lower()}")
            await ctx.send(f"Reloaded `cogs.{cog.upper()}`")
        except Exception as e:
            await ctx.send(f"Error reloading `{cog.upper()}`: {e}")


@bot.command()
@commands.is_owner()
async def reloadall(ctx: commands.Context):
    await ctx.message.delete()
    for subdir, _, files in os.walk("cogs"):
        files = [
            file for file in files if file.endswith(".py") and "template" not in file
        ]
        for file in files:
            if len(subdir.split("cogs\\")) >= 2:
                try:
                    sub = subdir.split("cogs\\")[1]
                    await bot.load_extension(f"cogs.{sub}.{file[:-3]}")
                    await ctx.send(f"Loaded `cogs.{sub}.{file[:-3]}`")
                except ExtensionAlreadyLoaded:
                    sub = subdir.split("cogs\\")[1]
                    await bot.reload_extension(f"cogs.{sub}.{file[:-3]}")
                    await ctx.send(f"Reloaded `cogs.{sub}.{file[:-3]}`")
            else:
                try:
                    await bot.load_extension(f"{subdir}.{file[:-3]}")
                    await ctx.send(f"Loaded `{subdir}.{file[:-3]}`")
                except ExtensionAlreadyLoaded:
                    await bot.reload_extension(f"{subdir}.{file[:-3]}")
                    await ctx.send(f"Reloaded `{subdir}.{file[:-3]}`")


@bot.command()
@commands.is_owner()
async def load(ctx: commands.Context, extension: str):
    await ctx.message.delete()
    try:
        await bot.load_extension(f"cogs.{extension}")
        await ctx.send(f"Loaded `{extension.upper()}`")
    except Exception as e:
        await ctx.send(f"Error loading `{extension.upper()}`\n{e}")


# https://about.abstractumbra.dev/discord.py/2023/01/29/sync-command-example.html
@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(
    ctx: commands.Context,
    guilds: commands.Greedy[discord.Object],
    spec: Optional[Literal["~", "*", "^", "x"]] = None,
) -> None:
    await ctx.reply("Sync request received.")
    if not guilds:
        if spec == "~":  # sync all to current guild
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":  # sync global to current guild
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":  # remove commands sync'd to current guild
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        elif spec == "x":  # remove all global sync'd commands
            ctx.bot.tree.clear_commands(guild=None)
            await ctx.bot.tree.sync()
            await ctx.send("Cleared all global commands.")
            return
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


bot.run(token)
