import os
from dotenv import load_dotenv
from discord.ext import commands
from helper import discord_common
from helper import config as config
current_path = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_path)
load_dotenv()
token = config.config.get("DISCORD_TOKEN")

def setup():
    if os.path.exists('database/save') is False:
        os.mkdir('database/save')
setup()
# bot
bot = commands.Bot(command_prefix=';tag ')
print(bot.command_prefix)
bot.load_extension("cogs.BotControl")
bot.load_extension("cogs.Tag")
bot.load_extension("cogs.Handle")
def no_dm_check(ctx):
    if ctx.guild is None:
        raise commands.NoPrivateMessage('Private messages not permitted.')
    return True

# Restrict bot usage to inside guild channels only.
# bot.add_check(no_dm_check)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')



@bot.event
async def on_command_error(ctx, error):
    print(error)

    await ctx.send(embed=discord_common.embed_alert(error))

bot.run(token)
