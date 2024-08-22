GNU General Public License v3.0
Permissions of this strong copyleft license are conditioned on making available complete source code of licensed works and modifications, which include larger works using a licensed work, under the same license. Copyright and license notices must be preserved. Contributors provide an express grant of patent rights.

## Bot add link
https://discord.com/oauth2/authorize?client_id=1264198984306790431

# Bot Commands
### `/feedback`:
(30 minute cooldown per user)
- Opens a form to provide anonymous feedback or bug report about the bot.
 - Reports are visible to all members of the support server to vote and/or comment on.
### `/search_deviant dev_name`:
(30 second cooldown per user)
- You can now search a small database for information on deviants.
### `/next`:
(30 second cooldown per user)
- Sends an ephemeral message (only the user who runs the command will see it) that shows the current UTC time, the list of crate and cargo scramble respawn times, and a timestamp with your local date/time of the next respawn.

## <- ADMINISTRATOR ONLY COMMANDS ->
### `/setup channel [role]`:
- Set the text/announcement channel that the weapon/gear crate respawn alert will be sent.
- [OPTIONAL] Include a role to be mentioned in the alerts.  Leave blank for no role mention (default behavior).
### `/cargo_scramble channel [role]`:
- Set the text/announcement channel that the Cargo Scramble alert will be sent.
- [OPTIONAL] Include a role to be mentioned in the alerts.  Leave blank for no role mention (default behavior).
### `/crate_mute` and `/cargo_mute`:
(30 second cooldown per user)
- Mutes alerts for times you pick.
### `/test_alert`:
(15 second cooldown per user)
- Sends a test alert to your designated channel to ensure it works properly.  This command is pretty much obsolete now that `/setup` has some checks built into it.
### `/remove_data`:
(1 hour cooldown per user)
- Deletes any records in the database with the guild_id of the guild the command was run in.

## Feel free to send any issues or suggestions for new features/changes.
