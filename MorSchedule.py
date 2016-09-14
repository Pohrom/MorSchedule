# -*- coding:utf-8 -*-
##  MorSchedule
##
__author__ = 'MorHop'
__version__ = '2016090609'
##
##

import requests
import re
from icalendar import *
from datetime import datetime,timedelta

#配置
proxies = {}

# 开学时间(在第一周中的某个日期即可)
# 每学期重设
SchoolOpen = datetime(2016,9,5)
SchoolOpen = SchoolOpen - timedelta(days=SchoolOpen.weekday())

# 课程时间
CoursePeriod = [
	[timedelta(hours=8, minutes=0 ),timedelta(hours=9, minutes=40)],
	[timedelta(hours=10,minutes=5 ),timedelta(hours=11,minutes=45)],
	[timedelta(hours=14,minutes=0 ),timedelta(hours=15,minutes=40)],
	[timedelta(hours=16,minutes=5 ),timedelta(hours=17,minutes=45)],
	[timedelta(hours=19,minutes=0 ),timedelta(hours=20,minutes=40)],
	[timedelta(hours=20,minutes=50),timedelta(hours=22,minutes=30)],
]

r = re.compile("<td.*?>.*?</td>", re.S)
rInfo = re.compile("(?=<br>).+?(?=<br>)|(<br>.+?(?=</span>))", re.S)
rHtml = re.compile(r'<[^>]+>',re.S)

def getKebiaoHTML(id):
        #代理服务器设置
        proxies = {}
        # proxies = {'http': 'http://127.0.0.1:8081'}
	# 内网
	resp = requests.get("http://jwzx.cqupt.edu.cn/jwzxtmp/showkebiao.php?type=student&id=" + str(id),timeout=1)
	# 外网
	# resp = requests.get("http://jwzx.cqupt.edu.cn.cqupt.congm.in/jwzxtmp/showkebiao.php?type=student&id=" + str(id),timeout=5)
        return resp.text.replace(chr(0x0d),"").replace(chr(0x0a),"")

# HTML表格拆解
def getKebiaoHTMLItems(html):
	Kebiaolist = r.findall(html)
	return Kebiaolist

# 单一课程信息提取
def getCourseFromHTML(item):
	if len(item) == len("<td ></td>"):
		return None
	course = dict()
	infos = item.split("<br>")
	classDetail = rHtml.sub('',infos[4])
	teacherName = classDetail[:classDetail.find(" ")]
	course = {
			'id':rHtml.sub('',infos[0]),
			'name':infos[1][infos[1].find("-")+1:],
			'location':infos[2][3:].strip(" "),
			'periods':rHtml.sub('',infos[3]).strip(" "),
			'teacher':teacherName
		}
	return course

# 单一课程信息验证与校正
def courseVerify(course):
	prefix = str()
	postfix = str()

	# 体育课标注
	if course["name"] == "" and course["location"] == u"运动场":
		course["name"] = u"体育"

	# 实验课标注
	if course["id"].find("SK") != -1:
		prefix += u"实验 - "

	if course["periods"].find(u"3节连上") != -1:
		course["periods"] = course["periods"].replace(u"3节连上","")
		postfix = u" - 3节连上"

	# 教师信息补全
	if course["teacher"] != "":
		postfix += u" - " + course["teacher"]


	course["name"] = prefix + course["name"] + postfix
	return course

# 多课程单元分割
def muiltCourseUnitSplit(unit):
	if (unit.find("<hr>") == -1):
		coursesHTML = [unit]
	else:
		coursesHTML = unit.split("<hr>")
	return coursesHTML

# 生成日历事件
def generateEvent(cal,periodIndex,dayIndex,weeklist,course):
	periodStart = CoursePeriod[periodIndex][0]
	periodEnd = CoursePeriod[periodIndex][1]

	for weekIndex in weeklist:
		event = Event()
		event.add('summary', course["name"])
		event.add('dtstart', SchoolOpen + timedelta(weeks=weekIndex-1,days=dayIndex - 1)  + periodStart)
		event.add('dtend', SchoolOpen + timedelta(weeks=weekIndex-1,days=dayIndex - 1) + periodEnd)
		event['location'] = vText(course["location"])
		cal.add_component(event)

def parseTime(periods):
	weeklist = list()
	for period in periods.split(","):
		if period.find(u"单周") != -1 or period.find(u"双周") != -1:
			#单双周时间 2-16周单周
			pair = period[:-3].split("-")
			if period.find(u"单周") != -1:
				for i in range(int(pair[0]),int(pair[1])+1):
					if i%2 == 1:
						weeklist.append(i)
			elif period.find(u"双周") != -1:
				for i in range(int(pair[0]),int(pair[1])+1):
					if i%2 == 0:
						weeklist.append(i)
			else:
				print(u"发现特殊时间类型,未做处理 : " + period)
				raise Exception(u"发现特殊时间类型,未做处理 : " + period)

		elif period.find("-") != -1:
			#一般时间段 2-16周
			pair = period[:-1].split("-")
			for i in range(int(pair[0]),int(pair[1])+1):
				weeklist.append(i)

		else:
			#单一时间点 2周
			weeklist.append(int(period[:-1]))
	return weeklist


def getICS(id):
	# 日历名称放于后部,以便添加异常警告
	# iOS添加时的日历描述遵循fallback : name->desc
	cal = Calendar()
	cal.add('prodid', '-//My calendar product//mxm.dk//')
	cal.add('version', '2.0')
	cal.add('timezone-id','Asia/Chongqing')
	cal.add('X-WR-TIMEZONE','Asia/Chongqing')

	try:  

		#所有表格项目
		items = getKebiaoHTMLItems(getKebiaoHTML(id))
		#二维数组化单元格
		units = zip(*[iter(items)]*8)
		#删除休息间隔
		del units[6]
		del units[3]
		del units[0]

		#dayIndex = 0 时是节数栏
		for periodIndex in range(0,6):
			for dayIndex in range(1,8):
				for courseHTML in muiltCourseUnitSplit(units[periodIndex][dayIndex]):
					course = getCourseFromHTML(courseHTML)	# HTML课程转对象
					if course != None:
						course = courseVerify(course)	# 课程对象信息校正
						weeklist = parseTime(course["periods"])
						generateEvent(cal,periodIndex,dayIndex,weeklist,course)
	except Exception,e:
		cal.add('name','异常 - MorSchedule - ' + str(id))
		cal.add('X-WR-CALNAME','异常 - MorSchedule - ' + str(id))
		cal.add('description',u"异常 - " + str(id) + u"的课表") 
		cal.add('X-WR-CALDESC',u"异常 - " + str(id) + u"的课表")
	else:
		cal.add('name','MorSchedule - ' + str(id))
		cal.add('X-WR-CALNAME','MorSchedule - ' + str(id)) # iOS used
		cal.add('description',str(id) + u"的课表") 
		cal.add('X-WR-CALDESC',str(id) + u"的课表")
	finally:
		return cal.to_ical()

if __name__ == "__main__":
	id = raw_input("code:")
	f = open('MorSchedule.ics', 'wb')
	f.write(getICS(id))
	f.close()
	print('saved to MorSchedule.ics')