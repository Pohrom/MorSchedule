# -*- coding:utf-8 -*-
##  MorSchedule
##
__author__ = 'MorHop'
__version__ = '2016121216'
##
##
import re
import traceback
from datetime import datetime, timedelta
import pytz
import requests
from icalendar import Calendar, Event, vText

# SOURCE 配置
KEBIAO_CQUPT_SOURCE_URL = "http://jwzx.cqupt.edu.cn/jwzxtmp/showkebiao.php"
WEEK_OF_TERM_CQUPT_SOURCE_URL = "http://jwzx.cqupt.edu.cn/jwzxtmp/ksap.php"
EXAM_ARRANGEMENT_CQUPT_SOURCE_URL = "http://jwzx.cqupt.edu.cn/jwzxtmp/showKsap.php"

EXAM_ARRANGEMENT_INTERNET_SOURCE_URL = "http://jwzx.cqupt.congm.in/jwzxtmp/showKsap.php"
KEBIAO_INTERNET_SOURCE_URL = "http://jwzx.cqupt.congm.in/jwzxtmp/kebiao/kb_stu.php"
WEEK_OF_TERM_INTERNET_SOURCE_URL = "http://jwzx.cqupt.congm.in/jwzxtmp/ksap.php"

KEBIAO_SOURCE_URL = KEBIAO_INTERNET_SOURCE_URL + "?xh="
WEEK_OF_TERM_SOURCE_URL = WEEK_OF_TERM_INTERNET_SOURCE_URL
EXAM_ARRANGEMENT_SOURCE_URL = EXAM_ARRANGEMENT_INTERNET_SOURCE_URL + "?type=stu&id="

# 课程时间
COURSE_CLASS_OF_DAY = [
    [timedelta(hours=8, minutes=0), timedelta(hours=9, minutes=40)],
    [timedelta(hours=10, minutes=5), timedelta(hours=11, minutes=45)],
    [timedelta(hours=14, minutes=0), timedelta(hours=15, minutes=40)],
    [timedelta(hours=16, minutes=5), timedelta(hours=17, minutes=45)],
    [timedelta(hours=19, minutes=0), timedelta(hours=20, minutes=40)],
    [timedelta(hours=20, minutes=50), timedelta(hours=22, minutes=30)],
]

REGEX_R = re.compile("<td.*?>.*?</td>", re.S)
REGEX_EXAM_PERIOD = re.compile("(?P<hour>\\d+):(?P<minute>\\d+)", re.S)
REGEX_INFO = re.compile("(?=<br>).+?(?=<br>)|(<br>.+?(?=</span>))", re.S)
REGEX_HTML = re.compile("<[^>]+>", re.S)
REGEX_ONLY_DIGIT = re.compile("(\\w*[0-9]+)\\w*", re.S)
REGEX_CURRENT_DATE_OF_TERM = re.compile(u"(?P<beginYear>\d{4})-(?P<endYear>\d{4})学年(?P<term>\d)学期 第 (?P<weekOfTerm>[-\d]+?) 周 星期 (?P<dayOfWeek>\d+)",re.S)

