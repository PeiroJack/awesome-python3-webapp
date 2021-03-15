#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 导入日志包
import logging
# 设置日志等级为INFO
logging.basicConfig(level=logging.INFO)

# 导入异步IO，标准库os， json， time
import asyncio, os, json, time
from datetime import datetime

# 异步框架aiohttp
from aiohttp import web

def index(request):
    return web.Response(body=b'<h1>Awesome</h1>', content_type='text/html')

@asyncio.coroutine
def init(loop):
    app = web.Application(loop=loop)
    # 添加路由
    app.router.add_route('GET', '/', index)
    # 异步调用loop 创建服务器 （调解器， IP， 占用端口）
    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

# 获取EventLoop:
loop = asyncio.get_event_loop()
# 执行coroutine
loop.run_until_complete(init(loop))
# loop 一直运行
loop.run_forever()