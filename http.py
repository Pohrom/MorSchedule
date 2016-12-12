# -*- coding:utf-8 -*-
##  MorSchedule HTTP Server
##
__author__ = 'MorHop'
__version__ = '2016090609'
##
##
import web
from MorSchedule import get_ics

urls = (
    '/', 'Hello',
    '/ics', 'Ics',
    )

app = web.application(urls, globals())

class Hello:
    def GET(self):
        return """
MorSchedule
重邮 iCalendar 课表接口

author : MorHop
issues : github.com/Pohrom/MorSchedule/issues
usage  : /ics?xh=
"""
class Ics:
    def GET(self):
        i = web.input(xh = None)
        if i.xh == None:
            return "Usage: /ics?xh="
        else:
            return get_ics(i.xh)

if __name__ == "__main__":
    app.run()