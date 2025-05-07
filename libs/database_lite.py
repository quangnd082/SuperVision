import time
import sqlite3
from sqlite3 import Error, IntegrityError
from datetime import datetime

# from constant import *

def create_db(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        pass

    return conn

def create_table(conn,create_table_sql):
    '''
    'CREATE TABLE IF NOT EXISTS table_name(
        column_1 data_type PRIMARY KEY,
   	    column_2 data_type NOT NULL,
	    column_3 data_type DEFAULT 0
    )'
    '''
    c = conn.cursor()
    c.execute(create_table_sql)

def insert(conn,insert_table_sql,values):
    '''
    'INSERT INTO table_name (column1,column2 ,..)
    VALUES (?,?,..)'
    '''
    cur = conn.cursor()
    cur.execute(insert_table_sql,values)
    conn.commit()
    pass
def update(conn,update_table_sql,values):
    ''' UPDATE tasks
              SET priority = ? ,
                  begin_date = ? ,
                  end_date = ?
              WHERE id = ?'''
    cur = conn.cursor()
    cur.execute(update_table_sql,values)
    conn.commit()
    pass

def select(conn,select_table_sql,key=None):
    ''' 'SELECT * FROM table WHERE id = ?' '''
    cur = conn.cursor()
    if key :
        obj = cur.execute(select_table_sql,key)
    else:
        obj = cur.execute(select_table_sql)
    rows = obj.fetchall()
    return rows

def delete(conn,delete_sql,key=None):
    '''DELETE * FROM mytable WHERE key=?'''
    cur = conn.cursor()
    if key is not None:
        cur.execute(delete_sql,key)
    else:
        cur.execute(delete_sql)
    conn.commit()
    pass


class MyDataBase():
    '''
    Count total, pass, fail and rate for model in history table
    '''
    def __init__(self, db_path, model="") -> None:
        self._path = db_path
        self._model = model
        self._n_pass = 0
        self._n_fail = 0
        self._n_total = 0
        self._rate = 0.0
        self._date_created = None
        self._last_time = None
    
    @property
    def n_total(self):
        return self._n_total
    
    @property
    def n_pass(self):
        return self._n_pass
    
    @property
    def n_fail(self):
        return self._n_fail
    
    @property
    def rate(self):
        return self._rate
    
    @property
    def path(self):
        return self._path
    
    @property
    def model(self):
        return self._model
    
    def set_model(self, model):
        self._model = model
        self.on_init()
    
    def update(self):
        '''
        update total, pass, fail, rate when history append new row
        '''
        # t0 = time.time()

        # conn = create_db(self._path)
        # model = self._model
        # if conn:
            # sql = "select result from history where model=? order by timecheck desc limit 1"
            # last_row = select(conn, sql, (model, ))
        last_row = self.get_last_row()
        if last_row:
            result = int(last_row[-3])
            timecheck = last_row[-2]
            if timecheck != self._last_time:
                self._last_time = timecheck
                if result == PASS:
                    self._n_pass += 1
                else:
                    self._n_fail += 1
                self._n_total = self._n_pass + self._n_fail
                self._rate = self._n_pass / self._n_total if self._n_total != 0 else 0.0
        pass
    
    def on_init(self):
        '''
        on init n total, pass, fail and rate 
        '''
        # t0 = time.time()
        conn = create_db(self._path)
        model = self._model
        if conn:
            cur_time = datetime.now().strftime(DATETIME_FORMAT)
            data = self.get_info_range('2000-01-01 00:00:00', cur_time)
            # self.
            self._n_pass = data["pass"]
            self._n_fail = data["fail"]
            self._n_total = data["total"]
            self._rate = data["rate"]
            self._last_time = self.get_last_time()

            sql = "select * from models where model=?"
            row = select(conn, sql, (model, ))
            if row:
                self._date_created = row[0][1]
        # dt = time.time() - t0
        # print("time for get info: %d ms" % (dt*1000))

    def get_last_row(self):
        conn = create_db(self._path)
        model = self._model
        sql = "select * from history where model=? order by timecheck desc limit 1"
        last_row = select(conn, sql, (model, ))
        if last_row:
            last_row = last_row[0]
            return last_row
    
    def get_last_time(self):
        last_row = self.get_last_row()
        if last_row:
            return last_row[-2]
        
    def get_info_range(self, from_time:str, to_time:str) -> dict:
        if not self._model:
            return {}
        conn = create_db(self._path)
        model = self._model
        if conn:
            sql = "select count(*) from history where model=? and result = ? and (timecheck between ? and ?)"
            n_pass = select(conn, sql, (model, 1, from_time, to_time))[0][0]

            sql = "select count(*) from history where model=? and result=? and (timecheck between ? and ?)"
            n_fail = select(conn, sql, (model, 0, from_time, to_time))[0][0]

            n_total = n_pass + n_fail

            rate = n_pass / n_total if n_total != 0 else 0.0
            rate = round(rate, 2)

            return{
                "total": n_total,
                "pass": n_pass,
                "fail": n_fail,
                "rate": rate
            }
        
    def get_info_on_day(self) -> dict:
        cur_day = datetime.now()
        from_time = cur_day.strftime("%Y-%m-%d 00:00:00")
        to_time = cur_day.strftime("%Y-%m-%d %H:%M:%S")

        return self.get_info_range(from_time, to_time)

    def get_info(self) -> dict:
        '''
        return information about total, pass, fail and rate
        '''
        return {
            "total": self._n_total,
            "pass": self._n_pass,
            "fail": self._n_fail,
            "rate": round(self._rate, 2),
            "model": self._model,
            "created": self._date_created
        }
    
    def get_data(self) -> list:
        '''
        return all rows in history table of model
        '''
        if not self._model:
            return []
        conn = create_db(self._path)
        model = self._model
        sql = "select * from history where model=?"

        total_rows = select(conn, sql, (model, ))
        return total_rows

if __name__ == '__main__':
    import random
    import time
    models = ["TEST", "EXAMPLE"]

    # fake data
    db = create_db(DATABASE_PATH)
    for i in range(100000):
        index = random.randint(0, len(models) - 1)
        model = models[index]

        result = random.randint(0, 1)

        timecheck = time.strftime(DATETIME_FORMAT)

        val = im_path = ""

        data = (
            model, result, val, timecheck, im_path
        )
        sql = "insert into history values(?,?,?,?,?)"
        insert(db, sql, data)
        print(data)
    pass