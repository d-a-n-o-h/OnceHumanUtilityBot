GNU General Public License v3.0
Permissions of this strong copyleft license are conditioned on making available complete source code of licensed works and modifications, which include larger works using a licensed work, under the same license. Copyright and license notices must be preserved. Contributors provide an express grant of patent rights.

# Bot Commands

`/setup channel [role]`:

  - Set the text channel that the alert will be sent.
  
  - [OPTIONAL] Include a role to be mentioned in the alerts.  Leave blank for no role mention (default behavior).

`/next`:

  - Sends an ephemeral message (only the user who runs the command will see it) that deletes itself after 60 seconds that shows the current UTC time, the list of respawn times, and a timestamp with your local date/time of the next respawn.

`/search_deviant dev_name`:

  - Sends an embed with deviant name, location, effects, and what increases happiness.

`/test_alert`:

  - Sends a test alert to your designated channel to ensure it works properly.  This command is pretty much obsolete now that `/setup` has some checks built into it.

`/check`:

  - Sends an ephemeral message that lists the channel and role you currently have set for alerts.

`/remove_data`:

  - Deletes any records in the database with the guild_id of the guild the command was run in.

`/manual_send ("no" or "yes")`:

  - If the automatic alerts fail for whatever reason, you can manually send the reset alert.

`/errors`:

  - Goes through the DB and checks permissions for the given channel_id.  Gives a brief output of the number of channels that the bot cannot see or send messages in, and the number of guilds that the bot is in, but no output channel has been specified.
  - The automatic alert every 4 hours will delete any channel_id in the database it is not able to see/send messages in.

# Add the bot to your server

https://discord.com/oauth2/authorize?client_id=1264198984306790431

## Feel free to send any issues or suggestions for new features/changes.
