import datetime
import sys
import traceback
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from googletrans import Translator  # type: ignore
from sqlalchemy import delete, select  # type: ignore
from sqlalchemy.dialects.postgresql import insert  # type: ignore
from sqlalchemy.ext.asyncio import create_async_engine  # type: ignore

from languages import LANGUAGES
from modals.channels import ReportingChannel
from modals.deviant import Deviants

utc = datetime.timezone.utc
config = dotenv_values(".env")

if config["DATABASE_STRING"]:
    engine = create_async_engine(config["DATABASE_STRING"])
else:
    print("Please set the DATABASE_STRING value in the .env file and restart the bot.")
    sys.exit(1)

class Feedback(discord.ui.Modal, title='Feedback/Bug Report'):
        def __init__(self, bot):
            super().__init__(timeout=300)
            self.bot = bot

        # Our modal classes MUST subclass `discord.ui.Modal`,
        # but the title can be whatever you want.

        # This will be a short input, where the user can enter their name
        # It will also have a placeholder, as denoted by the `placeholder` kwarg.
        # By default, it is required and is a short-style input which is exactly
        # what we want.

        # This is a longer, paragraph style input, where user can submit feedback
        # Unlike the name, it is not required. If filled out, however, it will
        # only accept a maximum of 300 characters, as denoted by the
        # `max_length=300` kwarg.
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
            if self.feedback_type.value.lower() == 'feedback' or self.feedback_type.value.lower() == 'bug':
                feedback_forum: discord.ForumChannel = self.bot.get_channel(int(config['FEEDBACK_CHAN']))  # type: ignore
                if self.feedback_type.value.lower() == 'feedback':
                    post_tag = [tag for tag in feedback_forum.available_tags if "feedback" in tag.name.lower()]
                elif self.feedback_type.value.lower() == 'bug':
                    post_tag = [tag for tag in feedback_forum.available_tags if "bug" in tag.name.lower()]
                feedback_embed = discord.Embed(title=f"Anonymous {self.feedback_type.value.capitalize()} Report")
                feedback_embed.description = self.feedback.value
                await feedback_forum.create_thread(name=f'{self.feedback_type.value.capitalize()} Report', applied_tags=post_tag, embed=feedback_embed, allowed_mentions=discord.AllowedMentions.none())
                await interaction.response.send_message(f'Thank you for the {self.feedback_type.value.lower()} report, {interaction.user.mention}!\n\nSent:\n`{self.feedback.value}`', ephemeral=True, delete_after=60)
            else:
                await interaction.response.send_message('Please only enter `Feedback` or `Bug` into the feedback type box.', ephemeral=True, delete_after=30)

        async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
            await interaction.response.send_message(f'Oops! Something went wrong.\n{error}', ephemeral=True)

            # Make sure we know what the error actually is
            traceback.print_exception(type(error), error, error.__traceback__)  

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
            for child in cmd_group.options:  # type: ignore
                if child.name.lower() == cmd.lower():
                    return child
                
    
    @app_commands.command(name='feedback', description='Open a form to provide feedback/a bug report about the bot.')
    @app_commands.guild_install()
    @app_commands.checks.cooldown(1, 1800, key=lambda i: (i.guild_id, i.user.id))
    async def feedback_report(self, interaction: discord.Interaction):
        await interaction.response.send_modal(Feedback(self.bot))
                
    
    @app_commands.command(name='search_deviant', description='Search the database for a deviant.')
    @app_commands.describe(dev_name='The name of the deviant you are searching for.  Less is more.')
    @app_commands.guild_install()
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def search_deviant(self, interaction: discord.Interaction, dev_name: str):
        dev_name = dev_name.lower()
        dest = LANGUAGES.get(str(interaction.guild_locale).lower())
        async with engine.begin() as conn:
            deviant = await conn.execute(select(Deviants).filter(Deviants.name.ilike(f"%{dev_name}%")))
            deviant = deviant.one_or_none()
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
            dev_embed.add_field(name=self.translator.translate('Locations', dest=dest).text, value=self.translator.translate(str(deviant.locations), dest=dest).text, inline=False)
            dev_embed.add_field(name=self.translator.translate('Effect', dest=dest).text, value=self.translator.translate(str(deviant.effect), dest=dest).text, inline=False)
            dev_embed.add_field(name=self.translator.translate('Happiness', dest=dest).text, value=self.translator.translate(str(deviant.happiness), dest=dest).text, inline=False)
            dev_embed.set_thumbnail(url=deviant.img_url)
            return await interaction.response.send_message(embed=dev_embed, delete_after=60)
        else:
            return await interaction.response.send_message(self.translator.translate(f"Unable to locate any deviant containing `{dev_name}`.  Please try your search again.", dest=dest), ephemeral=True, delete_after=30)


    @app_commands.command(name='test_alert', description='Sends a test alert to your channel.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild_id, i.user.id))
    async def test_alert_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        dest = LANGUAGES.get(str(interaction.guild_locale).lower())
        async with engine.begin() as conn:
            this_guild = await conn.execute(select(ReportingChannel.channel_id,ReportingChannel.role_id).filter_by(guild_id=interaction.guild_id))
            this_guild = this_guild.one_or_none()
        await engine.dispose(close=True)
        if not this_guild:
            return await interaction.followup.send(content=self.translator.translate('No channel set!', dest=dest).text, wait=True)
        (chan_id, role_id) = this_guild
        chan: discord.TextChannel = interaction.guild.get_channel(chan_id) # type: ignore
        role: discord.Role = interaction.guild.get_role(role_id) # type: ignore
        test_embed = discord.Embed(color=discord.Color.blurple(),title=self.translator.translate('Test Alert', dest=dest).text)
        setup_cmd = await self.find_cmd(self.bot, cmd='setup')
        if chan and not type(chan) == discord.TextChannel:
            async with engine.begin() as conn:
                await conn.execute(delete(ReportingChannel).filter_by(guild_id=interaction.guild_id))
            await engine.dispose(close=True)
            setup_cmd = await self.find_cmd(self.bot, cmd='setup')
            return await interaction.followup.send(content=self.translator.translate(f"The channel you previous selected was not a text/announcement channel.\nYour settings have been removed from the database.\nPlease {setup_cmd.mention} your channel again.", dest=dest).text)  # type: ignore
        test_embed.add_field(name='', value=self.translator.translate(f"Use {setup_cmd.mention} to change the channel or change/add a role to ping.", dest=dest).text, inline=False) # type: ignore
        try:
            await chan.send(content=f"{role.mention if role else ''}", embed=test_embed)
        except:
            async with engine.begin() as conn:
                await conn.execute(delete(ReportingChannel).filter_by(guild_id=interaction.guild_id))
            await engine.dispose(close=True)
            setup_cmd = await self.find_cmd(self.bot, cmd='setup')
            return await interaction.followup.send(content=self.translator.translate(f"The bot is not able to send messages/view the channel in the channel you have chosen, {chan.mention}.\nPlease edit the channel settings by right clicking the channel name and make sure the bot or it's role has View Channel and Send Messages set to the ✅ (green check) and try again.\nIf you need assistance, please join the support server: https://discord.mycodeisa.meme.", dest=dest).text)
        await interaction.followup.send(content=self.translator.translate("Sent test embed to your channel.", dest=dest).text, wait=True)
    
    @app_commands.command(name='check', description='Shows which channel/role the bot will send alerts to.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def check_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        dest = LANGUAGES.get(str(interaction.guild_locale).lower())
        async with engine.begin() as conn:
            guild_data = await conn.execute(select(ReportingChannel.channel_id,ReportingChannel.role_id).filter_by(guild_id=interaction.guild_id))
            guild_data = guild_data.one_or_none()
        await engine.dispose(close=True)
        if guild_data:
            if guild_data[1]:
                role = interaction.guild.get_role(int(guild_data[1])) # type: ignore
            else:
                role = None
            channel = interaction.guild.get_channel(int(guild_data[0])) # type: ignore
            if channel and not type(channel) == discord.TextChannel:
                async with engine.begin() as conn:
                    await conn.execute(delete(ReportingChannel).filter_by(guild_id=interaction.guild_id))
                await engine.dispose(close=True)
                setup_cmd = await self.find_cmd(self.bot, cmd='setup')
                return await interaction.followup.send(self.translator.translate(f"This bot only supports text/announcement channels.\nPlease {setup_cmd.mention} your channel again.", dest=dest).text) # type: ignore
            if not channel:
                async with engine.begin() as conn:
                    await conn.execute(delete(ReportingChannel).filter_by(guild_id=interaction.guild_id))
                await engine.dispose(close=True)
                setup_cmd = await self.find_cmd(self.bot, cmd='setup')
                return await interaction.followup.send(self.translator.translate(f"Channel not found.\nPlease {setup_cmd.mention} your channel again.", dest=dest).text) # type: ignore

            return await interaction.followup.send(content=self.translator.translate(f"Alerts go to {channel.mention if channel else '`None`'}.\nRole notified is {role.mention if role else '`None`'}.", dest=dest).text, wait=True)
        else:
            setup_cmd = await self.find_cmd(self.bot, cmd="setup")
            return await interaction.followup.send(content=self.translator.translate(f"You have not {setup_cmd.mention} your guild yet.", dest=dest).text, wait=True) # type: ignore
        
    
    @app_commands.command(name='remove_data', description='Remove your guild and channel ID from the database.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 3600, key=lambda i: (i.guild_id, i.user.id))
    async def remove_data(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        dest = LANGUAGES.get(str(interaction.guild_locale).lower())
        async with engine.begin() as conn:
            await conn.execute(delete(ReportingChannel).filter_by(guild_id=interaction.guild_id))
        await engine.dispose(close=True)
        return await interaction.followup.send(content=self.translator.translate("Your guild ID and channel ID have been removed from the `channels` database.\n## Your guild will no longer get alerts.", dest=dest).text)
        

    @app_commands.command(name='setup', description='Basic setup command for the bot.')
    @app_commands.describe(output_channel="The text channel you want notifications in.")
    @app_commands.describe(role_to_mention="The role you want mentioned in the alert. Blank = None")
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    async def output_setup(self, interaction: discord.Interaction, output_channel: discord.TextChannel, role_to_mention: Optional[discord.Role] = None):
        await interaction.response.defer(ephemeral=True)
        dest = LANGUAGES.get(str(interaction.guild_locale).lower())
        if not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel:
            return await interaction.followup.send(content=self.translator.translate(f"The bot is not able to send messages/view the channel in the channel you have chosen, {output_channel.mention}.\nPlease edit the channel settings by right clicking the channel name and make sure the bot or it's role has `View Channel` and `Send Messages` set to the ✅ (green check).\nIf you need assistance, please join the support server: https://discord.mycodeisa.meme.", dest=dest).text, suppress_embeds=True)
        if not type(output_channel) == discord.TextChannel:
            setup_cmd = await self.find_cmd(self.bot, cmd='setup')
            return await interaction.followup.send(content=self.translator.translate(f"This bot only supports text/announcement channels.\nPlease {setup_cmd.mention} your channel again.", dest=dest).text) # type: ignore
        if role_to_mention:
            role_id = role_to_mention.id
        else:
            role_id = None
        async with engine.begin() as conn:
            insert_stmt = insert(ReportingChannel).values(guild_id=interaction.guild_id,channel_id=output_channel.id,role_id=role_id)
            update = insert_stmt.on_conflict_do_update(constraint='channels_unique_guildid', set_={'role_id': role_id})
            await conn.execute(update)
        await engine.dispose(close=True)
        await output_channel.send(self.translator.translate(f"{interaction.user.mention}, this channel is where respawn alerts will be sent!", dest=dest).text)
        return await interaction.followup.send(content=self.translator.translate(f"Your output channel has been set to {output_channel.mention}!\nThe role that will be mentioned is {role_to_mention.mention if role_to_mention else '`None`'}.\nIf you do not get an alert when you expect it, please join the support server and let me know.  https://discord.mycodeisa.meme", dest=dest).text, suppress_embeds=True)
        


async def setup(bot: commands.Bot):
    await bot.add_cog(CommandsCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(CommandsCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")