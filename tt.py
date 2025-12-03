"""Example TeamTalk bot script for testing connections.

This is a standalone example script that demonstrates how to use pytalk-ex.
It reads configuration from the .env file.
"""

import pytalk
from pytalk import server

# Import configuration from the app
from app.config import BOT_SERVER_CONFIG

bot = pytalk.TeamTalkBot()


@bot.event
async def on_ready():
    """Called when the bot is ready to connect."""
    await bot.add_server(BOT_SERVER_CONFIG)


@bot.event
async def on_error(ename: str, *args, **kwargs):
    """Called when an error occurs."""
    print(f"Error in event {ename}: {args}, {kwargs}")


@bot.event
async def on_my_login(srv: server.Server):
    """Called when the bot successfully logs in."""
    print("Connected to the server!")
    users = srv.get_users()
    if users:
        print(users[0])


if __name__ == "__main__":
    bot.run()  # this is a blocking call