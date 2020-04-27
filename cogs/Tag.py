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
from helper import parser
from helper import codeforces_api
from helper import config
import helper.tag

_LOG_CHANNEL_ = config.config.get("LOG_CHANNEL")
# 2 string a considered as the same if LCS(a, b) >= max(len(a), len(b)) * _LCS_THRESHOLD_
_LCS_THRESHOLD_ = config.config.get("LCS_THRESHOLD")
BASE_URL = "https://codeforces.com/contest/{0}/problem/{1}"
SUBMISSION_BASE_URL = "https://codeforces.com/contest/{0}/submission/{1}"


def short_link_to_msg(short_link):
    contest_id, index = short_link.split('/')
    return BASE_URL.format(contest_id, index)


def problem_to_embed(problem, discord_id):
    msg = f"[{problem['name']}]({short_link_to_msg(problem['short_link'])})\n"
    submission_link = SUBMISSION_BASE_URL.format(problem['short_link'].split('/')[0], problem['submission_id'])
    msg += f"[AC submission]({submission_link})\n"
    msg += f"Rating: ({problem['rating']})\n"
    msg += f"Tag gốc từ codeforces: {str(problem['tags'])}\n"
    tags = TaggingDb.TaggingDb.get_problem_tag(problem['short_link'], discord_id)
    if len(tags) > 0:
        msg += "Các tag đã được add:\n"
        for tag in tags:
            msg += f"  + {tag}\n"
    comments = TaggingDb.TaggingDb.get_problem_comment(problem['short_link'], discord_id)
    if len(comments) > 0:
        msg += "Các comment đã được add:\n"
        for comment in comments:
            msg += f" + {comment}\n"
    return discord_common.embed_success(msg)


async def handle_new_problem(ctx, problem):
    codeforces_api.set_current_problem(ctx.author.id, problem)
    embed = problem_to_embed(problem, ctx.author.id)
    await ctx.author.send(f"Bạn {ctx.author.mention} ơi, tag giúp mình bài này đi <:blowop:665243570696880129>.\n"
                          "Để đánh tag bài, dùng `;add tag1 tag2 .... \"comment ít nhất 3 từ(có thể không có)\"`.\n"
                          "Các tag cách nhau bởi dấu cách\n"
                          "Ví dụ: `;add bit2d dp-bitmask \"dùng bitset để tối ưu\"`\n"
                          "Nếu bạn muốn bỏ qua thì dùng `;skip` nha :cry:", embed=embed)


