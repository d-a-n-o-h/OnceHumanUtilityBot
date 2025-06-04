import datetime
from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from googletrans import Translator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from languages import LANGUAGES
from models.channels import PremiumMessage
from models.deviant import Deviants
from models.languages import GuildLanguage
from translations import TRANSLATIONS

config = dotenv_values(".env")

def me_only(interaction: discord.Interaction) -> bool:
    return interaction.user.id == int(config["MY_USER_ID"])

class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()
        self.alert_types_list = ['cargo', 'crate', 'purification', 'controller', 'sproutlet', 'medics', 'lunar']

    async def get_language(self, guild: discord.Guild) -> str:
        async with self.bot.engine.begin() as conn:
            lang = await conn.execute(select(GuildLanguage.lang).filter_by(guild_id=guild.id))
            lang = lang.one_or_none()
        if lang is not None:
            lang = lang.lang
        if lang is None:
            lang = LANGUAGES.get(str(guild.preferred_locale).lower(), 'en')
        return lang

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

    async def check_if_premium(self, guild: discord.Guild):
        sku_list = list()
        is_premium = False
        skus = await self.bot.fetch_skus()
        for sku in skus:
            if sku.id == 1372073760546488391:
                sku_list.append(sku)
        ent_list = [ent async for ent in self.bot.entitlements(guild=guild,skus=sku_list,exclude_ended=True)]
        if len(ent_list) != 0:
            is_premium = True
        return is_premium

    async def alert_type_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        return [app_commands.Choice(name=alert_type, value=alert_type.lower()) for alert_type in self.alert_types_list if current.lower() in alert_type.lower()]

    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(alert_type=alert_type_autocomplete)
    @app_commands.command(name='premium_message', description='Set your guild\'s custom alert messages.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.cooldown(1,5,key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(custom_message="Use %time% to insert the usual timestamp in your message.")
    async def set_premium_messages(self, interaction: discord.Interaction, alert_type: str, custom_message: str):
        custom_message = custom_message.replace(";", ',').replace("\\n", " | ").replace("\\t", " | ").strip()
        is_premium = await self.check_if_premium(interaction.guild)
        if alert_type.lower() not in self.alert_types_list:
            return await interaction.response.send_message("Please choose a valid alert type from the list provided.", ephemeral=True, delete_after=30)
        if not is_premium:
            return await interaction.response.send_message("Please purchase a premium subscription found in the bot's store to use this feature.", ephemeral=True, delete_after=60)
        await interaction.response.defer()
        async with self.bot.engine.begin() as conn:
                premium_message_insert = insert(PremiumMessage).values(guild_id=interaction.guild_id,alert_type=alert_type,message=custom_message)
                premium_message_update = premium_message_insert.on_conflict_do_update(constraint='premium_messages_guild_alert_constraint', set_={'message': custom_message})
                await conn.execute(premium_message_update)
        dest = await self.get_language(interaction.guild)
        time_now = discord.utils.utcnow()
        generic_timestamp = int(datetime.datetime.timestamp(time_now))
        embed_titles = {
            'cargo': TRANSLATIONS[dest]['cargo_embed_title'],
            'crate': TRANSLATIONS[dest]['crate_embed_title'],
            'purification': TRANSLATIONS[dest]['purification_embed_title'],
            'controller': TRANSLATIONS[dest]['controller_embed_title'],
            'sproutlet': TRANSLATIONS[dest]['sproutlet_embed_title'],
            'medics': TRANSLATIONS[dest]['medics_embed_title'],
            'lunar': TRANSLATIONS[dest]['lunar_embed_title'],
            }
        reset_embed = discord.Embed(color=discord.Color.blurple())
        reset_embed.title = embed_titles.get(alert_type)
        if alert_type == 'cargo':
            cargo_timestamp = int(datetime.datetime.timestamp(time_now + datetime.timedelta(minutes=5)))
            reset_embed.add_field(name='', value=custom_message.replace('%time%', f'<t:{cargo_timestamp}:R>'), inline=False)
        elif alert_type == 'crate':
            crate_timestamp = int(datetime.datetime.timestamp(time_now.replace(minute=0, second=0, microsecond=0)))
            reset_embed.add_field(name='', value=custom_message.replace('%time%', f'<t:{crate_timestamp}:t>'), inline=False)
            reset_embed.set_footer(text=TRANSLATIONS[dest]['crate_respawn_footer'])
        elif alert_type == 'medics':
            medics_timestamp = int(datetime.datetime.timestamp(time_now.replace(minute=0, second=0, microsecond=0)))
            reset_embed.add_field(name='', value=custom_message.replace('%time%', f'<t:{medics_timestamp}:R>'), inline=False)
            reset_embed.set_footer(text=TRANSLATIONS[dest]['medics_respawn_footer'])
        else:
            reset_embed.add_field(name='', value=custom_message.replace('%time%', f'<t:{generic_timestamp}:R>'), inline=False)
        await interaction.followup.send(content=f"You have set the custom message for `{alert_type}` alerts.\nExample alert:", embed=reset_embed)

    
    @app_commands.command(name='search_deviant', description='Search the database for a deviant.')
    @app_commands.describe(dev_name='The ENGLISH name of the deviant you are searching for.  Less is more.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
    async def search_deviant(self, interaction: discord.Interaction, dev_name: str):
        dest = await self.get_language(interaction.guild)
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