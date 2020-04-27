# source: https://github.com/cheran-senthil/TLE/blob/a9848810344ae29ec30a5fb708783844bbbd6129/tle/util/py
import unicodedata

FULL_WIDTH = 1.66667
WIDTH_MAPPING = {'F': FULL_WIDTH, 'H': 1, 'W': FULL_WIDTH, 'Na': 1, 'N': 1, 'A': 1}


def width(s):
    return round(sum(WIDTH_MAPPING[unicodedata.east_asian_width(c)] for c in s))


def make_table(tags):
    nTag = len(tags)
    if nTag <= 10:
        style = Style('{:>}  {:<}')
        t = Table(style)
        t += Header('#', 'Tag')
        t += Line()
        for index, tag in enumerate(tags):
            t += Data(index + 1, tag)
        return t
    elif nTag <= 20:
        style = Style('{:>}  {:<}  {:>}  {:<}')
        t = Table(style)
        t += Header('#', 'Tag', '#', 'Tag')
        t += Line()
        for i in range(0, 10):
            if (i + 10 < nTag):
                t += Data(i + 1, tags[i], i + 10 + 1, tags[i + 10])
            else:
                t += Data(i + 1, tags[i], '', '')
        return t
    elif nTag <= 30:
        style = Style('{:>}  {:<}  {:>}  {:<}  {:>}  {:<}')
        t = Table(style)
        t += Header('#', 'Tag', '#', 'Tag', '#', 'Tag')
        t += Line()
        for i in range(0, 10):
            if (i + 20 < nTag):
                t += Data(i + 1, tags[i], i + 10 + 1, tags[i + 10], i + 20 + 1, tags[i + 20])
            else:
                t += Data(i + 1, tags[i], i + 10 + 1, tags[i + 10], '', '')
        return t
    raise ValueError


class Content:
    def __init__(self, *args):
        self.data = args

    def sizes(self):
        return [width(str(x)) for x in self.data]

    def __len__(self):
        return len(self.data)


class Header(Content):
    def layout(self, style):
        return style.format_header(self.data)


class Data(Content):
    def layout(self, style):
        return style.format_body(self.data)


class Line:
    def __init__(self, c='-'):
        self.c = c

    def layout(self, style):
        self.data = [''] * style.ncols
        return style.format_line(self.c)


class Style:
    def __init__(self, body, header=None):
        self._body = body
        self._header = header or body
        self.ncols = body.count('}')

    def _pad(self, data, fmt):
        S = []
        lastc = None
        size = iter(self.sizes)
        datum = iter(data)
        for c in fmt:
            if lastc == ':':
                dstr = str(next(datum))
                sz = str(next(size) - (width(dstr) - len(dstr)))
                if c in '<>^':
                    S.append(c + sz)
                else:
                    S.append(sz + c)
            else:
                S.append(c)
            lastc = c
        return ''.join(S)

    def format_header(self, data):
        return self._pad(data, self._header).format(*data)

    def format_line(self, c):
        data = [''] * self.ncols
        return self._pad(data, self._header).replace(':', ':' + c).format(*data)

    def format_body(self, data):
        return self._pad(data, self._body).format(*data)

    def set_colwidths(self, sizes):
        self.sizes = sizes


class Table:
    def __init__(self, style):
        self.style = style
        self.rows = []

    def append(self, row):
        self.rows.append(row)
        return self
    __add__ = append

    def __repr__(self):
        sizes = [row.sizes() for row in self.rows if isinstance(row, Content)]
        max_colsize = [max(s[i] for s in sizes) for i in range(self.style.ncols)]
        self.style.set_colwidths(max_colsize)
        return '\n'.join(row.layout(self.style) for row in self.rows)
    __str__ = __repr__
