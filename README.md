GNU General Public License v3.0
Permissions of this strong copyleft license are conditioned on making available complete source code of licensed works and modifications, which include larger works using a licensed work, under the same license. Copyright and license notices must be preserved. Contributors provide an express grant of patent rights.

## Bot add link
https://discord.com/oauth2/authorize?client_id=1264198984306790431

# Bot Commands
### `/feedback`:
- Opens a form to provide anonymous feedback or bug report about the bot.
 - Reports are visible to all members of the support server to vote and/or comment on.
### `/search_deviant` `dev_name`:
- Search a small database for information on deviants.
### `/next`:
- Sends an ephemeral message that shows the current UTC time, the list of crate and cargo scramble respawn times, and a timestamp with your local date/time of the next respawn.

## <- ADMINISTRATOR ONLY COMMANDS ->
### `/crate setup` `channel` `[role]`:
- Set the text/announcement channel that the weapon/gear crate respawn alert will be sent.
- [OPTIONAL] Include a role to be mentioned in the alerts.  Leave blank for no role mention.
### `/crate auto_delete` and `/cargo auto_delete` `On/Off`:
- Set `auto_delete` to `On` to have previous alerts delete themselves when new alerts come in.
### `/cargo setup` `channel` `[role]`:
- Set the text/announcement channel that the Cargo Scramble alert will be sent.
- [OPTIONAL] Include a role to be mentioned in the alerts.  Leave blank for no role mention.
### `/crate mute` and `/cargo mute`:
- Mutes alerts for times you pick.
### `/weekly controller_setup`, `/weekly purification_setup`, `/weekly sproutlet_setup` `channel` `day/hour` `[role]` `[auto_delete]`:
- Set the text channel the alert will be sent.
- [OPTIONAL] Include a role to be mentioned in the alerts.  Leave blank for no role mention.
- [OPTIONAL] Set `auto_delete` to `On` to have previous alerts delete themselves when new alerts come in.
### `/medics setup` `channel` `[role]` `[auto_delete]`:
- Set the text channel the alert will be sent.
- [OPTIONAL] Include a role to be mentioned in the alerts.  Leave blank for no role mention.
- [OPTIONAL] Set `auto_delete` to `On` to have previous alerts delete themselves when new alerts come in.
### `/remove_data`:
- Deletes any records in the database with the guild_id of the guild the command was run in.

## Feel free to send any issues or suggestions for new features/changes.
