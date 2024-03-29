#!/usr/bin/env python3
'''
script for getting course in SUSTech
'''
import logging
import time
import json
from urllib.parse import urlparse, parse_qs
from lxml import etree
from .cas import CASSession


class Grabber(object):
    operator = {0: 'fawxk', 1: 'ggxxkxk', 2: 'knjxk',
                3: 'bxqjhxk', 4: 'bxxk', 5: 'xxxk'}

    def __init__(self):
        self.session = None
        self.uid = None
        self.passwd = None
        self.courselist = list()
        self.delay = 100
        self.threadCount = 1
        self.xklist = list()

    def getCourseList(self):
        showlist = [(courseNo, Grabber.operator[courseType])
                    for (courseNo, courseType) in self.courselist]
        return showlist

    def setspeed(self, delay, threadCount):
        self.delay = delay
        self.threadCount = threadCount

    def init(self):
        c = CASSession()
        c.setAuthInfo(self.uid, self.passwd)
        c.loginService("http://jwxt.sustc.edu.cn/jsxsd/")
        self.session = c.getSession()

    def setloginInfo(self, username, password):
        self.uid = username
        self.passwd = password

    def addcourse(self, courseNo, courseType=0):
        '''
        coursetype: 0-fawxk, 1-ggxxkxk, 2-knjxk, 3-bxqjhxk, 4-bxxkOper
        '''
        self.courselist.append((courseNo, courseType))

    def saveConfig(self, filename='grabber-conf.json'):
        from collections import OrderedDict
        configstr = OrderedDict(
            delay=self.delay, uid=self.uid, password=self.passwd, courseList=self.courselist)
        with open(filename, 'w') as file:
            file.write(json.dumps(configstr))

    def loadConfig(self, filename='grabber-conf.json'):
        text = None
        with open(filename, 'r') as file:
            text = file.read()
        config = json.loads(text)
        self.uid = config['uid']
        self.passwd = config['password']
        self.courselist = config['courseList']
        self.delay = int(config['delay'])
        logging.info(config)

    def start(self):
        if len(self.courselist) < 1:
            return
        while(True):
            if len(self.xklist) < 1:
                self.xklist = self.__getxklist(self.session)
                logging.info("waiting for the entrance")
            else:
                for course in self.courselist:
                    # Important here! self.xklist[0][1]
                    # init server side session
                    self.session.get(
                        url="http://jwxt.sustc.edu.cn/jsxsd/xsxk/xsxk_index?jx0502zbid=" + self.xklist[0][1])
                    r = self.session.get(url="http://jwxt.sustc.edu.cn/jsxsd/xsxkkc/%sOper?jx0404id=%s&xkzy=&trjf=" % (
                        Grabber.operator[course[1]], course[0]))
                    logging.info("courseId: {0}, response: {1}".format(
                        course[0], r.text.strip()))
                    try:
                        result = json.loads(r.text)
                    except:
                        logging.info("anti-grabbing detected.")
                        continue
                    if 'success' in result.keys() and 'message' in result.keys():
                        if result['message'] == None:
                            logging.info("no such course")
                        elif '已选择' in result['message']:
                            # 当前教学班已选择 success
                            self.courselist.remove(course)
                    else:
                        logging.info("no such course")
            time.sleep(self.delay / 1000)
            logging.info("Remaining Course: {0}".format(self.courselist))
            if len(self.courselist) < 1:
                logging.info("Program finished. Exiting....")
                return

    def __getxklist(self, session):
        '''
        # r = s.get(url="http://jwxt.sustc.edu.cn/jsxsd/xsxk/xklc_list")
        # first row head | the rest content
        # time page.xpath("/html/body//table[@id='tbKxkc']/tr[2]/td[3]/text()[1]")[0]
        # url page.xpath("/html/body//table[@id='tbKxkc']/tr[2]/td[4]/a/@href[1]")[0]
        '''
        r = session.get(url="http://jwxt.sustc.edu.cn/jsxsd/xsxk/xklc_list")
        page = etree.HTML(r.text)
        # get the list
        row_count = len(page.xpath("/html/body//table[@id='tbKxkc']/tr"))
        row_exist = len(page.xpath("/html/body//table[@id='tbKxkc']/tr[2]/td"))
        xklist = list()
        if row_exist > 1:
            for row in range(row_count - 1):
                item_time = page.xpath(
                    "/html/body//table[@id='tbKxkc']/tr[%d]/td[3]/text()[1]" % (row + 2))[0]
                item_url = page.xpath(
                    "/html/body//table[@id='tbKxkc']/tr[%d]/td[4]/a/@href[1]" % (row + 2))[0]
                logging.debug(item_url)
                parsed = urlparse(item_url)
                query = parse_qs(qs=parsed.query)
                logging.info('Open time: {0}, ID: {1}'.format(
                    item_time, query['jx0502zbid'][0]))
                xklist.append((item_time, query['jx0502zbid'][0]))
        return xklist


def main():
    # logging
    logging.basicConfig(level=logging.INFO)
    log_formatter = logging.Formatter("%(asctime)s[%(levelname)s]%(message)s")
    file_handler = logging.FileHandler("grabber.log")
    file_handler.setFormatter(log_formatter)
    logging.getLogger().addHandler(file_handler)

    g = Grabber()
    isloadconfig = input("Load the config file? y or n [y]:")
    if isloadconfig == 'y' or isloadconfig == '':
        g.loadConfig()
    else:
        uid = input("CAS username:")
        passwd = input("CAS password:")
        g.setloginInfo(uid, passwd)
        total = input(
            "Please input the total number of courses you want to grab:")
        if total == '':
            total = 0
        try:
            total = int(total)
        except ValueError:
            print("That's not an int!")
        for _ in range(int(total)):
            course_code = input("Course code:")
            course_type = input(
                "0-fawxk, 1-ggxxkxk, 2-knjxk, 3-bxqjhxk, 4-bxxk 5-xxxk c-cancel \nCourse Type (default 0):")
            if course_code == '' or course_type == 'c':
                continue
            if course_type == '':
                course_type = 0
            g.addcourse(course_code, int(course_type))
        print(g.getCourseList())
        input("Please Check, Press enter to continue")
        input("Press enter to start")
        g.saveConfig()
    g.init()
    g.start()


if __name__ == "__main__":
    main()
