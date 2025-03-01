from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from models.languages import GuildLanguage

config = dotenv_values(".env")

@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.default_permissions(administrator=True)
class GuildLangCog(commands.GroupCog, name='language'):
    def __init__(self, bot):
        self.bot = bot


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


    @app_commands.command(name='set', description='Set the language the bot notifications use to your choice.')
    @app_commands.describe(language="Type your language.")
    @app_commands.checks.cooldown(1, 300, key=lambda i: (i.guild_id, i.user.id))
    async def set_language(self, interaction: discord.Interaction, language: str):
        if language is None:
            language = "English"
        lang_convert = {
            'Български': 'bg',
            'Hrvatski': 'hr',
            'Čeština': 'cs',
            'Dansk': 'da',
            'Nederlands': 'nl',
            'English': 'en',
            'Suomi': 'fi',
            'Français': 'fr',
            'Deutsch': 'de',
            'Ελληνικά': 'el',
            'हिन्दी': 'hi',
            'Magyar': 'hu',
            'Indonesia': 'id',
            'Italiano': 'it',
            '日本語': 'ja',
            '한국어': 'ko',
            'Lietuvių': 'lt',
            'Norsk': 'no',
            'Polski': 'pl',
            'Português': 'pt',
            'Română': 'ro',
            'Русский': 'ru',
            'Español': 'es',
            'Español (Latinoamérica)': 'es',
            'Svenska': 'sv-se',
            'ไทย': 'th',
            'Türkçe': 'tr',
            'Українська': 'uk',
            'Tiếng Việt': 'vi',
            '中文 (简体)': 'zh-cn',
            '中文 (繁體)': 'zh-tw'
        }
        await interaction.response.defer(ephemeral=True)
        lang = lang_convert[language]
        async with self.bot.engine.begin() as conn:
            insert_stmt = insert(GuildLanguage).values(guild_id=interaction.guild_id, lang=lang, added_by=interaction.user.id)
            update = insert_stmt.on_conflict_do_update(constraint='guild_lang_unique_guildid', set_={'lang': lang, 'added_by': interaction.user.id})
            await conn.execute(update)
        return await interaction.followup.send(f"Language set to `{language}` for this guild.")

    @set_language.autocomplete('language')
    async def language_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        languages = [
            'Български',    # Bulgarian (in Bulgarian)
            'Hrvatski',     # Croatian (in Croatian)
            'Čeština',      # Czech (in Czech)
            'Dansk',        # Danish (in Danish)
            'Nederlands',   # Dutch (in Dutch)
            'English',      # English (in English)
            'Suomi',        # Finnish (in Finnish)
            'Français',     # French (in French)
            'Deutsch',      # German (in German)
            'Ελληνικά',     # Greek (in Greek)
            'हिन्दी',          # Hindi (in Hindi)
            'Magyar',       # Hungarian (in Hungarian)
            'Indonesia',    # Indonesian (in Indonesian)
            'Italiano',     # Italian (in Italian)
            '日本語',        # Japanese (in Japanese)
            '한국어',        # Korean (in Korean)
            'Lietuvių',     # Lithuanian (in Lithuanian)
            'Norsk',        # Norwegian (in Norwegian)
            'Polski',       # Polish (in Polish)
            'Português',    # Portuguese (in Portuguese)
            'Română',       # Romanian (in Romanian)
            'Русский',      # Russian (in Russian)
            'Español',      # Spanish (in Spanish)
            'Español (Latinoamérica)'  # Spanish (Latin American)
            'Svenska',      # Swedish (in Swedish)
            'ไทย',          # Thai (in Thai)
            'Türkçe',       # Turkish (in Turkish)
            'Українська',   # Ukrainian (in Ukrainian)
            'Tiếng Việt',   # Vietnamese (in Vietnamese)
            '中文 (简体)',    # Chinese Simplified (in Chinese)
            '中文 (繁體)'     # Chinese Traditional (in Chinese)
            ]
        return [app_commands.Choice(name=lang, value=lang) for lang in languages if current.lower() in lang.lower()][0:24]
    

    @app_commands.command(name='remove', description='Set the language the bot notifications use to the server default.')
    @app_commands.checks.cooldown(1, 300, key=lambda i: (i.guild_id, i.user.id))
    async def remove_language(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with self.bot.engine.begin() as conn:
            delete_stmt = delete(GuildLanguage).filter_by(guild_id=interaction.guild_id)
            await conn.execute(delete_stmt)
        return await interaction.followup.send("Removed any set language for this guild.")
        


async def setup(bot: commands.Bot):
    await bot.add_cog(GuildLangCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(GuildLangCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")