
CF_DIFF = ['D1A', 'D1B', 'D1C', 'D1D', 'D1E']

def tag_parse(args):
    if len(args) < 4:
        return 'Thiếu param rồi. Gõ `;tag help add` đê'
    diff = args[-1]
    if diff.upper() not in CF_DIFF:
        return 'Độ khó (`{}`) phải theo format codeforces [D1A, D1B, ... D1E].'.format(diff)
    link_code = args[-2]
    if link_code[:4] != 'http':
        return 'Link code (`{}`) phải bắt đầu bằng `http`.'.format(link_code)
    link_problem = args[-3]
    if link_problem[:4] != 'http':
        return 'Link code (`{}`) phải bắt đầu bằng `http`.'.format(link_problem)
    tag = ' '.join(args[:-3])
    return tag, link_problem, link_code, diff