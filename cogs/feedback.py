import traceback
from typing import Final, Optional

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from languages import LANGUAGES
from models.languages import GuildLanguage
from translations import TRANSLATIONS


class Feedback(discord.ui.Modal, title='Feedback/Bug Report'):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot: Final[commands.Bot] = bot

    feedback_type = discord.ui.TextInput(
        label='Feedback or Bug?',
        style=discord.TextStyle.short,
        placeholder='Please enter only "Feedback" or "Bug" without quotes.',
        required=True
    )
    feedback = discord.ui.TextInput(
        label='Enter feedback/bug report:',
        style=discord.TextStyle.long,
        placeholder='Type your feedback/bug report here and be as descriptive as possible...',
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        dest = await self.get_language(interaction.guild)
        if self.feedback_type.value.lower() == 'feedback' or self.feedback_type.value.lower() == 'bug':
            feedback_forum: discord.ForumChannel = self.bot.get_channel(int(config['FEEDBACK_CHAN']))  # type: ignore
            if self.feedback_type.value.lower() == 'feedback':
                post_tag = [tag for tag in feedback_forum.available_tags if "feedback" in tag.name.lower()]
            elif self.feedback_type.value.lower() == 'bug':
                post_tag = [tag for tag in feedback_forum.available_tags if "bug" in tag.name.lower()]
            feedback_embed = discord.Embed(title=f"Anonymous {self.feedback_type.value.capitalize()} Report")
            feedback_embed.description = self.feedback.value
            await feedback_forum.create_thread(name=f'{self.feedback_type.value.capitalize()} Report', applied_tags=post_tag, embed=feedback_embed, allowed_mentions=discord.AllowedMentions.none())
            await interaction.response.send_message(content=TRANSLATIONS[dest]['feedback_response'].format(self.feedback_type.value.lower(), interaction.user.mention, self.feedback.value), ephemeral=True, delete_after=60, suppress_embeds=True)
        else:
            await interaction.response.send_message(content=TRANSLATIONS[dest]['feedback_wrong_choice'].format("Feedback", "Bug"), ephemeral=True, delete_after=30)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        dest = await self.get_language(interaction.guild)
        traceback.print_exception(type(error), error, error.__traceback__)
        await interaction.response.send_message(TRANSLATIONS[dest]['feedback_error'].format(error), ephemeral=True)


class FeedbackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    @app_commands.command(name='feedback', description='Open a form to provide feedback/a bug report about the bot.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.cooldown(1, 1800, key=lambda i: (i.guild_id, i.user.id))
    async def feedback_report(self, interaction: discord.Interaction):
        await interaction.response.send_modal(Feedback(self.bot))

    @app_commands.command(name='support', description='Send an embed with a link to the support server.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.cooldown(1, 60, key=lambda i: (i.guild_id, i.user.id))
    async def send_support_embed(self, interaction: discord.Interaction):
        dest = await self.get_language(interaction.guild)
        support_embed = discord.Embed(title=f"{interaction.guild.me.display_name} Quick Support", color=discord.Color.og_blurple(), url="https://discord.mycodeisa.meme")
        feedback_cmd = await self.find_cmd(self.bot, cmd='feedback')
        support_embed.add_field(name=TRANSLATIONS[dest]['support_title'], value='https://discord.mycodeisa.meme', inline=False)
        support_embed.add_field(name='', value=TRANSLATIONS[dest]['support_last_update'].format(self.bot.last_update), inline=False)
        support_embed.add_field(name='', value=TRANSLATIONS[dest]['support_feedback'].format(feedback_cmd.mention), inline=False)
        support_embed.add_field(name='', value=TRANSLATIONS[dest]['support_reload'], inline=False)
        support_embed.add_field(name='', value=TRANSLATIONS[dest]['support_permissions'], inline=False)
        support_embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await interaction.response.send_message(embed=support_embed, delete_after=120, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(FeedbackCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(FeedbackCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")