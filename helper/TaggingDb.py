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
            'CREATE TABLE IF NOT EXISTS user_tag_rank ('
            'discord_id     TEXT,'
            'problem    TEXT'
            ')'
        )
        self.conn.execute(
            'CREATE TABLE IF NOT EXISTS cnt_tagged ('
            'problem    TEXT,'
            'cnt        INTEGER'
            ')'
        )
        self.conn.execute(
            'CREATE TABLE IF NOT EXISTS tagged ('
            'problem    TEXT,'
            'tag        TEXT,'
            'discord_id TEXT'
            ')'
        )
        self.conn.execute(
            'CREATE TABLE IF NOT EXISTS submission ('
            'problem        TEXT,'
            'link           TEXT,'
            'discord_id     INTEGER'
            ')'
        )
        self.conn.execute(
            'CREATE TABLE IF NOT EXISTS commented ('
            'problem    TEXT,'
            'comment    TEXT,'
            'discord_id TEXT'
            ')'
        )
        self.conn.execute(
            'CREATE TABLE IF NOT EXISTS user ('
            'discord_id         TEXT,'
            'handle             TEXT'
            ')'
        )
        self.conn.execute(
            'CREATE TABLE IF NOT EXISTS tagging ('
            'problem            TEXT'
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
    def add_submission(self, problem, link, discord_id):
        cur = self.conn.cursor()
        query = (
            'INSERT INTO submission (problem, link, discord_id) '
            'VALUES (?, ?, ?)'
        )
        cur.execute(query, (problem, link, discord_id))
        self.conn.commit()
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
    def done(self, discord_id, problem):
        query = (
            'INSERT INTO user_tag_rank (discord_id, problem) '
            'VALUES (?, ?)'
        )
        self.conn.execute(query, (discord_id, problem))
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

    def get_all_problem_tag(self, problem):
        query = (
            'SELECT tag, discord_id '
            'FROM tagged '
            'WHERE problem = ?'
        )
        res = self.conn.execute(query, (problem, )).fetchall()
        return res
    def is_tagged(self, problem, discord_id):
        x = self.get_problem_tag(problem, discord_id)
        return x is not None and len(x) != 0
    def get_problem_tag(self, problem, discord_id):
        query = (
            'SELECT tag '
            'FROM tagged '
            'WHERE problem = ? AND discord_id = ?'
        )
        res = self.conn.execute(query, (problem, discord_id)).fetchall()
        return list(map(lambda x: x[0], res))
    def get_problem_comment(self, problem, discord_id):
        query = (
            'SELECT comment '
            'FROM commented '
            'WHERE problem = ? AND discord_id = ?'
        )
        res = self.conn.execute(query, (problem, discord_id)).fetchall()
        return list(map(lambda x: x[0], res))

    def get_similar_tag(self, tag):
        tag_table = self.get_data('tag_info', limit=None)
        similar = []
        for id, tag_name in tag_table:
            similar.append((LCS(tag, tag_name) / max(len(tag_name), len(tag)) , tag_name))
        # sort by LCS
        # if there are many tag_names with the same LCS, 
        # sort them by length (shorter is better)
        similar.sort(reverse=True)
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
        
    def rename(self, old_tag, new_tag):
        if not self.check_exists('tag_info', 'tag', old_tag):
            return f"Không tìm thấy tag {old_tag}"
        if self.check_exists('tag_info', 'tag', new_tag):
            return f"Tag {new_tag} đã có trong dữ liệu"
        query = (
            'UPDATE tag_info '
            'SET tag = ? '
            'WHERE tag = ?'
        )
        self.conn.execute(query, (new_tag, old_tag))
        query = (
            'UPDATE tagged '
            'SET tag = ? '
            'WHERE tag = ?'
        )
        self.conn.execute(query, (new_tag, old_tag))
        self.conn.commit()
        return
    def tagging(self, problem, tag, discord_id):
        id = self.get_tag_id(tag)
        assert tag is not None
        query = (
            'SELECT 1 '
            'FROM tagged '
            'WHERE problem = ? AND tag = ? AND discord_id = ?'
        )
        if self.conn.execute(query, (problem, tag, discord_id)).fetchone() is not None:
            return
        query = (
            'INSERT INTO tagged (problem, tag, discord_id) '
            'VALUES (?, ?, ?)'
        )
        self.conn.execute(query, (problem, tag, discord_id))
        self.conn.commit()
    def remove_tag(self, problem, tag, discord_id):
        id = self.get_tag_id(tag)
        assert tag is not None

        query = (
            'DELETE FROM tagged '
            'WHERE problem = ? AND tag = ? AND discord_id = ?'
        )
        self.conn.execute(query, (problem, tag, discord_id))
        self.conn.commit()
    
    def commenting(self, problem, comment, discord_id):
        comment = comment.strip()
        query = (
            'SELECT 1 '
            'FROM commented '
            'WHERE problem = ? AND comment = ? AND discord_id = ?'
        )
        if self.conn.execute(query, (problem, comment, discord_id)).fetchone() is not None:
            return

        query = (
            'INSERT INTO commented (problem, comment, discord_id) '
            'VALUES (?, ?, ?)'
        )
        self.conn.execute(query, (problem, comment, discord_id))
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
