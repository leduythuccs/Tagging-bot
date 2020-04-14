# VOJ-Tagging-bot
 A discord bot which helps tagging Codeforces problem

## Features
- Create a tag
- Add problem to tag

## Installation
Clone this repository 
- `python pip install -r requirements`
- Base on file `.env-example`, create file `.env` and fill it with your bot token

## How to use
- Create a discord bot, add it to your discord server.
- Then use `python main.py` to run the bot. Remember to edit data in `.env`.
- Use `;tag help` to see list command
    
## Developing:
- How can we create/add multiple tag? Maybe we can use the comma (`,`) to separate tags, small fix in [parser](helper/parser.py) would be okay.

