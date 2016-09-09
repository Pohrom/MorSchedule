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

def GetKebiaoHTML(id):
        #代理服务器设置
        proxies = {}
        # proxies = {'http': 'http://127.0.0.1:8081'}
	# 内网
	# resp = requests.get("http://jwzx.cqupt.edu.cn/jwzxtmp/showkebiao.php?type=student&id=" + str(id),timeout=1)
	# 外网
	resp = requests.get("http://jwzx.cqupt.edu.cn.cqupt.congm.in/jwzxtmp/showkebiao.php?type=student&id=" + str(id),timeout=5)
        return resp.text.replace(chr(0x0d),"").replace(chr(0x0a),"")

def GetKebiao(html):
	Kebiaolist = r.findall(html)
	return Kebiaolist

def GetCourseInfo(item):
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
	return CourseVerify(course) 

def CourseVerify(course):
	if course["name"] == "" and course["location"] == u"运动场":
		course["name"] = u"体育"
	elif course["id"].find("SK") != -1:
		course["name"] = u"实验 - " + course["name"] + " - " + course["teacher"]
	else:
		course["name"] = course["name"] + " - " + course["teacher"]
	return course

# 单时间段多课程
def GetCourseSplit(period):
	courses = list()
	if (period.find("<hr>") == -1):
		courses.append(GetCourseInfo(period))
	else:
		items = period.split("<hr>")
		for item in items:
			courses.append(GetCourseInfo(item))
	return courses

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

def appendWeek(periods):
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
				print("发现异常时间类型" + period)

		elif period.find("-") != -1:
			#一般时间段 2-16周
			pair = period[:-1].split("-")
			for i in range(int(pair[0]),int(pair[1])+1):
				weeklist.append(i)

		else:
			#单一时间点 2周
			weeklist.append(int(period[:-1]))
	return weeklist

def oneCourseAddMultiEvent(cal,periodIndex,dayIndex,courses):
	for course in courses:
		if course != None:
			weeklist = appendWeek(course["periods"])
			generateEvent(cal,int(periodIndex),int(dayIndex),weeklist,course)


def getICS(id):
	cal = Calendar()
	cal.add('prodid', '-//My calendar product//mxm.dk//')
	cal.add('version', '2.0')

	#所有表格项目
	itemsFlat = GetKebiao(GetKebiaoHTML(id))
	#二维数组化
	items = zip(*[iter(itemsFlat)]*8)
	#删除休息间隔
	del items[6]
	del items[3]
	del items[0]

	#dayIndex = 0 时是节数栏
	for periodIndex in range(0,6):
		for dayIndex in range(0,8):
			if dayIndex !=0:
				oneCourseAddMultiEvent(cal,periodIndex,dayIndex,GetCourseSplit(items[periodIndex][dayIndex]))
	return cal.to_ical()

if __name__ == "__main__":
	id = raw_input("code:")
	f = open('MorSchedule.ics', 'wb')
	f.write(getICS(id))
	f.close()
	print('saved to MorSchedule.ics')