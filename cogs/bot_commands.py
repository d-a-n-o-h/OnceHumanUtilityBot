import datetime
import sys
import traceback
from typing import Final, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from googletrans import Translator
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import create_async_engine

from languages import LANGUAGES
from translations import TRANSLATIONS
from modals.channels import CargoScrambleChannel, CrateRespawnChannel, CrateMutes, CargoMutes
from modals.deviant import Deviants

utc = datetime.timezone.utc
config = dotenv_values(".env")

if config["DATABASE_STRING"]:
    engine: Final = create_async_engine(config["DATABASE_STRING"])
else:
    print("Please set the DATABASE_STRING value in the .env file and restart the bot.")
    sys.exit(1)

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
            dest = LANGUAGES.get(str(interaction.guild_locale).lower())
            if dest is None:
                dest = 'en'
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
                await interaction.response.send_message(content=TRANSLATIONS[dest]['feedback_wrong_choice'], ephemeral=True, delete_after=30)

        async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
            dest = LANGUAGES.get(str(interaction.guild_locale).lower())
            if dest is None:
                dest = 'en'
            await interaction.response.send_message(TRANSLATIONS[dest]['feedback_error'].format(error), ephemeral=True)

            traceback.print_exception(type(error), error, error.__traceback__)  

class CrateMuteSelect(discord.ui.Select):
    def __init__(self):
        hours = [0,4,8,12,16,20]
        options = []
        options.append(discord.SelectOption(label="None", value="None", default=False))
        for hour in hours:
            hour_opt = discord.SelectOption(label=f"{hour:02}:00 UTC", value=hour, default=False)
            options.append(hour_opt)
        super().__init__(placeholder="Pick the hour(s) you want to mute.", max_values=6, options=options)

    async def callback(self, interaction: discord.Interaction):
        if len(self.values) == 1 and self.values[0] == "None":
            async with engine.begin() as conn:
                insert_stmt = insert(CrateMutes).values(guild_id=interaction.guild_id,zero=False,four=False,eight=False,twelve=False,sixteen=False,twenty=False)
                update_stmt = insert_stmt.on_conflict_do_update(constraint='crate_mutes_unique_guildid', set_={'zero': False, 'four': False, 'eight': False, 'twelve': False, 'sixteen': False, 'twenty': False})
                await conn.execute(update_stmt)
            await engine.dispose(close=True)
            return await interaction.response.send_message("No mutes set or all mutes removed.", delete_after=60, ephemeral=True)
        db_dict = {0: "zero", 4: "four", 8: "eight", 12: "twelve", 16: "sixteen", 20: "twenty"}
        db_convert = {'zero': False, 'four': False, 'eight': False, 'twelve': False, 'sixteen': False, 'twenty': False, }
        muted_values = []
        for value in self.values:
            if value == "None":
                continue
            muted_values.append(f"`{int(value):02}:00`")
            db_convert[db_dict[int(value)]] = True
        muted_values.sort()
        async with engine.begin() as conn:
            insert_stmt = insert(CrateMutes).values(guild_id=interaction.guild_id,zero=db_convert['zero'],four=db_convert['four'],eight=db_convert['eight'],twelve=db_convert['twelve'],sixteen=db_convert['sixteen'],twenty=db_convert['twenty'])
            update_stmt = insert_stmt.on_conflict_do_update(constraint='crate_mutes_unique_guildid', set_={'zero': db_convert['zero'], 'four': db_convert['four'], 'eight': db_convert['eight'], 'twelve': db_convert['twelve'], 'sixteen': db_convert['sixteen'], 'twenty': db_convert['twenty'], })
            await conn.execute(update_stmt)
        await engine.dispose(close=True)
        await interaction.response.send_message(f"You have muted {', '.join(muted_values)} UTC.", delete_after=60, ephemeral=True)

class CrateMuteView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(CrateMuteSelect())


