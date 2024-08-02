GNU General Public License v3.0
Permissions of this strong copyleft license are conditioned on making available complete source code of licensed works and modifications, which include larger works using a licensed work, under the same license. Copyright and license notices must be preserved. Contributors provide an express grant of patent rights.

## Bot add link
https://discord.com/oauth2/authorize?client_id=1264198984306790431

## Bot Commands
#### `/search_deviant dev_name`:
(30 second cooldown per user)
- You can now search a small database for information on deviants.
 - Where they are found, what effect they have, and what makes them happy.
#### `/next`:
(30 second cooldown per user)
- Sends an ephemeral message (only the user who runs the command will see it) that deletes itself after 60 seconds that shows the current UTC time, the list of respawn times, and a timestamp with your local date/time of the next respawn.

< ADMINISTRATOR ONLY COMMANDS>
#### `/setup channel [role]`:
- Set the text channel that the alert will be sent.
- [OPTIONAL] Include a role to be mentioned in the alerts.  Leave blank for no role mention (default behavior).
#### `/test_alert`:
(30 second cooldown per user)
- Sends a test alert to your designated channel to ensure it works properly.  This command is pretty much obsolete now that `/setup` has some checks built into it.
#### `/check`:
- Sends an ephemeral message that lists the channel and role you currently have set for alerts.
#### `/remove_data`:
(1 hour cooldown per user)
- Deletes any records in the `channels` database with the guild_id of the guild the command was run in.

## Feel free to send any issues or suggestions for new features/changes.
