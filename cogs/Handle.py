# type: ignore
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

    @commands.command(brief="Set nick codeforces cho người khác",
                      usage="@user codeforces_handle")
    @commands.check_any(commands.is_owner(), commands.has_any_role('Admin', 'Mod VNOI'))
    async def set(self, ctx, member: discord.Member, handle):
        """
        Dùng command này để set nick codeforces cho người khác
        """
        discord_id = member.id
        TaggingDb.TaggingDb.add_handle(discord_id, handle)
        if os.path.exists('database/save/' + str(discord_id) + '.json'):
            os.remove('database/save/' + str(discord_id) + '.json')
        
        if os.path.exists('database/save/info_' + str(discord_id) + '.json'):
            os.remove('database/save/info_' + str(discord_id) + '.json')
        
        await ctx.send(SET_HANDLE_SUCCESS.format(discord_id, handle))

    @commands.command(brief="Tự set nick codeforces",
                      usage="codeforces_handle")
    async def identify(self, ctx, handle):
        """
        Dùng command này để set nick codeforces:
        Ví dụ account codeforces của mình là leduykhongngu thì mình dùng:
        ;identify leduykhongngu
        """
        if ctx.guild is None:
            await ctx.send("Lệnh này chỉ được dùng ở server discord của VNOI, không được dùng trong tin nhắn")
            return
        discord_id = ctx.author.id
        TaggingDb.TaggingDb.add_handle(discord_id, handle)
        await ctx.send(SET_HANDLE_SUCCESS.format(discord_id, handle))


def setup(bot):
    bot.add_cog(Handle(bot))