class CargoMuteSelect(discord.ui.Select):
    def __init__(self):
        hours = [12,15,18,22]
        options = []
        options.append(discord.SelectOption(label="None", value="None", default=False))
        for hour in hours:
            if hour == 18:
                hour_opt = discord.SelectOption(label=f"{hour:02}:30 UTC", value=hour, default=False)
            else:
                hour_opt = discord.SelectOption(label=f"{hour:02}:00 UTC", value=hour, default=False)
            options.append(hour_opt)
        super().__init__(placeholder="Pick the hour(s) you want to mute.", max_values=4, options=options)

    async def callback(self, interaction: discord.Interaction):
        if len(self.values) == 1 and self.values[0] == "None":
            async with engine.begin() as conn:
                insert_stmt = insert(CargoMutes).values(guild_id=interaction.guild_id,twelve=False,fifteen=False,twenty_two=False,eighteen_thirty=False)
                update_stmt = insert_stmt.on_conflict_do_update(constraint='cargo_mutes_unique_guildid', set_={'twelve': False, 'fifteen': False, 'twenty_two': False, 'eighteen_thirty': False})
                await conn.execute(update_stmt)
            await engine.dispose(close=True)
            return await interaction.response.send_message("No mutes set or all mutes removed.", delete_after=60, ephemeral=True)
        db_dict = {12: 'twelve', 15: 'fifteen', 18: 'eighteen_thirty', 22: 'twenty_two'}
        db_convert = {'twelve': False, 'fifteen': False, 'eighteen_thirty': False, 'twenty_two': False}
        muted_values = []
        for value in self.values:
            if value == "None":
                continue
            if value == 18:
                muted_values.append(f"`{int(value):02}:30`")
            else:
                muted_values.append(f"`{int(value):02}:00`")
            db_convert[db_dict[int(value)]] = True
        muted_values.sort()
        async with engine.begin() as conn:
            insert_stmt = insert(CargoMutes).values(guild_id=interaction.guild_id,twelve=db_convert['twelve'],fifteen=db_convert['fifteen'],twenty_two=db_convert['twenty_two'],eighteen_thirty=db_convert['eighteen_thirty'])
            update_stmt = insert_stmt.on_conflict_do_update(constraint='cargo_mutes_unique_guildid', set_={'twelve': db_convert['twelve'], 'fifteen': db_convert['fifteen'], 'twenty_two': db_convert['twenty_two'], 'eighteen_thirty': db_convert['eighteen_thirty']})
            await conn.execute(update_stmt)
        await engine.dispose(close=True)
        await interaction.response.send_message(f"You have muted {', '.join(muted_values)} UTC.", delete_after=60, ephemeral=True)

class CargoMuteView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(CargoMuteSelect())


