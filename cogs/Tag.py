from discord.ext import commands, tasks
import discord
import asyncio
import os
import json
import time
from datetime import datetime

from helper import TaggingDb
from helper import discord_common
from helper import parser

# 2 string a considered as the same if LCS(a, b) >= max(len(a), len(b)) * _LCS_THRESHOLD_
_LCS_THRESHOLD_ = 0.8  # 80%

async def get_similar_tag(ctx, tag):
    similar = TaggingDb.TaggingDb.get_similar_tag(tag)
    if len(similar) == 0:
        embed = discord_common.embed_alert('Không tìm thấy tag `{}`'.format(tag))
        await ctx.send(embed=embed)
        return
    if similar[0][0] < max(len(tag), len(similar[0][1])) * _LCS_THRESHOLD_:
        msg = 'Không tìm thấy tag nào giống `{}`. '.format(tag)
        msg_similar = ""  

        for i in range(min(5, len(similar))):
            if similar[i][0] == 0:
                break
            msg_similar += '\n- ' + similar[i][1]
        if len(msg_similar) > 0:
            msg += 'Một số tag có thể giống:'
            embed = discord_common.embed_alert(msg_similar)
            await ctx.send(msg, embed=embed)
            return
        await ctx.send(msg)
        return
    return similar[0][1]


class Tag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Force tạo category mới.",
                      usage="[category name]")
    @commands.check_any(commands.is_owner(), commands.has_any_role('Admin', 'Mod VNOI'))
    async def _create(self, ctx, *args):
        """
        Force tạo category mới, có thể có unicode
        Ví dụ ;tag _create Quy Hoạch Động bao lồi cực mạnh
        """
        tag = ' '.join(args)
        tag = TaggingDb.normalize_tag(tag)
        TaggingDb.TaggingDb.add_tag(tag)
        await ctx.send('Tạo tag `{}` thành công'.format(tag))

    @commands.command(brief="Tạo tag mới.",
                      usage="[tag]")
    @commands.check_any(commands.is_owner(), commands.has_any_role('Admin', 'Mod VNOI'))
    async def create(self, ctx, *args):
        """
        Tạo tag mới, có thể có unicode
        Ví dụ ;tag create Quy Hoạch Động bao lồi cực mạnh
        """
        tag = ' '.join(args)
        tag = TaggingDb.normalize_tag(tag)
        similar = TaggingDb.TaggingDb.get_similar_tag(tag)
        if len(similar) > 0:
            if similar[0][0] >= max(len(tag), len(similar[0][1])) * _LCS_THRESHOLD_:
                await ctx.send('Hmm, hình như 2 tag này giống nhau, '
                               'nếu chắc chắn muốn add thì dùng _create:'
                               '\n- `{}`\n- `{}`'.format(tag, similar[0][1]))
                return
        await self._create(ctx, tag)

    @commands.command(brief="Thêm bài vào tag.",
                      usage="[tag] [link bài] [link code] [độ khó]")
    @commands.check_any(commands.is_owner(), commands.has_any_role('Admin', 'Mod VNOI'))
    async def add(self, ctx, *args):
        """
        Thêm bài vào tag, lưu ý là link phải bắt đầu bằng http. Độ khó phải theo format codeforces [D1A, D1B, ... D1E]
        Ví dụ ;tag add DP https://linkbai  https://linkcode D1E
        """
        # parse arg
        params = parser.tag_parse(args)
        if isinstance(params, str):
            embed = discord_common.embed_alert(params)
            await ctx.send(embed=embed)
            return
        tag, link_problem, link_code, diff = params

        # get tag
        real_tag = await get_similar_tag(ctx, tag)
        if real_tag is None:
            return

        TaggingDb.TaggingDb.tagging(real_tag, link_problem, link_code, diff)

        await ctx.send('Tìm thấy tag `{}` giống với `{}`. Đã add.'.format(real_tag, tag))

    @commands.command(brief="Lấy danh sách các bài đã được add theo tag.",
                      usage="[tag]")
    async def get(self, ctx, *args):
        """
        Thêm bài vào tag, lưu ý là link phải bắt đầu bằng http. Độ khó phải là số float-able
        Ví dụ ;tag add DP https://linkbai  https://linkcode 250
        """
        tag = ' '.join(args)
        # ----------------------------
        # get tag
        real_tag = await get_similar_tag(ctx, tag)
        if real_tag is None:
            return
        await ctx.send('Tìm thấy tag `{}` giống với `{}`.'.format(real_tag, tag))

        problems = TaggingDb.TaggingDb.get_tagged(real_tag)
        if len(problems) == 0:
            await ctx.send('Chưa có bài nào thuộc tag `{}`'.format(tag))
            return
        msg = ""
        for link, code, diff in problems:
            msg += f"[link]({link})\t[code]({code})\t{diff}\n"
        embed = discord.Embed(description=msg.strip())
        await ctx.send('Các bài thuộc tag `{}`'.format(real_tag), embed=embed)


def setup(bot):
    bot.add_cog(Tag(bot))
