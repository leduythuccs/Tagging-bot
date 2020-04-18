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
from helper import codeforces_api

# 2 string a considered as the same if LCS(a, b) >= max(len(a), len(b)) * _LCS_THRESHOLD_
_LCS_THRESHOLD_ = 0.8  # 80%


async def get_similar_tag(ctx, tag):
    similar = TaggingDb.TaggingDb.get_similar_tag(tag)
    if len(similar) == 0:
        embed = discord_common.embed_alert(
            'Không tìm thấy tag `{}`'.format(tag))
        await ctx.send(embed=embed)
        return
    if similar[0][0] < _LCS_THRESHOLD_:
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
BASE_URL = "https://codeforces.com/contest/{0}/problem/{1}"
SUBMISSION_BASE_URL = "https://codeforces.com/contest/{0}/submission/{1}"


def short_link_to_msg(short_link):
    contest_id, index = short_link.split('/')
    return BASE_URL.format(contest_id, index)

def problem_to_embed(problem):
    msg = f"[{problem['name']}]({short_link_to_msg(problem['short_link'])})\n"
    submission_link = SUBMISSION_BASE_URL.format(problem['short_link'].split('/')[0], problem['submission_id'])
    msg += f"[AC submission]({submission_link})\n"
    msg += f"Rating: ({problem['rating']})\n"
    msg += f"Tag gốc từ codeforces: {str(problem['tags'])}\n"
    tags = TaggingDb.TaggingDb.get_problem_tag(problem['short_link'])
    if len(tags) > 0:
        msg += "Các tag đã được add:\n"
        for tag in tags:
            msg += f"  + {tag}\n"
    comments = TaggingDb.TaggingDb.get_problem_comment(problem['short_link'])
    if len(comments) > 0:
        msg += "Các comment đã được add:\n"
        for comment in comments:
            msg += f" + {comment}\n"
    return discord_common.embed_success(msg)

