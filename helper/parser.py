import re
_COMMENT_LENGTH_MSG = -1
def tag_parse(args, is_remove = False):
    if len(args) == 0:
        if is_remove:
            return 'Thiếu param rồi. Gõ `;help remove` đê'
        return 'Thiếu param rồi. Gõ `;help add` đê'
    tags = args
    comment = ""
    if args[-1].count(' ') != 0:
        comment = args[-1]
        tags = args[:-1]
    comment = comment.strip()
    if len(comment) != 0 and comment.count(' ') < 2:
        comment = _COMMENT_LENGTH_MSG
    return tags, comment
# ;pick 1339B
# ;pick https://codeforces.com/problemset/problem/1339/B
# ;pick https://codeforces.com/contest/1339/problem/B
def link_parse(link):
    p1 = r'problemset/problem/(\d+)/(\w+)'
    s = re.findall(p1, link)
    if len(s) != 0:
        return s[0][0] + '/' + s[0][1]
    p2 = r'contest/(\d+)/problem/(\w+)'
    s = re.findall(p2, link)
    if len(s) != 0:
        return s[0][0] + '/' + s[0][1]
    p3 = r'(\d+)(\w+)'
    s = re.findall(p3, link)
    if len(s) != 0:
        return s[0][0] + '/' + s[0][1]
    return None
    