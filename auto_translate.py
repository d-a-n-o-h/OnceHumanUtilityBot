from googletrans import Translator
from tqdm import tqdm

from languages import LANGUAGES

translator = Translator()

strings_to_translate = [
    # Embed titles
    {'cargo_embed_title': 'Once Human Cargo Scramble Spawn'},
    {'crate_embed_title': 'Once Human Gear/Weapon Crates Reset'},
    {'purification_embed_title': 'Once Human Purification Weekly Reset'},
    {'controller_embed_title': 'Once Human Controller Weekly Reset'},
    {'sproutlet_embed_title': 'Once Human Sproutlet Reset'},
    {'medics_embed_title': 'Once Human Medics/Trunks Reset'},
    {'lunar_embed_title': 'Once Human Lunar Event Start'},
    {'test_crate_embed_title': 'Weapon/Gear Respawn Test Alert'},
    {'test_cargo_embed_title': 'Cargo Scramble Test Alert'},
    # Cargo
    {'cargo_scramble_alert_message': 'The cargo scramble event has a chance to spawn {}!'},
    {'asian_cargo_scramble_alert_message': '(ASIAN SERVERS) The cargo scramble event has a chance to spawn {}!'},
    {'check_cargo_channel_success': 'Cargo Scramble alerts go to {}.\nRole notified is {}.'},
    {'check_cargo_not_used': 'You have not used {} in your guild yet.'},
    {'setup_cargo_channel_ping': '{}, this channel is where cargo scramble alerts will be sent!'},
    {'setup_cargo_success': 'Your cargo scramble alerts output channel has been set to {}!\nThe role that will be mentioned is {}.\n-# If you do not get an alert when you expect it, please join the support server and let me know.'},
    {'cargo_previous_channel_alert_error': 'The channel you previous selected for cargo scramble spawn alerts was not a text/announcement channel.\nYour settings have been removed from the database.\nPlease {} your channel again.'},
    {'cargo_cmd_notify': 'Use {} to change the channel or change/add a role to ping.'},
    {'cargo_channel_alert_error': '[CARGO] The bot is not able to send messages/view the channel in the channel you have chosen for cargo scramble spawn alerts, {}.\nPlease edit the channel settings by right clicking the channel name and make sure the bot or it\'s role has View Channel, Send Messages, and Embed Links set to the ✅ (green check) and try again.\n-# If you need assistance, please join the support server,'},
    # Crate
    {'crate_respawn_alert_message': 'This is the {} reset announcement.'},
    {'crate_respawn_footer': 'Log out to the main menu and log back in to see the reset crates.'},
    {'check_crate_channel_success': 'Weapon/Gear crate respawn alerts go to {}.\nRole notified is {}.'},
    {'check_crate_not_used': 'You have not used {} in your guild yet.'},
    {'setup_crate_channel_ping': '{}, this channel is where weapon/gear crate respawn alerts will be sent!'},
    {'setup_crate_success': 'Your crate alerts output channel has been set to {}!\nThe role that will be mentioned is {}.\n-# If you do not get an alert when you expect it, please join the support server and let me know.'},
    {'crate_previous_channel_alert_error': 'The channel you previous selected for weapon/gear crate respawn alerts was not a text/announcement channel.\nYour settings have been removed from the database.\nPlease {} your channel again.'},
    {'crate_cmd_notify': 'Use {} to change the channel or change/add a role to ping.'},
    {'crate_channel_alert_error': '[CRATE] The bot is not able to send messages/view the channel in the channel you have chosen for Weapon/Gear crate respawn alerts, {}.\nPlease edit the channel settings by right clicking the channel name and make sure the bot or it\'s role has View Channel, Send Messages, and Embed Links set to the ✅ (green check) and try again.\n-# If you need assistance, please join the support server.'},
    # Guild blacklist
    {'guild_blacklist_title': 'Guild has been Blacklisted!'},
    {'guild_blacklist_message': 'Your guild was blacklisted from adding the bot due to removing it from the server too many times.\nPlease contact me on Discord on the support server if you have a good reason for removing it so many times.'},
    # New guild embed
    {'new_guild_welcome_message_title': 'Thanks for adding the Once Human Utility Bot!'},
    {'new_guild_welcome_message_description': 'This message was added to combat the issue with users not getting alerts.'},
    {'new_guild_welcome_message_info': 'By default, you will not get any alerts.\nPlease use the {} or {} command to setup the alerts.'},
    {'new_guild_welcome_message_footer': 'The is the only \"spam\" message the bot will send.\nThis message deletes itself after 5 minutes.'},
    # Deviant
    {'deviant_locations': 'Locations'},
    {'deviant_effects': 'Effects'},
    {'deviant_happiness': 'Happiness'},
    {'deviant_error': 'Unable to locate any deviant containing `{}`.  Please try your search again.'},
    # Purification/Controller
    {'purification_channel_alert_error': '[PURIFICATION] The bot is not able to send messages/view the channel in the channel you have chosen for Purification reset alerts, {}.\nPlease edit the channel settings by right clicking the channel name and make sure the bot or it\'s role has View Channel, Send Messages, and Embed Links set to the ✅ (green check) and try again.\n-# If you need assistance, please join the support server.'},
    {'controller_channel_alert_error': '[CONTROLLER] The bot is not able to send messages/view the channel in the channel you have chosen for Controller reset alerts, {}.\nPlease edit the channel settings by right clicking the channel name and make sure the bot or it\'s role has View Channel, Send Messages, and Embed Links set to the ✅ (green check) and try again.\n-# If you need assistance, please join the support server.'},
    {'setup_purification_success': 'Your purification reset alerts output channel has been set to {} on {}!\nThe role that will be mentioned is {}.\n-# If you do not get an alert when you expect it, please join the support server and let me know.'},
    {'setup_controller_success': 'Your controller reset alerts output channel has been set to {} on {}!\nThe role that will be mentioned is {}.\n-# If you do not get an alert when you expect it, please join the support server and let me know.'},
    {'purification_reset_alert_message': 'This is the weekly Purification reset alert message.'},
    {'controller_reset_alert_message': 'This is the weekly Controller reset alert message.'},
    {'setup_purification_channel_ping': '{}, this channel is where purification alerts will be sent!'},
    {'setup_controller_channel_ping': '{}, this channel is where controller alerts will be sent!'},
    {'sproutlet_channel_alert_error': '[SPROUTLET] The bot is not able to send messages/view the channel in the channel you have chosen for Controller reset alerts, {}.\nPlease edit the channel settings by right clicking the channel name and make sure the bot or it\'s role has View Channel, Send Messages, and Embed Links set to the ✅ (green check) and try again.\n-# If you need assistance, please join the support server.'},
    {'setup_sproutlet_success': 'Your sproutlet alerts output channel has been set to {} at {}!\nThe role that will be mentioned is {}.\n-# If you do not get an alert when you expect it, please join the support server and let me know.'},
    {'setup_sproutlet_channel_ping': '{}, this channel is where sproutlet alerts will be sent!'},
    # Medics/Trunks
    {'sproutlet_alert_message': 'The sproutlet event has a chance to spawn {}!\nRandomly spawns at a settlement in Chalk Peak, Lone Wolf Wastes, or Blackheart Region and lasts for 20 minutes.'},
    {'medics_channel_alert_error': '[MEDICS/TRUNKS] The bot is not able to send messages/view the channel in the channel you have chosen for medic/trunk respawn alerts, {}.\nPlease edit the channel settings by right clicking the channel name and make sure the bot or it\'s role has View Channel, Send Messages, and Embed Links set to the ✅ (green check) and try again.\n-# If you need assistance, please join the support server,'},
    {'setup_medics_channel_ping': '{}, this channel is where medics/trunks respawn alerts will be sent!'},
    {'setup_medics_success': 'Your medics/trunks respawn alerts output channel has been set to {}!\nThe role that will be mentioned is {}.\n-# If you do not get an alert when you expect it, please join the support server and let me know.'},
    {'medics_respawn_alert_message': 'This is the {} reset announcement.'},
    {'medics_respawn_footer': 'Log out to the main menu and log back in to see the reset medics/trunks.'},
    # Lunar Event
    {'lunar_alert_message': 'The Lunar event is starting now!  This event lasts 15 minutes.'},
    # Errors
    {'no_channels_set_alert': 'No channel set for any alerts!'},
    {'check_channel_type_error': 'This bot only supports text/announcement channels.\nPlease {} your channel again.'},
    {'check_chanel_not_found_error': 'Channel not found.\nPlease {} your channel again.'},
    {'app_command_cooldown_error': 'That command is on cooldown.  Please try again in `{}` seconds.'},
    {'app_command_general_error': 'There was an error with your request:\n`{}`'},
    # Support/Feedback
    {'feedback_response': 'Thank you for the `{}` report, {}!\n\nSent:\n`{}`\n\n-# Follow up on the support server!'},
    {'feedback_wrong_choice': 'Please only enter `{}` or `{}` into the feedback type box.'},
    {'feedback_error': 'Oops! Something went wrong.\n{}'},
    {'support_title': 'Discord Invite Link'},
    {'support_last_update': '-# Last update: {}'},
    {'support_feedback': 'You can send an anonymous feedback or bug report with {}.'},
    {'support_reload': 'If a command isn\'t working as expected, reload (CTRL+R) or restart Discord.'},
    {'support_permissions': 'After that, verify the bot user has the correct permissions for "View Channel", "Send Messages", and "Embed Links" marked as ✅ on the channel you are trying to use.'},
    # Other
    {'next_respawns_message': 'It is {}:{} UTC.\nCrates respawn at 00:00 UTC and every 4 hours after.\nCargo Scramble spawns at 12:00, 15:00, 18:30, and 22:00 UTC (11, 14, 17:30, 21 UTC for Asian servers).\n\nNext crate respawn:\t\t{} or ~{}.\nNext Cargo Scramble:\t{} or ~{}\n\t\t\t(Asia:\t{} or ~{}).'},
    {'test_alert_success': 'Sent test embed(s): `{}` to your channel{}.'},
    {'remove_data_success': 'Your guild ID and channel ID have been removed from the database.\n## Your guild will no longer get alerts.'},
    ]

class AutoVivification(dict):
    """Implementation of perl's autovivification feature."""
    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value


lang_dict = AutoVivification()
for i, language in enumerate(LANGUAGES.values()):
    print(f'({i+1}/{len(LANGUAGES.values())}) {language.upper()}')
    for phrase in tqdm(strings_to_translate):
        translated_phrase = translator.translate(list(phrase.values())[0], dest=language.lower())
        lang_dict[language][list(phrase.keys())[0]] = translated_phrase.text
with open('translations.py', 'w', encoding='utf-8') as f:
    f.write(f"TRANSLATIONS = {lang_dict}")
    
print("All done!") 