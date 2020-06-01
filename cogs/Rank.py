# type: ignore
from discord.ext import commands, tasks
import discord
import asyncio
import os
import json
import time
from datetime import datetime

from helper import TaggingDb
from helper import discord_common
from helper import table
from helper import paginator

class Rank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.rank_cache = []
        self.rank_tag_cache = []
        self.tagged_problem = set()
        self.tagged_problem_and_discord_id = set()

    async def calculate_rank(self, ctx):
        await ctx.send('Calculating...')
        #shortlink, tag, discord_id
        tagged = TaggingDb.TaggingDb.get_data('tagged', limit=None)
        cnt_tag = {}
        for p, tag, discord_id in tagged:
            self.tagged_problem.add(p)
            self.tagged_problem_and_discord_id.add((p, discord_id))
            if tag not in cnt_tag:
                cnt_tag[tag] = 0
            cnt_tag[tag] += 1
        self.rank_tag_cache = []
        for tag, cnt_t in cnt_tag.items():
            self.rank_tag_cache.append((cnt_t, tag))
        self.rank_tag_cache.sort(reverse=True)
        cnt = {}
        for p, discord_id in self.tagged_problem_and_discord_id:
            if discord_id not in cnt:
                cnt[discord_id] = 0
            cnt[discord_id] += 1
        self.rank_cache = []
        for discord_id, cnt_t in cnt.items():
            member = ctx.guild.get_member(int(discord_id))
            name = discord_id
            if member is not None:
                name = member.name
            self.rank_cache.append((cnt_t, name))
        self.rank_cache.sort(reverse=True)

    # from TLE bot: https://github.com/cheran-senthil/TLE/blob/97c9bff9800b3bbaefb72ec00faa57a4911d3a4b/tle/cogs/duel.py#L410
    @commands.command(brief="Hiện bảng xếp hạng và một số thông tin")
    @commands.check_any(commands.is_owner(), commands.has_any_role('Admin', 'Mod VNOI'))
    async def rank(self, ctx):
        """
        Hiện bảng xếp hạng.
        """
        if ctx.guild is None:
            await ctx.send("Vì lý do kỹ thuật, lệnh này chỉ được dùng ở server discord của VNOI")
            return
        # if len(self.rank_cache) == 0:
        await self.calculate_rank(ctx)
        await ctx.send(f'Số bài đã được tag (các user tính riêng): {len(self.tagged_problem_and_discord_id)}\n'
            f'Số bài đã được tag (unique): {len(self.tagged_problem)}')
        _PER_PAGE = 10

        def make_page(chunk, page_num, tag_rank=False):
            style = table.Style('{:>}  {:<}  {:<}')
            t = table.Table(style)
            if tag_rank:
                t += table.Header('#', 'Tag', 'Số bài')
            else:
                t += table.Header('#', 'Username', 'Số bài')
            t += table.Line()
            for index, (cnt_tagged, User) in enumerate(chunk):
                t += table.Data(_PER_PAGE * page_num + index, User, cnt_tagged)

            table_str = f'```yml\n{t}\n```'
            embed = discord.Embed(description=table_str)
            if tag_rank:
                return 'Số bài đã tag theo từng tag', embed
            return 'Bảng xếp hạng', embed

        pages = [make_page(chunk, k) for k, chunk in enumerate(
            paginator.chunkify(self.rank_cache, _PER_PAGE))]
        paginator.paginate(self.bot, ctx.channel, pages)
        pages = [make_page(chunk, k, tag_rank=True) for k, chunk in enumerate(
            paginator.chunkify(self.rank_tag_cache, _PER_PAGE))]
        paginator.paginate(self.bot, ctx.channel, pages)

def setup(bot):
    bot.add_cog(Rank(bot))
