# type: ignore
from helper import config
from helper import TaggingDb
from helper import table
from helper import discord_common
import json
_LCS_THRESHOLD_ = config.config.get("LCS_THRESHOLD")


async def get_similar_tag(ctx, tag):
    _LV1_TAGS = json.load(open('database/detailed_suggestions.json', encoding='utf-8'))
    if tag in _LV1_TAGS:
        name = _LV1_TAGS[tag]['name']
        tag_codes = _LV1_TAGS[tag]['codes']
        try:
            t = table.make_table(tag_codes)
        except ValueError:
            raise ValueError(f"Tag {name} is too long, expected length <= 30, found {len(tag_codes)}")

        table_str = f'```yml\n{t}\n```'
        await ctx.author.send(f'Bạn có thể ghi chi tiết hơn về tag `{name}` được không <:blowop:665243570696880129>? '
                              'Dưới đây là list một số tag có thể liên quan\n' + table_str)
        return

    similar = TaggingDb.TaggingDb.get_similar_tag(tag)
    if len(similar) == 0:
        embed = discord_common.embed_alert(
            'Không tìm thấy tag `{}`'.format(tag))
        await ctx.author.send(embed=embed)
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
            await ctx.author.send(msg, embed=embed)
            return
        await ctx.author.send(msg)
        return
    return similar[0][1]
