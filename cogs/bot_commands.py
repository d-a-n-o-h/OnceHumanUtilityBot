import datetime

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from googletrans import Translator
from sqlalchemy import select

from languages import LANGUAGES
from models.deviant import Deviants
from translations import TRANSLATIONS

utc = datetime.timezone.utc
config = dotenv_values(".env")


class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()


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
    
    
    @app_commands.command(name='search_deviant', description='Search the database for a deviant.')
    @app_commands.describe(dev_name='The ENGLISH name of the deviant you are searching for.  Less is more.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def search_deviant(self, interaction: discord.Interaction, dev_name: str):
        dest = LANGUAGES.get(str(interaction.guild_locale).lower())
        if dest is None:
            dest = 'en'
        async with self.bot.engine.begin() as conn:
            deviant = await conn.execute(select(Deviants).filter(Deviants.name.ilike(f"%{dev_name}%")))
            deviant = deviant.first()
        if deviant is not None:
            dev_embed = discord.Embed(title=self.translator.translate(str(deviant.name), dest=dest).text, description=self.translator.translate(str(deviant.sub_type), dest=dest).text)
            try:
                color_dict = {
                    'combat': discord.Color.red(),
                    'crafting': discord.Color.blue(),
                    'gadget': discord.Color.green(),
                    'territory': discord.Color.orange()
                    }
                dev_embed.color = color_dict[deviant.sub_type.split(" – ")[0].lower()]
            except:
                dev_embed.color = discord.Color.dark_grey()
            dev_embed.add_field(name=TRANSLATIONS[dest]['deviant_locations'], value=self.translator.translate(str(deviant.locations), dest=dest).text, inline=False)
            dev_embed.add_field(name=TRANSLATIONS[dest]['deviant_effects'], value=self.translator.translate(str(deviant.effect), dest=dest).text, inline=False)
            dev_embed.add_field(name=TRANSLATIONS[dest]['deviant_happiness'], value=self.translator.translate(str(deviant.happiness), dest=dest).text, inline=False)
            dev_embed.set_thumbnail(url=deviant.img_url)
            return await interaction.response.send_message(embed=dev_embed, delete_after=60)
        else:
            return await interaction.response.send_message(content=TRANSLATIONS[dest]['deviant_error'].format(dev_name), ephemeral=True, delete_after=30)


async def setup(bot: commands.Bot):
    await bot.add_cog(CommandsCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(CommandsCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")