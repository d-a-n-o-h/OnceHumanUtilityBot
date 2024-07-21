import os
import datetime

import asqlite
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import ExtensionAlreadyLoaded
from dotenv import dotenv_values

config = dotenv_values(".env")
utc = datetime.timezone.utc
db_name = config["DATABASE"]


def me_only(interaction: discord.Interaction) -> bool:
    return interaction.user.id == int(config["MY_USER_ID"])

MY_GUILD_ID = discord.Object(int(config["TESTING_GUILD_ID"]))

class UtilsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='utility', description='Utility command for testing.')
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def utility_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("Utility.")
            


    @app_commands.command(name='reload', description='Reloads the cogs.')
    @app_commands.describe(cog="The cog to be reloaded.")
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def reload(self, interaction: discord.Interaction, cog: str):
        if os.path.exists(f"cogs/{cog.lower()}.py"):
            try:
                await self.bot.reload_extension(f"cogs.{cog.lower()}")
                await interaction.response.send_message(f"Reloaded `{cog.upper()}` cog.", ephemeral=True, delete_after=10)
            except Exception as e:
                await interaction.response.send_message(f"Error reloading `{cog.upper()}` cog.: {e}", ephemeral=True)


    @app_commands.command(name='reloadall', description='Reloads all the cogs, starts cogs that aren\'t loaded.')
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def reloadall(self, interaction: discord.Interaction):
        for subdir, _, files in os.walk("cogs"):
            files = [
                file for file in files if file.endswith(".py") and "template" not in file
            ]
            for file in files:
                if len(subdir.split("cogs\\")) >= 2:
                    try:
                        sub = subdir.split("cogs\\")[1]
                        await self.bot.load_extension(f"cogs.{sub}.{file[:-3]}")
                        await interaction.response.send_message(f"Loaded `cogs.{sub}.{file[:-3]}` cog.", ephemeral=True, delete_after=10)
                    except ExtensionAlreadyLoaded:
                        sub = subdir.split("cogs\\")[1]
                        await self.bot.reload_extension(f"cogs.{sub}.{file[:-3]}")
                        await interaction.response.send_message(f"Reloaded `cogs.{sub}.{file[:-3]}` cog.", ephemeral=True, delete_after=10)
                else:
                    try:
                        await self.bot.load_extension(f"{subdir}.{file[:-3]}")
                        await interaction.response.send_message(f"Loaded `{subdir}.{file[:-3]}` cog.", ephemeral=True, delete_after=10)
                    except ExtensionAlreadyLoaded:
                        await self.bot.reload_extension(f"{subdir}.{file[:-3]}")
                        await interaction.response.send_message(f"Reloaded `{subdir}.{file[:-3]}` cog.", ephemeral=True, delete_after=10)


    @app_commands.command(name='load', description='Loads the specified cog.')
    @app_commands.describe(cog="The cog to be loaded.")
    @app_commands.guild_install()
    @app_commands.check(me_only)
    @app_commands.guilds(MY_GUILD_ID)
    async def load(self, interaction: discord.Interaction, cog: str):
        try:
            await self.bot.load_extension(f"cogs.{cog}")
            await interaction.response.send_message(f"Loaded `{cog.upper()}` cog.", ephemeral=True, delete_after=10)
        except Exception as e:
            await interaction.response.send_message(f"Error loading `{cog.upper()}` cog.\n{e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilsCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(UtilsCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")