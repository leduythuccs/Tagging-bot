def tag_parse(args):
    if len(args) == 0:
        return 'Thiếu param rồi. Gõ `;tag help add` đê'
    tags = args
    comment = ""
    if args[-1].count(' ') != 0:
        comment = args[-1]
        tags = args[:-1]
    return tags, comment