class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()

    async def try_channel(self, id: int) -> discord.TextChannel | None:
        try:
            return self.bot.get_channel(id) or await self.bot.fetch_channel(id)
        except discord.NotFound:
            return None

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


    @app_commands.command(name='support', description='Send an embed with a link to the support server.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.cooldown(1, 3600, key=lambda i: (i.guild_id, i.user.id))
    async def send_support_embed(self, interaction: discord.Interaction):
        support_embed = discord.Embed(title=f"{interaction.guild.me.display_name} Quick Support", color=discord.Color.og_blurple(), url="https://discord.mycodeisa.meme") # type: ignore
        feedback_cmd = await self.find_cmd(self.bot, cmd='feedback')
        support_embed.add_field(name='Discord Invite Link', value='https://discord.mycodeisa.meme', inline=False)
        support_embed.add_field(name='', value="-# Last update: <t:1723291200:f>", inline=False)
        support_embed.add_field(name='', value=f"You can send an anonymous feedback or bug report with {feedback_cmd.mention}.", inline=False)
        support_embed.add_field(name='', value='If a command isn\'t working as expected, reload (CTRL+R) or restart Discord.', inline=False)
        support_embed.add_field(name='', value='After that, verify the bot user has the correct permissions for "View Channel" and "Send Messages" marked as ✅ on the channel you are trying to use.')
        support_embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await interaction.response.send_message(embed=support_embed, delete_after=120, ephemeral=True)
                
    
    @app_commands.command(name='feedback', description='Open a form to provide feedback/a bug report about the bot.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.cooldown(1, 1800, key=lambda i: (i.guild_id, i.user.id))
    async def feedback_report(self, interaction: discord.Interaction):
        await interaction.response.send_modal(Feedback(self.bot))
                
    
    @app_commands.command(name='search_deviant', description='Search the database for a deviant.')
    @app_commands.describe(dev_name='The ENGLISH name of the deviant you are searching for.  Less is more.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def search_deviant(self, interaction: discord.Interaction, dev_name: str):
        dest = LANGUAGES.get(str(interaction.guild_locale).lower())
        if dest is None:
            dest = 'en'
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
            dev_embed.add_field(name=TRANSLATIONS[dest]['deviant_locations'], value=self.translator.translate(str(deviant.locations), dest=dest).text, inline=False)
            dev_embed.add_field(name=TRANSLATIONS[dest]['deviant_effects'], value=self.translator.translate(str(deviant.effect), dest=dest).text, inline=False)
            dev_embed.add_field(name=TRANSLATIONS[dest]['deviant_happiness'], value=self.translator.translate(str(deviant.happiness), dest=dest).text, inline=False)
            dev_embed.set_thumbnail(url=deviant.img_url)
            return await interaction.response.send_message(embed=dev_embed, delete_after=60)
        else:
            return await interaction.response.send_message(content=TRANSLATIONS[dest]['deviant_error'].format(dev_name), ephemeral=True, delete_after=30)


    @app_commands.command(name='test_alert', description='Sends a test alert to your channel.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild_id, i.user.id))
    async def test_alert_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        alert_success = list()
        dest = LANGUAGES.get(str(interaction.guild_locale).lower())
        if dest is None:
            dest = 'en'
        async with engine.begin() as conn:
            crate_data = await conn.execute(select(CrateRespawnChannel.channel_id,CrateRespawnChannel.role_id).filter_by(guild_id=interaction.guild_id))
            crate_data = crate_data.one_or_none()
            cargo_data = await conn.execute(select(CargoScrambleChannel.channel_id,CargoScrambleChannel.role_id).filter_by(guild_id=interaction.guild_id))
            cargo_data = cargo_data.one_or_none()
        await engine.dispose(close=True)
        if not crate_data and not cargo_data:
            return await interaction.followup.send(content=TRANSLATIONS[dest]['no_channels_set_alert'], wait=True, ephemeral=True)
        else:
            if crate_data:
                crate_cmd = await self.find_cmd(self.bot, cmd='setup')
                (channel_id, role_id) = crate_data
                output_channel: discord.TextChannel = self.bot.get_channel(channel_id)
                if output_channel is None:
                    msg = await interaction.followup.send(content=f"Crate Respawn output channel not found.  Deleted from the database.", wait=True, ephemeral=True)
                    async with engine.begin() as conn:
                        await conn.execute(delete(CrateRespawnChannel).filter_by(guild_id=interaction.guild_id))
                    await engine.dispose(close=True)
                    await msg.delete(delay=60)
                    return
                role: discord.Role = interaction.guild.get_role(role_id) # type: ignore
                if output_channel and (not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel or not output_channel.permissions_for(output_channel.guild.me).embed_links):
                    await interaction.followup.send(content=TRANSLATIONS[dest]['crate_channel_alert_error'].format(crate_cmd.mention), ephemeral=True)  # type: ignore
                else:
                    crate_embed = discord.Embed(color=discord.Color.blurple(),title=TRANSLATIONS[dest]['test_crate_embed_title'])
                    crate_embed.add_field(name='', value=TRANSLATIONS[dest]['crate_cmd_notify'].format(crate_cmd.mention), inline=False) # type: ignore
                    await output_channel.send(content=f"{role.mention if role else ''}", embed=crate_embed)
                    alert_success.append("Crate Respawn")
            if cargo_data:
                cargo_cmd = await self.find_cmd(self.bot, cmd='cargo_scramble')
                (channel_id, role_id) = cargo_data
                output_channel: discord.TextChannel = self.bot.get_channel(channel_id)
                if output_channel is None:
                    msg = await interaction.followup.send(content=f"Cargo Scramble output channel not found.  Deleted from the database.", wait=True, ephemeral=True)
                    async with engine.begin() as conn:
                        await conn.execute(delete(CargoScrambleChannel).filter_by(guild_id=interaction.guild_id))
                    await engine.dispose(close=True)
                    await msg.delete(delay=60)
                    return
                role: discord.Role = interaction.guild.get_role(role_id) # type: ignore
                if output_channel and (not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel):
                    await interaction.followup.send(content=TRANSLATIONS[dest]['cargo_channel_alert_error'].format(cargo_cmd.mention), ephemeral=True) # type: ignore
                else:
                    cargo_embed = discord.Embed(color=discord.Color.blurple(),title=TRANSLATIONS[dest]['test_cargo_embed_title'])
                    cargo_embed.add_field(name='', value=TRANSLATIONS[dest]['cargo_cmd_notify'].format(cargo_cmd.mention), inline=False) # type: ignore
                    await output_channel.send(content=f"{role.mention if role else ''}", embed=cargo_embed)
                    alert_success.append("Cargo Spawn")
        await interaction.followup.send(content=TRANSLATIONS[dest]['test_alert_success'].format(', '.join(alert_success), 's' if cargo_data is not None and crate_data is not None else ''), wait=True, ephemeral=True)

    
    @app_commands.command(name='crate_mute', description='Mute crate alerts at specific times.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def mute_crate_alerts(self, interaction: discord.Interaction):
        view = CrateMuteView()
        return await interaction.response.send_message(content=f"Pick the hour(s) you want to mute for `WEAPON/GEAR CRATE RESPAWN ALERTS`.\nFind a timezone converter online if you don't know what your local time is in UTC.\nNothing will be selected until you click away from the menu.\nPicking `None` by itself will remove all mutes you have set.\n\n-# This menu is reusable and will delete after 2 minutes.", view=view, delete_after=120, ephemeral=True) # type: ignore


    @app_commands.command(name='cargo_mute', description='Mute cargo alerts at specific times.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def mute_cargo_alerts(self, interaction: discord.Interaction):
        view = CargoMuteView()
        return await interaction.response.send_message(content=f"Pick the hour(s) you want to mute for `CARGO SCRAMBLE SPAWN ALERTS`.\nFind a timezone converter online if you don't know what your local time is in UTC.\nNothing will be selected until you click away from the menu.\nPicking `None` by itself will remove all mutes you have set.\n\n-# This menu is reusable and will delete after 2 minutes.", view=view, delete_after=120, ephemeral=True) # type: ignore
    


    @app_commands.command(name='remove_data', description='Remove your guild and channel ID from the database.')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 3600, key=lambda i: (i.guild_id, i.user.id))
    async def remove_data(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        dest = LANGUAGES.get(str(interaction.guild_locale).lower())
        if dest is None:
            dest = 'en'
        async with engine.begin() as conn:
            await conn.execute(delete(CrateRespawnChannel).filter_by(guild_id=interaction.guild_id))
            await conn.execute(delete(CargoScrambleChannel).filter_by(guild_id=interaction.guild_id))
            await conn.execute(delete(CrateMutes).filter_by(guild_id=interaction.guild_id))
            await conn.execute(delete(CargoMutes).filter_by(guild_id=interaction.guild_id))
        await engine.dispose(close=True)
        return await interaction.followup.send(content=TRANSLATIONS[dest]['remove_data_success'])
        

    @app_commands.command(name='setup', description='Basic setup command for the bot.')
    @app_commands.describe(output_channel="The text/announcement channel you want notifications in.")
    @app_commands.describe(role_to_mention="The role you want mentioned in the alert. Blank = None")
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    async def crate_alert_setup(self, interaction: discord.Interaction, output_channel: discord.TextChannel, role_to_mention: Optional[discord.Role] = None):
        await interaction.response.defer(ephemeral=True)
        dest = LANGUAGES.get(str(interaction.guild_locale).lower())
        if dest is None:
            dest = 'en'
        if not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel or not output_channel.permissions_for(output_channel.guild.me).embed_links:
            return await interaction.followup.send(content=TRANSLATIONS[dest]['crate_channel_alert_error'].format(output_channel.mention), suppress_embeds=True)
        if role_to_mention:
            role_id = role_to_mention.id
        else:
            role_id = None
        async with engine.begin() as conn:
            insert_stmt = insert(CrateRespawnChannel).values(guild_id=interaction.guild_id,channel_id=output_channel.id,role_id=role_id,added_by=interaction.user.id)
            update = insert_stmt.on_conflict_do_update(constraint='craterespawn_channels_unique_guildid', set_={'channel_id': output_channel.id, 'role_id': role_id, 'added_by': interaction.user.id})
            await conn.execute(update)
        await engine.dispose(close=True)
        await output_channel.send(content=TRANSLATIONS[dest]['setup_crate_channel_ping'].format(interaction.user.mention))
        return await interaction.followup.send(content=TRANSLATIONS[dest]['setup_crate_success'].format(output_channel.mention, role_to_mention.mention if role_to_mention else '`None`'), suppress_embeds=True)
    

    @app_commands.command(name='cargo_scramble', description='Setup for Cargo Scramble alerts')
    @app_commands.describe(output_channel="The text/announcement channel you want notifications in.")
    @app_commands.describe(role_to_mention="The role you want mentioned in the alert. Blank = None")
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    async def cargoscramble_alert_setup(self, interaction: discord.Interaction, output_channel: discord.TextChannel, role_to_mention: Optional[discord.Role] = None):
        await interaction.response.defer(ephemeral=True)
        dest = LANGUAGES.get(str(interaction.guild_locale).lower())
        if dest is None:
            dest = 'en'
        if not output_channel.permissions_for(output_channel.guild.me).send_messages or not output_channel.permissions_for(output_channel.guild.me).view_channel or not output_channel.permissions_for(output_channel.guild.me).embed_links:
            return await interaction.followup.send(content=TRANSLATIONS[dest]['cargo_channel_alert_error'].format(output_channel.mention), suppress_embeds=True)
        if not type(output_channel) == discord.TextChannel:
            cargo_cmd = await self.find_cmd(self.bot, cmd='cargo_scramble')
            return await interaction.followup.send(content=TRANSLATIONS[dest]['check_channel_type_error'].format(cargo_cmd.mention)) # type: ignore
        if role_to_mention:
            role_id = role_to_mention.id
        else:
            role_id = None
        async with engine.begin() as conn:
            insert_stmt = insert(CargoScrambleChannel).values(guild_id=interaction.guild_id,channel_id=output_channel.id,role_id=role_id,added_by=interaction.user.id)
            update = insert_stmt.on_conflict_do_update(constraint='cargoscramble_channels_unique_guildid', set_={'channel_id': output_channel.id, 'role_id': role_id, 'added_by': interaction.user.id})
            await conn.execute(update)
        await engine.dispose(close=True)
        await output_channel.send(content=TRANSLATIONS[dest]['setup_cargo_channel_ping'].format(interaction.user.mention))
        return await interaction.followup.send(content=TRANSLATIONS[dest]['setup_cargo_success'].format(output_channel.mention, role_to_mention.mention if role_to_mention else '`None`'), suppress_embeds=True)
        


async def setup(bot: commands.Bot):
    await bot.add_cog(CommandsCog(bot))
    print(f"{__name__[5:].upper()} loaded")


async def teardown(bot: commands.Bot):
    await bot.remove_cog(CommandsCog(bot).qualified_name)
    print(f"{__name__[5:].upper()} unloaded")