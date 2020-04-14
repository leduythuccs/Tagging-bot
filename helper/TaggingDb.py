import sqlite3
import csv
import unicodedata
def normalize_tag(tag):
    tag = unicodedata.normalize('NFC', tag)
    tag = tag.strip()
    while (tag.find('  ') != -1):
        tag = tag.replace('  ', ' ')
    tag = tag.lower()
    return tag
def LCS(a: str, b: str):
    m = len(a)
    n = len(b)
    L = [[0]*(n + 1) for i in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                L[i][j] = L[i - 1][j - 1] + 1
            else:
                L[i][j] = max(L[i - 1][j], L[i][j - 1])
    return L[m][n]
class TaggingDbConn:
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.create_table()

    def create_table(self):
        self.conn.execute(
            'CREATE TABLE IF NOT EXISTS tag_info ('
            'id             INTEGER PRIMARY KEY AUTOINCREMENT,'
            'tag            TEXT'
            ')'
        )

        self.conn.execute(
            'CREATE TABLE IF NOT EXISTS tagged ('
            'id             INTEGER,'
            'problem_link   TEXT,'
            'code_link      TEXT,'
            'diff           TEXT'
            ')'
        )

    def check_exists(self, table, where, value):
        query = (
            'SELECT 1 '
            'FROM {0} '.format(table) +
            'WHERE {0} = ?'.format(where)
        )
        res = self.conn.execute(query, (value, )).fetchone()
        return res is not None


    def add_tag(self, tag):
        assert self.check_exists('tag_info', 'tag', tag) == False, f"Tag {tag} đã tồn tại"
        cur = self.conn.cursor()
        query = (
            'INSERT INTO tag_info (tag) '
            'VALUES (?)'
        )
        cur.execute(query, (tag, ))
        self.conn.commit()
        return cur.lastrowid

    def get_similar_tag(self, tag):
        tag_table = self.get_data('tag_info', limit=None)
        similar = []
        for id, tag_name in tag_table:
            similar.append((LCS(tag, tag_name), -len(tag_name), tag_name))
        # sort by LCS
        # if there are many tag_names with the same LCS, 
        # sort them by length (shorter is better)
        similar.sort(reverse=True)
        similar = list(map(lambda x: (x[0], x[2]), similar))
        return similar
        
    def get_tag_id(self, tag):
        query = (
            'SELECT id '
            'FROM tag_info '
            'WHERE tag = ?'
        )
        res = self.conn.execute(query, (tag, )).fetchone()
        return res[0] if res is not None else None
    def get_tagged(self, tag):
        id = self.get_tag_id(tag)
        assert tag is not None
        query = (
            'SELECT problem_link, code_link, diff '
            'FROM tagged '
            'WHERE id = ?'
        )
        return self.conn.execute(query, (id, )).fetchall()

    def tagging(self, tag, problem_link, code_link, diff):
        id = self.get_tag_id(tag)
        assert tag is not None

        query = (
            'INSERT INTO tagged (id, problem_link, code_link, diff) '
            'VALUES (?, ?, ?, ?)'
        )

        self.conn.execute(query, (id, problem_link, code_link, diff))
        self.conn.commit()
    
    #for local debug
    def get_data(self, table, limit = 10):
        query = (
            'SELECT * '
            'FROM {0} '.format(table)
        )
        if limit is not None:
            query +=  'LIMIT {0}'.format(limit)
        x = self.conn.execute(query).fetchall()
        return x


TaggingDb = TaggingDbConn('database/tagging.db')