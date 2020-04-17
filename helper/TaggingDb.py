import sqlite3
import csv
import unicodedata
def normalize_tag(tag):
    tag = unicodedata.normalize('NFC', tag)
    tag = tag.strip()
    while (tag.find('  ') != -1):
        tag = tag.replace('  ', ' ')
    tag = tag.lower()
    if tag == "treap" or tag == "splay":
        tag = "treap/splay"
    if tag == "fft" or tag == "ntt":
        tag = "fft/ntt"
    if tag == "dfs" or tag == "bfs":
        tag = "dfs/bfs"
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
            'problem    TEXT,'
            'tag        TEXT'
            ')'
        )
        self.conn.execute(
            'CREATE TABLE IF NOT EXISTS commented ('
            'problem    TEXT,'
            'comment    TEXT'
            ')'
        )
        self.conn.execute(
            'CREATE TABLE IF NOT EXISTS user ('
            'discord_id         TEXT,'
            'handle             TEXT,'
            'current_problem    TEXT'
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

    def add_handle(self, discord_id, handle):
        if self.check_exists('user', 'discord_id', discord_id):
            query = (
                'UPDATE user '
                'SET handle = ? '
                'WHERE discord_id = ?'
            )
        else:
            query = (
                'INSERT INTO user (handle, discord_id) '
                'VALUES (?, ?)'
            )
        self.conn.execute(query, (handle, discord_id))
        self.conn.commit()
    def get_handle(self, discord_id):
        query = (
            'SELECT handle '
            'FROM user '
            'WHERE discord_id = ?'
        )
        res = self.conn.execute(query, (discord_id, )).fetchone()
        if res is None or res[0] is None:
            return None
        return res[0]
    def get_current_problem(self, discord_id):
        query = (
            'SELECT current_problem '
            'FROM user '
            'WHERE discord_id = ?'
        )
        res = self.conn.execute(query, (discord_id, )).fetchone()
        if res is None or res[0] is None:
            return None
        return res[0]
    def set_current_problem(self, discord_id, problem):
        query = (
            'UPDATE user '
            'SET current_problem = ? '
            'WHERE discord_id = ?'
        )
        self.conn.execute(query, (problem, discord_id)).fetchone()
        self.conn.commit()
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
            similar.append((LCS(tag, tag_name) / max(len(tag_name), len(tag)) , tag_name))
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
            'SELECT problem '
            'FROM tagged '
            'WHERE tag = ?'
        )
        return self.conn.execute(query, (tag, )).fetchall()

    def tagging(self, problem, tag):
        id = self.get_tag_id(tag)
        assert tag is not None

        query = (
            'INSERT INTO tagged (problem, tag) '
            'VALUES (?, ?)'
        )
        self.conn.execute(query, (problem, tag))
        self.conn.commit()
    def remove_tag(self, problem, tag):
        id = self.get_tag_id(tag)
        assert tag is not None

        query = (
            'DELETE FROM tagged '
            'WHERE problem = ? AND tag = ?'
        )
        self.conn.execute(query, (problem, tag))
        self.conn.commit()
    
    def commenting(self, problem, comment):
        query = (
            'INSERT INTO commented (problem, comment) '
            'VALUES (?, ?)'
        )
        self.conn.execute(query, (problem, comment))
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