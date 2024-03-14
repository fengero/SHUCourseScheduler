import requests
import rsa
import base64
import re
from icalendar import Calendar, Event
from datetime import datetime, timedelta
from lxml import html
import getpass
from pytz import timezone

# 登录所需的API和URL
_baseurl = "http://xk.autoisp.shu.edu.cn/"
_termindex = _baseurl + "Home/TermIndex"
_termselect = _baseurl + "Home/Termselect"
_table = _baseurl + "StudentQuery/QueryCourseTable"

# 密码加密公钥
_keystr = '''-----BEGIN PUBLIC KEY-----
    MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDl/aCgRl9f/4ON9MewoVnV58OLOU2ALBi2FKc5yIsfSpivKxe7A6FitJjHva3WpM7gvVOinMehp6if2UNIkbaN+plWf5IwqEVxsNZpeixc4GsbY9dXEk3WtRjwGSyDLySzEESH/kpJVoxO7ijRYqU+2oSRwTBNePOk1H+LRQokgQIDAQAB
    -----END PUBLIC KEY-----'''

default_date_str = "2024-03-11"

session = requests.Session()

def encrypt_pass(passwd):
    pubkey = rsa.PublicKey.load_pkcs1_openssl_pem(_keystr.encode('utf-8'))
    encrypt_pwd = base64.b64encode(rsa.encrypt(passwd.encode('utf-8'), pubkey)).decode()
    return encrypt_pwd

def login(username, encrypted_password):
    login_data = {"username": username, "password": encrypted_password}
    try:
        response = session.get(_baseurl)
        print(response.url)
        if "https://oauth.shu.edu.cn/login" in response.url:
            response = session.post(response.url, data=login_data)
            if "http://xk.autoisp.shu.edu.cn/Home/TermIndex" in response.url:
                print("登录成功")
                return True
            else:
                print("登录失败，请检查您的用户名和密码")
        else:
            print("认证系统请求出错，请重试")
    except requests.exceptions.RequestException as e:
        print("请求出现错误，请检查您的网络连接或确保已连接至校园VPN。错误详情:", e)
        exit(1)
    return False

def term_get():
    response = session.get(_termindex)
    response.encoding = 'GBK' 
    response.encoding = 'utf-8'  # 显式设置响应的编码为UTF-8
    tree = html.fromstring(response.text)
    term_elements = tree.xpath('//tr[@name="rowterm"]')
    terms = [(elem.xpath('./@value')[0], elem.xpath('./td/text()')[0].strip()) for elem in term_elements]
    return terms

def clear_course_time(courses):
    pattern = re.compile(r'(?<=\d)(-)(\d+)(?![(\d])')
    # 添加默认周次信息
    def replacement(match):
        return f"{match.group(1)}{match.group(2)}(1,2,3,4,5,6,7,8,9,10)"
    for course in courses:
        course['上课时间'] = re.sub(r'[^\d\-双单一二三四五(),]', '', course['上课时间'])
        course['上课时间'] = re.sub(r'单', '(1,3,5,7,9)', course['上课时间'])
        course['上课时间'] = re.sub(r'双', '(2,4,6,8,10)', course['上课时间'])
        course['上课时间'] = pattern.sub(replacement, course['上课时间'])
        course['上课时间'] = re.sub(r'\(\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+\)\((\d+(?:,\d+)*)\)', r'(\1)', course['上课时间'])
    return courses

def select_term(terms):
    print("当前可用的学期：")
    for i, term in enumerate(terms, start=1):
        print(f"{i}. {term[1]}")

    choice = input("请输入您想选择的学期前面的编号: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(terms):
        selected_term = terms[int(choice) - 1]
        print(f"您选择了学期：{selected_term[1]}，ID为：{selected_term[0]}")
        return selected_term
    else:
        print("输入无效，请输入有效的编号。")
        exit()

def courses_get():
    response = session.post(_table, data={'termId': selected_term[0]})
    tree = html.fromstring(response.text)
    time_cells = tree.xpath('//tr[@name="rowweek"]/td[2]/text()')
    courses = []
    for course_row in tree.xpath('//tr[@name="rowclass"]'):
        course_info = {
            '课程名': course_row.xpath('.//td[3]/text()')[0].strip(),
            '教师姓名': course_row.xpath('.//td[6]/text()')[0].strip(),
            '上课时间': course_row.xpath('.//td[7]/text()')[0].strip(),
            '上课地点': course_row.xpath('.//td[8]/text()')[0].strip(),
        }
        courses.append(course_info)
    return courses, time_cells

def get_semester_start_date():
    print(f"请输入学期的开始日期，即校历第一周第一天(格式: YYYY-MM-DD)。默认为{default_date_str}（2024年春季学期）")
    try:
        user_input = input() or default_date_str
        semester_start_date = datetime.strptime(user_input, "%Y-%m-%d")
    except ValueError:
        print("输入的日期格式不正确，将使用默认的学期开始日期。")
        semester_start_date = datetime.strptime(default_date_str, "%Y-%m-%d")
    return semester_start_date

def parse_course_time(course_time_str, time_cells,semester_start_date ):
    weekdays = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '日': 7}
    course_times = []
    # 查找所有的上课时间段
    time_patterns = re.findall(r'([一二三四五六日])(\d+)-(\d+)\(([\d,]+)\)', course_time_str)
    for day, start, end, weeks in time_patterns:
        week_numbers = [int(w) for w in weeks.split(',')]
        
        # 转换为具体的上课和下课时间
        start_time = time_cells[int(start)-1].split('-')[0]
        end_time = time_cells[int(end)-1].split('-')[1]
        
        # 添加到结果列表
        for week_number in week_numbers:
            course_date = semester_start_date + timedelta(days=(week_number - 1) * 7 + (weekdays[day] - 1))
            course_times.append({
                'date': course_date.strftime('%Y-%m-%d'),
                'start_time': start_time,
                'end_time': end_time,
                'week': week_number,
                'weekday': day
            })    
    return course_times

def create_ics_calendar(courses,time_cells,semester_start_date ):
    
    cal = Calendar()

    for course in courses:
        parsed_course_times = parse_course_time(course['上课时间'],time_cells,semester_start_date )
        for ct in parsed_course_times:
            print(ct)
            event = Event()
            event.add('summary', course['课程名'])
            event.add('dtstart', datetime.strptime(f"{ct['date']} {ct['start_time']}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone('Asia/Shanghai')))
            event.add('dtend', datetime.strptime(f"{ct['date']} {ct['end_time']}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone('Asia/Shanghai')))
            event.add('dtstamp', datetime.now())
            event.add('location', course['上课地点'])
            event.add('description', f"教师姓名: {course['教师姓名']}\n周数: {ct['week']}\n星期: {ct['weekday']}")
            # 添加事件到日历
            cal.add_component(event)
    with open(f"{selected_term[1]}.ics", 'wb') as f:
        f.write(cal.to_ical())
    print(f"日历文件已经保存到当前目录下：{selected_term[1]}.ics")
    return
                     
response = False
while not response:
    username = input("请输入您的学号: ")
    password = getpass.getpass("请输入您的密码: ")
    response = login(username, encrypt_pass(password))

terms = term_get()

selected_term = select_term(terms)

session.post(_termselect, data={'termId': selected_term[0]})

courses, time_cells = courses_get()

courses = clear_course_time(courses)

semester_start_date = get_semester_start_date()

print(f"学期开始日期设置为：{semester_start_date.date()}")

create_ics_calendar(courses,time_cells,semester_start_date )