def get_current_date_info_of_term():
    '''
    获取当前学期的时间信息
    '''
    resp = requests.get(WEEK_OF_TERM_SOURCE_URL)
    result = REGEX_CURRENT_DATE_OF_TERM.search(resp.text)
    tz = pytz.timezone("Asia/Chongqing")
    serverDatetime = datetime.strptime(resp.headers['date'], '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo = tz)
    # TODO: dayOfWeek 的可能性需要更多测试
    return serverDatetime,int(result.group('beginYear')),int(result.group('endYear')),int(result.group('term')),int(result.group('weekOfTerm')),int(result.group('dayOfWeek')) or Null

def get_beginning_of_term():
    '''获取当前学期的开始日期'''
    serverDatetime,beginYear,endYear,term,weekOfTerm,dayOfWeek = get_current_date_info_of_term()
    beginning = serverDatetime - timedelta(weeks=weekOfTerm - 1 , days=dayOfWeek - 1)
    return datetime.combine(beginning.date(),datetime(1970,1,1).time())

SchoolOpen = get_beginning_of_term()

def reserve_digit(string):
    '''
    仅保留字符串中的数字，返回一个列表
    '''
    return REGEX_ONLY_DIGIT.findall(string)

def reserve_first_number(string):
    '''
    仅保留字符串中的第一个数字，返回 int 类型
    '''
    return int(reserve_digit(string)[0])

def get_kebiao_source(id_):
    '''
    从课表页面获取源代码
    '''
    resp = requests.get(KEBIAO_SOURCE_URL + str(id_), timeout=5)
    return resp.text.replace(chr(0x0d), "").replace(chr(0x0a), "")

def get_exam_source(id_):
    '''
    从课表页面获取源代码
    '''
    resp = requests.get(EXAM_ARRANGEMENT_SOURCE_URL + str(id_), timeout=5)
    return resp.text.replace(chr(0x0d), "").replace(chr(0x0a), "")

# HTML表格拆解
def get_table_source(html):
    kebiao_list = REGEX_R.findall(html)
    return kebiao_list

# 单一课程信息提取
def get_course_info_from_source(item):
    if len(item) == len("<td ></td>") or len(item) == len("<td></td>"):
        return None
    course = dict()
    infos = item.split("<br>")
    class_detail = REGEX_HTML.sub('', infos[4])
    teacher_name = class_detail[:class_detail.find(" ")]
    course = {
        'id': REGEX_HTML.sub('', infos[0]),
        'name': infos[1][infos[1].find("-")+1:],
        'location': infos[2][3:].strip(" "),
        'periods': REGEX_HTML.sub('', infos[3]).strip(" "),
        'teacher': teacher_name
        }
    return course

def verify_course_info(course):
    '''验证/校正课程信息并增加可读性'''
    prefix = str()
    postfix = str()

    # 体育课标注
    if course["name"] == "" and course["location"] == u"运动场":
        course["name"] = u"体育"

    # 实验课标注
    if course["id"].find("SK") != -1:
        prefix += u"实验 - "

    if course["periods"].find(u"3节连上") != -1:
        course["periods"] = course["periods"].replace(u"3节连上", "")
        postfix = u" - 3节连上"

    # 教师信息补全
    if course["teacher"] != "":
        postfix += u" - " + course["teacher"]


    course["name"] = prefix + course["name"] + postfix
    return course

def split_course_sources(unit):
    '''分割含有多节课的单元'''
    if unit.find("<hr>") == -1:
        course_sources = [unit]
    else:
        course_sources = unit.split("<hr>")
    return course_sources

def generate_week_event(cal):
    '''生成周信息日历时间'''
    for i in range(1, 19):
        event = Event()
        event.add('summary', "即将第%d周" % (i))
        event.add('dtstart', SchoolOpen + timedelta(weeks=(i-1), days=-1, hours=17))
        event.add('dtend', SchoolOpen + timedelta(weeks=(i-1), days=-1, hours=17))
        event['location'] = vText("重庆邮电大学")
        cal.add_component(event)

def generate_course_event(cal, class_of_day, day_of_week, weeklist, course):
    '''生成课程日历事件'''
    period_begin = COURSE_CLASS_OF_DAY[class_of_day][0]
    period_end = COURSE_CLASS_OF_DAY[class_of_day][1]

    for week_index in weeklist:
        event = Event()
        event.add('summary', course["name"])
        event.add('dtstart', SchoolOpen + timedelta(weeks=week_index-1, days=day_of_week - 1)  + period_begin)
        event.add('dtend', SchoolOpen + timedelta(weeks=week_index-1, days=day_of_week - 1) + period_end)
        event['location'] = vText(course["location"])
        cal.add_component(event)

def parse_time(periods):
    '''解析周数字符串为周列表'''
    weeklist = list()
    for period in periods.split(","):
        if period.find(u"单周") != -1 or period.find(u"双周") != -1:
            #单双周时间 2-16周单周
            pair = period[:-3].split("-")
            if period.find(u"单周") != -1:
                for i in range(reserve_first_number(pair[0]), reserve_first_number(pair[1])+1):
                    if i%2 == 1:
                        weeklist.append(i)
            elif period.find(u"双周") != -1:
                for i in range(reserve_first_number(pair[0]), reserve_first_number(pair[1])+1):
                    if i%2 == 0:
                        weeklist.append(i)
            else:
                print "发现特殊时间类型,未做处理 : " + period
                raise Exception("发现特殊时间类型,未做处理 : " + period)

        elif period.find("-") != -1:
            #一般时间段 2-16周
            pair = period[:-1].split("-")
            for i in range(reserve_first_number(pair[0]), reserve_first_number(pair[1])+1):
                weeklist.append(i)

        else:
            #单一时间点 2周
            weeklist.append(reserve_first_number(period))
    return weeklist

def generate_exam_event(cal, exam_info):
    '''生成考试事件'''
    event = Event()
    event.add('summary', u"%s考试 - %s - %s - %s" % (exam_info["type"], exam_info["name"], exam_info["sn"], exam_info["qualified"]))
    event.add('dtstart', SchoolOpen + timedelta(weeks=exam_info['week']-1, days=exam_info['weekday'] - 1)  + exam_info['period']['begin'])
    event.add('dtend', SchoolOpen + timedelta(weeks=exam_info['week']-1, days=exam_info['weekday'] - 1) + exam_info['period']['end'])
    event['location'] = vText(exam_info["location"])
    cal.add_component(event)

def parse_exam_period(period_string):
    '''解析考试时间段'''
    result = REGEX_EXAM_PERIOD.findall(period_string)
    ret = {
        'begin':timedelta(hours=int(result[0][0]), minutes=int(result[0][1])),
        'end':timedelta(hours=int(result[1][0]), minutes=int(result[1][1])),
    }
    return ret

def get_ics(student_id):
    '''
    日历名称放于后部,以便添加异常警告
    iOS添加时的日历描述遵循 fallback : name->desc
    '''
    cal = Calendar()
    cal.add('prodid', '-//My calendar product//mxm.dk//')
    cal.add('version', '2.0')
    cal.add('timezone-id', 'Asia/Chongqing')
    cal.add('X-WR-TIMEZONE', 'Asia/Chongqing')

    try:
        # 所有表格项目
        course_table = get_table_source(get_kebiao_source(student_id))
        exam_table = get_table_source(get_exam_source(student_id))
        # 二维数组化单元格
        course_units = zip(*[iter(course_table)]*8)
        exam_units = zip(*[iter(exam_table)]*12)
        # 删除表头/休息间隔
        del course_units[6]
        del course_units[3]
        del course_units[0]
        del exam_units[0]

        for exam_source in exam_units:
            exam_info = {
                'name':REGEX_HTML.sub('', exam_source[5]),
                'type':REGEX_HTML.sub('', exam_source[3]),
                'week':int(REGEX_HTML.sub('', exam_source[6])[:-1]),
                'weekday':int(REGEX_HTML.sub('', exam_source[7])),
                'period':parse_exam_period(REGEX_HTML.sub('', exam_source[8])),
                'location':REGEX_HTML.sub('', exam_source[9]),
                'sn':REGEX_HTML.sub('', exam_source[10]),
                'qualified':REGEX_HTML.sub('', exam_source[11]),
            }
            generate_exam_event(cal, exam_info)

        for class_of_day in range(0, 6):
            for day_of_week in range(1, 8):
                for course_source in split_course_sources(course_units[class_of_day][day_of_week]):
                    course = get_course_info_from_source(course_source)	# HTML课程转对象
                    if course != None:
                        course = verify_course_info(course)	# 课程对象信息校正
                        weeklist = parse_time(course["periods"])
                        generate_course_event(cal, class_of_day, day_of_week, weeklist, course)
        generate_week_event(cal)
    except Exception,e:
        cal.add('name', '异常 - MorSchedule - ' + str(student_id))
        cal.add('X-WR-CALNAME', '异常 - MorSchedule - ' + str(student_id))
        cal.add('description', u"异常 - " + str(student_id) + u"的课表")
        cal.add('X-WR-CALDESC', u"异常 - " + str(student_id) + u"的课表")
        traceback.print_exc()
    else:
        cal.add('name', 'MorSchedule - ' + str(student_id))
        cal.add('X-WR-CALNAME', 'MorSchedule - ' + str(student_id)) # iOS used
        cal.add('description', str(student_id) + u"的课表")
        cal.add('X-WR-CALDESC', str(student_id) + u"的课表")
    finally:
        return cal.to_ical()

def save_ics_file():
    '''生成 iCal 格式日历文件'''
    student_id = raw_input("code:")
    ics_file = open('MorSchedule.ics', 'wb')
    ics_file.write(get_ics(student_id))
    ics_file.close()
    print 'saved to MorSchedule.ics'

if __name__ == "__main__":
    save_ics_file()
