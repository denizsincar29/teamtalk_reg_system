# task
Create a fastapi web application that registers users on my teamtalk server denizsincar.ru.
It must receive a username and password from entered form data and register the user on the teamtalk server using the TeamTalk SDK. The example is in tt.py.
The pytalk-ex library doesn't like other frameworks, so we can run teamtalk things in a separate process or provide a solution your own way.
We use UV package manager. Use uv add dependencyname and uv run main.py to run the application.
Also the website must check if this user already exists on the teamtalk server before registering.
I don't know how to use pytalk-ex, examin the source at https://github.com/BlindMaster24/pytalk
Feal free to experiment with the teamtalk api, my server under the credentials at tt.py works and is reachable.