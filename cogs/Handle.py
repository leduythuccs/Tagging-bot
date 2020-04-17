from discord.ext import commands
import discord
import asyncio
import os
from helper import TaggingDb
import random
SET_HANDLE_SUCCESS = 'Nick cho <@{0}> đã được set thành <https://codeforces.com/profile/{1}>'

class Handle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Set nick codeforces để dùng bot.",
    usage="nick codeforces của bạn.")
    async def identify(self, ctx, handle): 
        """
        Dùng command này để set nick codeforces.
        Nếu nick codeforces mình là `leduykhongngu` thì mình dùng:
        ;tag identify leduykhongngu
        """
        discord_id = ctx.author.id
        TaggingDb.TaggingDb.add_handle(discord_id, handle)
        await ctx.send(SET_HANDLE_SUCCESS.format(discord_id, handle))

def setup(bot):
    bot.add_cog(Handle(bot))