class Tag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.log_channel = self.bot.get_channel(int(_LOG_CHANNEL_))

    @commands.command(brief="Force tạo 1 tag mới.",
                      usage="[tag]")
    @commands.check_any(commands.is_owner(), commands.has_any_role('Admin', 'Mod VNOI'))
    async def _create(self, ctx, *args):
        """
        Force tạo tag mới, chỉ được tạo duy nhất 1
        Ví dụ ;_create Quy Hoạch Động bao lồi cực mạnh
        """
        tags = list(filter(lambda x: len(x) > 0, args))
        for tag in tags:
            tag = TaggingDb.normalize_tag(tag)
            TaggingDb.TaggingDb.add_tag(tag)
            if ctx is not None:
                await ctx.author.send('Tạo tag `{}` thành công'.format(tag))

    @commands.command(brief="Tạo tag mới.",
                      usage="[tag1];[tag2];[tag3];...")
    @commands.check_any(commands.is_owner(), commands.has_any_role('Admin', 'Mod VNOI'))
    async def create(self, ctx, *args):
        """
        Tạo (nhiều) tag mới, có thể có unicode, các tag cách nhau bởi dấu `;`
        Ví dụ ;create Quy Hoạch Động; Segment tree
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
            await ctx.author.send('Các tag chưa được thêm vì giống trong database, dùng _create để force create:', embed=embed)
        if len(added_msg) > 0:
            embed = discord_common.embed_success(added_msg)
            await ctx.author.send('Các tag đã được thêm:', embed=embed)

    @commands.command(brief="Đổi tên tag")
    @commands.check_any(commands.is_owner(), commands.has_any_role('Admin', 'Mod VNOI'))
    async def modify(self, ctx, old_tag, new_tag):
        old_tag = TaggingDb.normalize_tag(old_tag)
        new_tag = TaggingDb.normalize_tag(new_tag)
        s = TaggingDb.TaggingDb.rename(old_tag, new_tag)
        if s is not None:
            embed = discord_common.embed_alert(s)
            await ctx.author.send(embed=embed)
        await ctx.author.send(f'Đã đổi tên tag {old_tag} sang {new_tag}')

    @commands.command(brief="Thêm tag vào bài .",
                      usage="[tag1] [tag2] [tag3] ... \"comment\"")
    async def add(self, ctx, *args):
        """
        Thêm tag vào bài, lưu ý các tag cần cách nhau bởi space. comment cần được đặt vào giữa 2 dấu \"\".
        Ví dụ: `;add dp-tree bitset dsu-general `\n
        Hoặc: `;add dp-tree \"bài này tuy tag dp-tree nhưng có thể làm thuật toán tham lam tốt hơn\"` (comment cần có ít nhất 3 từ)
        """
        current_problem = codeforces_api.get_current_problem(ctx.author.id)
        if current_problem is None:
            await ctx.author.send(f"{ctx.author.mention} chưa được phân công bài nào <:sadness:662197924918329365>," +
                                  "hãy dùng lệnh `;get` để được phân công bài <:dad:661181642802724894>.")
            return
        problem_short_link = current_problem['short_link']
        # parse arg
        params = parser.tag_parse(args)
        if isinstance(params, str):
            embed = discord_common.embed_alert(params)
            await ctx.author.send(embed=embed)
            return
        tags, comment = params
        msg = ""
        any_error = False
        for tag in tags:
            tag = TaggingDb.normalize_tag(tag)
            # get tag
            real_tag = await helper.tag.get_similar_tag(ctx, tag)
            if real_tag is None:
                any_error = True
                continue

            TaggingDb.TaggingDb.tagging(problem_short_link, real_tag, ctx.author.id)

            msg += '\n-`{}` (giống `{}`).'.format(real_tag, tag)
        if len(msg) != 0:
            await ctx.author.send('Các tag đã tìm thấy:', embed=discord_common.embed_success(msg))
        if comment == parser._COMMENT_LENGTH_MSG:
            embed = discord_common.embed_alert("Comment cần có ít nhất 3 từ")
            await ctx.send(embed=embed)
        elif len(comment) > 0:
            TaggingDb.TaggingDb.commenting(problem_short_link, comment, ctx.author.id)
        # --------------------------------------------------------------
        embed = problem_to_embed(current_problem, ctx.author.id)
        if any_error:
            await ctx.author.send('Thông tin hiện tại của bài:', embed=embed)
        else:
            await ctx.author.send('Nếu tag xong rồi bạn có thể dùng `;done` để lấy bài tập mới.'
                                  'Thông tin hiện tại của bài:', embed=embed)

    @commands.command(brief="Lấy bài tập mới")
    async def get(self, ctx):
        handle = TaggingDb.TaggingDb.get_handle(ctx.author.id)
        if handle is None:
            await ctx.author.send(f"Không tìm được codeforces handle của {ctx.author.mention} <:sadness:662197924918329365>."
                                  "Hãy dùng lệnh `identify` trước")
            return
        problem = await codeforces_api.get_problem(handle, ctx.author.id)
        if problem is None:
            await ctx.author.send(f"Không tìm được bài nào phù hợp cho {ctx.author.mention} <:sadness:662197924918329365>")
            return

        current_problem = codeforces_api.get_current_problem(ctx.author.id)
        if current_problem is not None:
            # todo done info
            embed = problem_to_embed(current_problem, ctx.author.id)
            await ctx.author.send('Thông tin của bài tập hiện tại', embed=embed)
            return
        await handle_new_problem(ctx, problem)

    @commands.command(brief="Chọn một bài tập")
    async def pick(self, ctx, link):
        """
            Tự chọn một bài tập để tag, yêu cầu bài này phải AC trước đó rồi
            ;pick 1339B
            ;pick https://codeforces.com/problemset/problem/1339/B
            ;pick https://codeforces.com/contest/1339/problem/B
        """
        handle = TaggingDb.TaggingDb.get_handle(ctx.author.id)
        if handle is None:
            await ctx.author.send(f"Không tìm được codeforces handle của {ctx.author.mention} <:sadness:662197924918329365>."
                                  "Hãy dùng lệnh `identify` trước")
            return
        short_link = parser.link_parse(link)
        if short_link is None:
            await ctx.author.send(f"Format link không đúng, vui lòng dùng 1 trong 3 format sau:\n"
                                  ";pick 1339B\n"
                                  ";pick https://codeforces.com/problemset/problem/1339/B\n"
                                  ";pick https://codeforces.com/contest/1339/problem/B\n")
            return
        problem = await codeforces_api.pick(handle, ctx.author.id, short_link)
        if problem == codeforces_api._IS_TAGGED:
            await ctx.author.send(f"Bài đã được tag")
            return
        if problem == codeforces_api._NOT_FOUND:
            await ctx.author.send(f"Không tìm được bài {short_link}, khả năng là bạn chưa AC" +
                                  "nếu đã AC vui lòng tag @Cá Nóc Cắn Cáp để hỗ trợ")
            return
        if problem == codeforces_api._RATING_TOO_LOW:
            await ctx.author.send(f"Không được chọn bài có rating bé hơn {codeforces_api._LIM_RATING}")
            return
        current_problem = codeforces_api.get_current_problem(ctx.author.id)
        if current_problem is not None:
            embed = problem_to_embed(current_problem, ctx.author.id)
            is_tagged = TaggingDb.TaggingDb.is_tagged(current_problem['short_link'], ctx.author.id)
            if is_tagged:
                await self.log_channel.send(f"Đội ơn bạn {ctx.author.mention} <:orz:661153248186597386> đã làm xong bài:", embed=embed)
                TaggingDb.TaggingDb.done(ctx.author.id, current_problem['short_link'])
                submission_link = SUBMISSION_BASE_URL.format(current_problem['short_link'].split('/')[0], current_problem['submission_id'])
                TaggingDb.TaggingDb.add_submission(current_problem['short_link'], submission_link, ctx.author.id)
                codeforces_api.set_current_problem(ctx.author.id, None)
            else:
                await ctx.author.send("Đã bỏ qua bài tập:", embed=embed)
                codeforces_api.set_current_problem(ctx.author.id, None, skip=False)
        # -----------------------------------------------------------
        await handle_new_problem(ctx, problem)

    @commands.command(brief="Xóa tag bị add nhầm")
    async def remove(self, ctx, *args):
        """
        Xóa tag đã add vào bài, param giống add
        Ví dụ ;remove dp-tree bitset
        """
        current_problem = codeforces_api.get_current_problem(
            ctx.author.id)
        if current_problem is None:
            await ctx.author.send(f"{ctx.author.mention} chưa được phân công bài nào <:sadness:662197924918329365>,"
                                  "hãy dùng lệnh `;get` để được phân công bài.")
            return
        problem_short_link = current_problem['short_link']
        # parse arg
        params = parser.tag_parse(args, True)
        if isinstance(params, str):
            embed = discord_common.embed_alert(params)
            await ctx.author.send(embed=embed)
            return
        tags, comment = params
        msg = ""
        for tag in tags:
            tag = TaggingDb.normalize_tag(tag)
            # get tag
            real_tag = await helper.tag.get_similar_tag(ctx, tag)
            if real_tag is None:
                continue

            TaggingDb.TaggingDb.remove_tag(problem_short_link, real_tag, ctx.author.id)

            msg += '\n-`{}` (giống `{}`).'.format(real_tag, tag)
        if len(msg) != 0:
            await ctx.author.send('Các tag đã tìm thấy:', embed=discord_common.embed_success(msg))

        embed = problem_to_embed(current_problem, ctx.author.id)
        await ctx.author.send('Thông tin hiện tại của bài:', embed=embed)

    @commands.command(brief="Hoàn thành bài.")
    async def done(self, ctx):
        """
        Hoàn thành bài tập đang làm
        Ví dụ ;done
        sẽ hoàn thành việc tag bài hiện tại và được lấy bài mới
        """
        current_problem = codeforces_api.get_current_problem(ctx.author.id)
        if current_problem is None:
            await ctx.author.send(f"{ctx.author.mention} chưa được phân công bài nào <:sadness:662197924918329365>,"
                                  "hãy dùng lệnh `;get` để được phân công bài.")
            return
        embed = problem_to_embed(current_problem, ctx.author.id)

        is_tagged = TaggingDb.TaggingDb.is_tagged(current_problem['short_link'], ctx.author.id)
        # is_commented = TaggingDb.TaggingDb.check_exists(
        #     'commented', 'problem', current_problem['short_link'])
        if not is_tagged:
            await ctx.author.send("Bạn ơi bài này chưa đc tag ư ư, nếu bạn muốn bỏ qua thì `skip` nha :heart:, các thông tin:", embed=embed)
            return
        await self.log_channel.send(f"Đội ơn bạn {ctx.author.mention} <:orz:661153248186597386> đã làm xong bài:", embed=embed)
        TaggingDb.TaggingDb.done(ctx.author.id, current_problem['short_link'])
        submission_link = SUBMISSION_BASE_URL.format(current_problem['short_link'].split('/')[0], current_problem['submission_id'])
        TaggingDb.TaggingDb.add_submission(current_problem['short_link'], submission_link, ctx.author.id)
        codeforces_api.set_current_problem(ctx.author.id, None)
        await self.get(ctx)

    @commands.command(brief="Bỏ qua bài")
    async def skip(self, ctx, *args):
        """
        Bỏ quả bài tập đang làm
        Ví dụ ;skip
        sẽ hoàn thành việc tag bài hiện tại và được lấy bài mới
        """
        current_problem = codeforces_api.get_current_problem(ctx.author.id)
        if current_problem is None:
            await ctx.author.send(f"{ctx.author.mention} chưa được phân công bài nào <:sadness:662197924918329365>,"
                                  "hãy dùng lệnh `;get` để được phân công bài.")
            return
        embed = problem_to_embed(current_problem, ctx.author.id)

        is_tagged = TaggingDb.TaggingDb.is_tagged(current_problem['short_link'], ctx.author.id)
        # is_commented = TaggingDb.TaggingDb.check_exists(
        #     'commented', 'problem', current_problem)
        if is_tagged:
            await ctx.author.send("Bạn ơi bài này đã được tag nên không `skip` được nha,"
                                  "hãy dùng `done` <:aquanice:692418002007883836>, các thông tin:", embed=embed)
            return
        await ctx.author.send("Đã bỏ qua bài tập:", embed=embed)
        codeforces_api.set_current_problem(ctx.author.id, None)
        await self.get(ctx)

    @commands.command(brief="Lấy danh sách các bài cùng tag.",
                      usage="[tag]")
    @commands.check_any(commands.is_owner(), commands.has_any_role('Admin', 'Mod VNOI'))
    async def info(self, ctx, tag):
        """
        Lấy danh sách các bài có tag cho trước
        Ví dụ ;info dp-tree
        """
        tag = TaggingDb.normalize_tag(tag)
        # ----------------------------
        # get tag
        real_tag = await helper.tag.get_similar_tag(ctx, tag)
        if real_tag is None:
            return
        await ctx.author.send('Tìm thấy tag `{}` giống với `{}`.'.format(real_tag, tag))

        problems = TaggingDb.TaggingDb.get_tagged(real_tag)
        if len(problems) == 0:
            await ctx.author.send('Chưa có bài nào thuộc tag `{}`'.format(real_tag))
            return
        msg = ""
        for p in problems:
            link = short_link_to_msg(p[0])
            msg += f"[link]({link})\n"
        embed = discord.Embed(description=msg.strip())
        await ctx.author.send('Các bài thuộc tag `{}`'.format(real_tag), embed=embed)


def setup(bot):
    bot.add_cog(Tag(bot))
