from discord.ext import commands, tasks
import discord
import asyncio
import os
import json
import time
from datetime import datetime

from helper import TaggingDb
from helper import table
from helper import discord_common

_LCS_THRESHOLD_ = 0.8 #80%
def is_float(value):
    try:
        float(value)
        return True
    except ValueError:  
        return False

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
        TaggingDb.TaggingDb.conn.commit()
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
            if similar[0][0] > max(len(tag), -similar[0][1]) * _LCS_THRESHOLD_:
                await ctx.send('Hmm, hình như 2 tag này giống nhau, nếu chắc chắn muốn add thì dùng _create :\n- `{}`\n- `{}`'.format(tag, similar[0][2]))
                return
        await self._create(ctx, tag)
    @commands.command(brief="Thêm bài vào tag.",
                      usage="[tag] [link bài] [link code] [độ khó]")
    @commands.check_any(commands.is_owner(), commands.has_any_role('Admin', 'Mod VNOI'))
    async def add(self, ctx, *args):
        """
        Thêm bài vào tag, lưu ý là link phải bắt đầu bằng http. Độ khó phải là số float-able
        Ví dụ ;tag add DP https://linkbai  https://linkcode 250
        """
        #----------------------------
        # parse arg
        if len(args) <= 4:
            embed = discord_common.embed_alert('Thiếu param rồi.')
            await ctx.send(embed=embed)
            return
        diff = args[-1]
        if not is_float(diff):
            embed = discord_common.embed_alert('Độ khó phải float-able.\n{}'.format(diff))
            await ctx.send(embed=embed)
            return
        link_code = args[-2]
        if link_code[:4] != 'http':
            embed = discord_common.embed_alert('link code phải bắt đầu bằng `http`.\n{}'.format(link_code))
            await ctx.send(embed=embed)
            return
        link_problem = args[-3]
        if link_problem[:4] != 'http':
            embed = discord_common.embed_alert('link code phải bắt đầu bằng `http`.\n{}'.format(link_problem))
            await ctx.send(embed=embed)
            return
        tag = ' '.join(args[:-3])
        #----------------------------
        # get tag
        similar = TaggingDb.TaggingDb.get_similar_tag(tag)
        if len(similar) == 0:
            embed = discord_common.embed_alert('Không tìm thấy tag `{}`'.format(tag))
            await ctx.send(embed=embed)
            return
        if similar[0][0] < max(len(tag), -similar[0][1]) * _LCS_THRESHOLD_:
            msg = 'Không tìm thấy tag nào giống `{}`. '.format(tag)
            msg_similar = "" #'Một số tag có thể giống: '
            
            for i in range(min(5, len(similar))):
                if similar[i][0] == 0:
                    break
                msg_similar += '\n- ' + similar[i][2]
            if len(msg_similar) > 0:
                msg_similar = 'Một số tag có thể giống:' + msg_similar
            embed = discord_common.embed_alert(msg + msg_similar)
            await ctx.send(embed=embed)
            return
        real_tag = similar[0][2]
        TaggingDb.TaggingDb.tagging(real_tag, link_problem, link_code, diff)
        TaggingDb.TaggingDb.conn.commit()
        await ctx.send('Tìm thấy tag `{}` giống với `{}`. Đã add.'.format(real_tag, tag))
    @commands.command(brief="Lấy danh sách các bài đã được add theo tag.",
                      usage="[tag]")
    async def get(self, ctx, *args):
        """
        Thêm bài vào tag, lưu ý là link phải bắt đầu bằng http. Độ khó phải là số float-able
        Ví dụ ;tag add DP https://linkbai  https://linkcode 250
        """
        tag = ' '.join(args)
        #----------------------------
        # get tag
        similar = TaggingDb.TaggingDb.get_similar_tag(tag)
        if len(similar) == 0:
            embed = discord_common.embed_alert('Không tìm thấy tag `{}`'.format(tag))
            await ctx.send(embed=embed)
            return
        if similar[0][0] < max(len(tag), -similar[0][1]) * _LCS_THRESHOLD_:
            msg = 'Không tìm thấy tag nào giống `{}`. '.format(tag)
            msg_similar = "" #'Một số tag có thể giống: '
            
            for i in range(min(5, len(similar))):
                if similar[i][0] == 0:
                    break
                msg_similar += '\n- ' + similar[i][2]
            if len(msg_similar) > 0:
                msg_similar = 'Một số tag có thể giống:' + msg_similar
            embed = discord_common.embed_alert(msg + msg_similar)
            await ctx.send(embed=embed)
            return
        
        real_tag = similar[0][2]
        await ctx.send('Tìm thấy tag `{}` giống với `{}`.'.format(real_tag, tag))
        problems = TaggingDb.TaggingDb.get_tagged(real_tag)
        if len(problems) == 0:
            await ctx.send('Chưa có bài nào thuộc tag `{}`'.format(tag))
            return

        msg = ""
        for link, code, diff in problems:
            msg += f"[link]({link}) [code]({code}) {diff:.0f}\n"
        embed = discord.Embed(description=msg.strip())
        await ctx.send('Các bài thuộc tag `{}`'.format(real_tag), embed=embed)
    
def setup(bot):
    bot.add_cog(Tag(bot))
