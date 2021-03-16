#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio, logging
# MySQL数据库异步IO的驱动
import aiomysql

# 打印SQL日志函数
def log(sql, args=()):
    logging.info('SQL: %s' % sql)

# 创建数据库连接池
async def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    # 全局变量__pool 连接池
    # 使用连接池的好处是不必频繁地打开和关闭数据库连接，而是能复用就尽量复用。
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'), #IP
        port=kw.get('port', 3306), # 端口
        user=kw['user'], # 用户名
        password=kw['password'], # 密码
        db=kw['db'], # 要连接的数据库
        charset=kw.get('charset', 'utf8'), # 字符集
        autocommit=kw.get('autocommit', True), # 自动提交
        maxsize=kw.get('maxsize', 10), # 最大数
        minsize=kw.get('minsize', 1), # 最小数
        loop=loop # EventLoop
    )

# 查询
async def select(sql, args, size=None):
    # 打印SQL日志
    log(sql, args)
    global __pool
    async with __pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # SQL语句的占位符是?，而MySQL的占位符是%s，select()函数在内部自动替换。
            # 注意要始终坚持使用带参数的SQL，而不是自己拼接SQL字符串，这样可以防止SQL注入攻击。
            await cur.execute(sql.replace('?', '%s'), args or ())
            # 如果传入size参数，就通过fetchmany()获取最多指定数量的记录，否则，通过fetchall()获取所有记录
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs))
        return rs

# 执行Insert, Update, Delete语句
async def execute(sql, args, autocommit=True):
    log(sql)
    async with __pool.get() as conn:
        # 如果 autocommit 为False，等待执行 conn.begin()
        if not autocommit:
            await conn.begin()
        try:
            # 获取连接数据库的游标
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 执行语句
                await cur.execute(sql.replace('?', '%s'), args)
                # 获取影响行数
                affected = cur.rowcount
            # 如果autocommit 为 False，提交
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            # 如果autocommit 为 False，回滚
            if not autocommit:
                await conn.rollback()
            raise
        #返回影响的行数
        return affected

# 创建 参数列表字符串 的工具类
# num 为创建？的数量
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)


# Field 字段 及其 子类
class Field(object):
    # 初始化
    def __init__(self, name, column_type, primary_key, default):
        self.name = name # 名字
        self.column_type = column_type # 字段类型
        self.primary_key = primary_key # 主键
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)



# 模板元类 是类的模板，所以必须从`type`类型派生：
class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):
        if name=='Model':
            return type.__new__(cls, name, bases, attrs)
        # 获取 表名
        tableName = attrs.get('__table__', None) or name
        # 打印 类名 和表名
        logging.info('found model: %s (table: %s)' % (name, tableName))
        
        mappings = dict() # 空字典
        fields = [] # 字段数组
        primaryKey = None # 是否为关键字段
        # 把 attrs属性集合 中属于 Field类的属性 添加到 fields[]
        for k, v in attrs.items():
            # 是否为 Field 类
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    # 找到主键:
                    if primaryKey:
                        raise StandardError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        # 没找到主键， 抛出 StandardError
        if not primaryKey:
            raise StandardError('Primary key not found.')
        # 把attrs字典中 key 属于 Field类的键值对 出栈
        for k in mappings.keys():
            attrs.pop(k)
        # 出栈的字段列表
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))

        attrs['__mappings__'] = mappings # 保存属性和列的映射关系
        attrs['__table__'] = tableName # 表名
        attrs['__primary_key__'] = primaryKey # 主键属性名
        attrs['__fields__'] = fields # 除主键外的属性名
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        # __new__()方法接收到的参数依次是：
        # cls ：当前准备创建的类的对象；
        # name ：类的名字
        # bases：类继承的父类集合
        # attrs：类的方法集合
        return type.__new__(cls, name, bases, attrs)

# 模板类 父类：字典类， 模板元类
class Model(dict, metaclass=ModelMetaclass):

    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value

    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        ' find objects by where clause. '
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        ' find number by select and where. '
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    @classmethod
    async def find(cls, pk):
        ' find object by primary key. '
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)

    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)

    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warn('failed to remove by primary key: affected rows: %s' % rows)