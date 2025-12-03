import pytalk
from pytalk import server, enums

bot = pytalk.TeamTalkBot()

# this stupid library takes function name as event name!
# IDE users, no autocompletion here! You lazy people!
@bot.event
async def on_ready():
    my_server = {"host": "denizsincar.ru", "tcp_port": 10333, "udp_port": 10333, "username": "bot", "password": "893200"}
    await bot.add_server(my_server)

@bot.event
async def on_error(ename: str, *args, **kwargs):
    print(f"Error in event {ename}: {args}, {kwargs}")


@bot.event
async def on_my_login(server: server.Server):
    print("Connected to the server!")
    users = server.get_users()
    print(users[0])

    #result = server.teamtalk_instance.create_user_account("someuser", "12345", enums.UserType.DEFAULT)  # Don't know why this needs to be sync, i think because it just calls a dll function
    #print("Account creation result:", result)


bot.run()  # this is a blocking call! Don't know how to run this with fastapi or other frameworks yet.