class Tag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Force tạo 1 tag mới.",
                      usage="[tag]")
    @commands.check_any(commands.is_owner(), commands.has_any_role('Admin', 'Mod VNOI'))
    async def _create(self, ctx, *args):
        """
        Force tạo tag mới, chỉ được tạo duy nhất 1
        Ví dụ ;tag _create Quy Hoạch Động bao lồi cực mạnh
        """
        tag = ' '.join(args)
        tag = TaggingDb.normalize_tag(tag)
        TaggingDb.TaggingDb.add_tag(tag)
        if ctx is not None:
            await ctx.send('Tạo tag `{}` thành công'.format(tag))

    @commands.command(brief="Tạo tag mới.",
                      usage="[tag1];[tag2];[tag3];...")
    @commands.check_any(commands.is_owner(), commands.has_any_role('Admin', 'Mod VNOI'))
    async def create(self, ctx, *args):
        """
        Tạo (nhiều) tag mới, có thể có unicode, các tag cách nhau bởi dấu `;`
        Ví dụ ;tag create Quy Hoạch Động; Segment tree
        """
        tags = list(filter(lambda x: len(x) > 0, args))
        error_msg = ""
        added_msg = ""
        for tag in tags:
            tag = TaggingDb.normalize_tag(tag)
            similar = TaggingDb.TaggingDb.get_similar_tag(tag)
            if len(similar) > 0:
                if similar[0][0] >= _LCS_THRESHOLD_:
                    error_msg += '`{}` giống `{}`\n'.format(tag, similar[0][1])
                    continue
            added_msg += tag + '\n'
            await self._create(None, tag)
        if len(error_msg) > 0:
            embed = discord_common.embed_alert(error_msg.strip())
            await ctx.send('Các tag chưa được thêm vì giống trong database, dùng _create để force create:', embed=embed)
        if len(added_msg) > 0:
            embed = discord_common.embed_success(added_msg)
            await ctx.send('Các tag đã được thêm:', embed=embed)
    
    @commands.command(brief="Đổi tên tag")
    @commands.check_any(commands.is_owner(), commands.has_any_role('Admin', 'Mod VNOI'))
    async def modify(self, ctx, old_tag, new_tag):
        old_tag = TaggingDb.normalize_tag(old_tag)
        new_tag = TaggingDb.normalize_tag(new_tag)
        s = TaggingDb.TaggingDb.rename(old_tag, new_tag)
        if s is not None:
            embed = discord_common.embed_alert(s)
            await ctx.send(embed=embed)
        await ctx.send(f'Đã đổi tên tag {old_tag} sang {new_tag}')

    @commands.command(brief="Thêm tag vào bài .",
                      usage="[tag1] [tag2] [tag3] ... \"comment\"")
    async def add(self, ctx, *args):
        """
        Thêm tag vào bài, lưu ý các tag cần cách nhau bởi space. comment cần được đặt vào giữa 2 dấu \"\". 
        Không cần comment cũng được. Vì lý do kỹ thuật, trong comment cần có ít nhất 1 space
        Ví dụ ;tag add dp-tree bitset \"bài hay\"
        """
        current_problem = codeforces_api.get_current_problem(ctx.author.id)
        if current_problem is None:
            await ctx.send(f"{ctx.author.mention} chưa được phân công bài nào, hãy dùng lệnh `;tag get` để được phân công bài.")
            return
        problem_short_link = current_problem['short_link']
        # parse arg
        params = parser.tag_parse(args)
        if isinstance(params, str):
            embed = discord_common.embed_alert(params)
            await ctx.send(embed=embed)
            return
        tags, comment = params
        msg = ""
        for tag in tags:
            tag = TaggingDb.normalize_tag(tag)
            # get tag
            real_tag = await get_similar_tag(ctx, tag)
            if real_tag is None:
                continue

            TaggingDb.TaggingDb.tagging(problem_short_link, real_tag)

            msg += '\n-`{}` (giống `{}`).'.format(real_tag, tag)
        if len(msg) != 0:
            await ctx.send('Các tag đã tìm thấy:', embed=discord_common.embed_success(msg))
        if len(comment) > 0:
            TaggingDb.TaggingDb.commenting(problem_short_link, comment)
        #--------------------------------------------------------------
        embed = problem_to_embed(current_problem)
        await ctx.send('Thông tin hiện tại của bài:', embed=embed)

    @commands.command(brief="Lấy bài tập mới")
    async def get(self, ctx):
        handle = TaggingDb.TaggingDb.get_handle(ctx.author.id)
        if handle is None:
            await ctx.send(f"Không tìm được codeforces handle của {ctx.author.mention}. Hãy dùng lệnh `;tag identify handle_cf`")
            return
        problem = await codeforces_api.get_problem(handle, ctx.author.id)
        if problem is None:
            await ctx.send(f"Không tìm được bài nào phù hợp cho {ctx.author.mention}")
            return

        current_problem = codeforces_api.get_current_problem(ctx.author.id)
        if current_problem is not None:
            # todo done info 
            embed = problem_to_embed(current_problem)
            await ctx.send('Thông tin của bài tập hiện tại', embed=embed)
            return

        codeforces_api.set_current_problem(ctx.author.id, problem)

        embed = problem_to_embed(problem)
        await ctx.send(f"Bài tập mới cho {ctx.author.mention}.\n" +
        "Để đánh tag bài, dùng `;tag add tag1 tag2 .... \"comment có space\"`.\n" +
        "Các tag cách nhau bởi dấu cách, comment có thể có hoặc không. Vì lý do kỹ thuật, trong comment cần có ít nhất 1 space.\n" + 
        "Ví dụ: `;tag add dp-tree bitset \"bài hay\"`\n"+ 
        "Dùng lệnh `;tag done` để hoàn thành, `;tag skip` để bỏ qua.", embed=embed)

    @commands.command(brief="Xóa tag bị add nhầm")
    async def remove(self, ctx, *args):
        """
        Xóa tag đã add vào bài, param giống add
        Ví dụ ;tag remove dp-tree bitset
        """
        current_problem = TaggingDb.TaggingDb.get_current_problem(
            ctx.author.id)
        if current_problem is None:
            await ctx.send(f"{ctx.author.mention} chưa được phân công bài nào, hãy dùng lệnh `;tag get` để được phân công bài.")
            return
        problem_short_link = current_problem['short_link']
        # parse arg
        params = parser.tag_parse(args)
        if isinstance(params, str):
            embed = discord_common.embed_alert(params)
            await ctx.send(embed=embed)
            return
        tags, comment = params
        msg = ""
        for tag in tags:
            tag = TaggingDb.normalize_tag(tag)
            # get tag
            real_tag = await get_similar_tag(ctx, tag)
            if real_tag is None:
                continue

            TaggingDb.TaggingDb.remove_tag(problem_short_link, real_tag)

            msg += '\n-`{}` (giống `{}`).'.format(real_tag, tag)
        if len(msg) != 0:
            await ctx.send('Các tag đã tìm thấy:', embed=discord_common.embed_success(msg))
        
        embed = problem_to_embed(current_problem)
        await ctx.send('Thông tin hiện tại của bài:', embed=embed)

    @commands.command(brief="Hoàn thành bài.")
    async def done(self, ctx):
        """
        Hoàn thành bài tập đang làm
        Ví dụ ;tag done 
        sẽ hoàn thành việc tag bài hiện tại và được lấy bài mới
        """
        current_problem = codeforces_api.get_current_problem(ctx.author.id)
        if current_problem is None:
            await ctx.send(f"{ctx.author.mention} chưa được phân công bài nào, hãy dùng lệnh `;tag get` để được phân công bài.")
            return
        embed = problem_to_embed(current_problem)

        is_tagged = TaggingDb.TaggingDb.check_exists(
                'tagged', 'problem', current_problem['short_link'])
        # is_commented = TaggingDb.TaggingDb.check_exists(
        #     'commented', 'problem', current_problem['short_link'])
        if not is_tagged:
            await ctx.send("Bài hiện tại đã được đánh tag đâu mà `done`, nếu muốn bỏ qua thì dùng `skip`, các thông tin:", embed=embed)
            return
        await ctx.send("Đội ơn bạn <:orz:661153248186597386>", embed=embed)
        submission_link = SUBMISSION_BASE_URL.format(current_problem['short_link'].split('/')[0], current_problem['submission_id'])
        TaggingDb.TaggingDb.add_submission(current_problem['short_link'], submission_link)
        codeforces_api.set_current_problem(ctx.author.id, None)
        await self.get(ctx)
    
    @commands.command(brief="Bỏ qua bài")
    async def skip(self, ctx, *args):
        """
        Bỏ quả bài tập đang làm
        Ví dụ ;tag skip 
        sẽ hoàn thành việc tag bài hiện tại và được lấy bài mới
        """
        current_problem = codeforces_api.get_current_problem(ctx.author.id)
        if current_problem is None:
            await ctx.send(f"{ctx.author.mention} chưa được phân công bài nào, hãy dùng lệnh `;tag get` để được phân công bài.")
            return
        embed = problem_to_embed(current_problem)

        is_tagged = TaggingDb.TaggingDb.check_exists(
                'tagged', 'problem', current_problem['short_link'])
        # is_commented = TaggingDb.TaggingDb.check_exists(
        #     'commented', 'problem', current_problem)
        if is_tagged:
            await ctx.send("Bài hiện tại đã được đánh tag rồi sao lại dùng `skip`, dùng `done` đê, các thông tin:", embed=embed)
            return
        await ctx.send("Đã bỏ qua bài tập:", embed=embed)
        codeforces_api.set_current_problem(ctx.author.id, None)
        await self.get(ctx)

    @commands.command(brief="Lấy danh sách các bài cùng tag.",
                      usage="[tag]")
    async def info(self, ctx, *args):
        """
        Lấy danh sách các bài có tag cho trước
        Ví dụ ;tag info dp-tree 
        """
        tag = ' '.join(args)
        tag = TaggingDb.normalize_tag(tag)
        # ----------------------------
        # get tag
        real_tag = await get_similar_tag(ctx, tag)
        if real_tag is None:
            return
        await ctx.send('Tìm thấy tag `{}` giống với `{}`.'.format(real_tag, tag))

        problems = TaggingDb.TaggingDb.get_tagged(real_tag)
        if len(problems) == 0:
            await ctx.send('Chưa có bài nào thuộc tag `{}`'.format(real_tag))
            return
        msg = ""
        for p in problems:
            link = short_link_to_msg(p[0])
            msg += f"[link]({link})\n"
        embed = discord.Embed(description=msg.strip())
        await ctx.send('Các bài thuộc tag `{}`'.format(real_tag), embed=embed)


def setup(bot):
    bot.add_cog(Tag(bot))
