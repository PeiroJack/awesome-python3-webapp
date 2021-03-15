# awesome-python3-webapp
A python webapp tutorial.



这个项目是跟着廖雪峰python教程的实战：

[廖雪峰python教程网址](https://www.liaoxuefeng.com/wiki/1016959663602400/1018138223191520)：

https://www.liaoxuefeng.com/wiki/1016959663602400/1018138223191520



开发环境：

python 3.8.5

Anaconda

MySQL 5.7数据库

用`pip`安装开发Web App需要的第三方库：

异步框架aiohttp：

```
$pip3 install aiohttp
```

前端模板引擎jinja2：

```
$ pip3 install jinja2
```

MySQL的Python异步驱动程序aiomysql：

```
$ pip3 install aiomysql
```



目录结构：

```
awesome-python3-webapp/  <-- 根目录
|
+- backup/               <-- 备份目录
|
+- conf/                 <-- 配置文件
|
+- dist/                 <-- 打包目录
|
+- www/                  <-- Web目录，存放.py文件
|  |
|  +- static/            <-- 存放静态文件
|  |
|  +- templates/         <-- 存放模板文件
|
+- ios/                  <-- 存放iOS App工程
```