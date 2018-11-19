#! /usr/local/bin/python3
# coding: utf-8
# __author__ = "lsg"
# __date__ = 2017/10/16 16:11

#加载内置包
import requests
import json
import time
import sys
#加载第三方包
import pandas
from selenium import webdriver
from requests.exceptions import RequestException
from selenium.common.exceptions import WebDriverException
#加载自己编写的文件
import qqlist
import settings
import transCoordinateSystem

class CookieException(Exception):
    def __init__(self):
        Exception.__init__(self)

class easygospider():
    #初始化基本量
    def __init__(self):
        self.qq_number_list = []
        self.cookie = None
        #输入文件的名称
        self.input = settings.xy_name
        #文件保存的路径
        self.filepath = settings.filepath
        self.filename = settings.filename
        self.qq_number_list = qqlist.qq_list

    # 初始化用于爬虫的网格，形成url
    def initial_paramslist(self):
        """
        :return: List[]
        """
        #filename文件中需要存储的为Wgs84坐标系下渔网为2.5Km的中心点的坐标，格式如data.txt
        #读取渔网中心点
        center = []
        with open(self.input, 'r', encoding='utf-8') as f:
            for item in f.readlines()[1:]:
                center.append(tuple(item.strip().split(",")[-2:]))
        #生成四至范围（按照2.6km范围生成，防止有遗漏点，如有重复，最后去重的时候处理）
        round = []
        for item in center:
            lng, lat = item
            lng, lat = float(lng), float(lat)
            round.append([lng - 0.5 * settings.lng_delta,
                          lng + 0.5 * settings.lng_delta,
                          lat - 0.5 * settings.lat_delta,
                          lat + 0.5 * settings.lat_delta])
        #生成待抓取的params
        paramslist = []
        for item in round:
            lng_min, lng_max, lat_min, lat_max = item
            #lng_min, lat_min = transCoordinateSystem.wgs84_to_gcj02(lng_min, lat_min)
            #lng_max, lat_max = transCoordinateSystem.wgs84_to_gcj02(lng_max, lat_max)
            params = {"lng_min": lng_min,
                      "lat_max": lat_max,
                      "lng_max": lng_max,
                      "lat_min": lat_min,
                      "level": 16,
                      "city": "厦门",
                      "lat": "undefined",
                      "lng": "undefined",
                      "_token": ""}
            paramslist.append(params)
        return paramslist

    def get_cookie(self):
        while True:
            try:
                chrome_login = webdriver.Chrome(executable_path="chromedriver.exe")
                chrome_login.implicitly_wait(10)
                chrome_login.get(
                    "http://c.easygo.qq.com/eg_toc/map.html?origin=csfw&cityid=110000")
                try:
                    qq_ = self.qq_number_list.pop()
                except IndexError:
                    self.qq_number_list = qqlist.qq_list
                    qq_ = self.qq_number_list.pop()
                qq_num = qq_[0]
                qq_passwd = qq_[1]
                chrome_login.find_element_by_id("u").send_keys(qq_num)
                chrome_login.find_element_by_id("p").send_keys(qq_passwd)
                chrome_login.find_element_by_id("go").click()
                #检查是否存在验证码
                time.sleep(5)
                if "安全验证" in chrome_login.page_source:
                    if settings.CAPTCHA_RECOGNIZ:
                        input('等待手动去除验证码')
                    else:
                        chrome_login.close()
                        continue

                #获取cookie
                cookies = chrome_login.get_cookies()
                chrome_login.quit()
                user_cookie = {}
                for cookie in cookies:
                    user_cookie[cookie["name"]] = cookie["value"]
                return user_cookie
            except WebDriverException as e:
                pass
            finally:
                try:
                    chrome_login.close()
                except Exception:
                    pass

    def spyder(self,cookie,params):
        user_header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
            "Referer": "http://c.easygo.qq.com/eg_toc/map.html?origin=csfw"
        }
        url = "http://c.easygo.qq.com/api/egc/heatmapdata"
        while True:
            try:
                r = requests.get(url, headers=user_header,
                                 cookies=cookie, params=params)
                # print(r.status_code)
                if r.status_code == 200:
                    print('返回正确,返回的文本：', r.text)
                    return r.text
                else:
                    raise CookieException
            except RequestException:
                self.spyder(cookie, params)

    def save(self,text,time_now,file_name):
        try:
            with open(file_name, 'r') as f:
                f.readline()
        except FileNotFoundError as e:
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write('count,wgs_lng,wgs_lat,time\n')
        # 写入数据
        with open(file_name, "a", encoding="utf-8") as f:
            if text is None:
                return
            node_list = json.loads(text)["data"]
            try:
                min_count = json.loads(text)['max_data']/40
                for i in node_list:
                    # 此处的算法在宜出行网页后台的js可以找到，文件路径是http://c.easygo.qq.com/eg_toc/js/map-55f0ea7694.bundle.js
                    i['count'] = i['count'] // min_count
                    gcj_lng = 1e-6 * (250.0 * i['grid_x'] + 125.0)
                    gcj_lat = 1e-6 * (250.0 * i['grid_y'] + 125.0)
                    lng, lat = transCoordinateSystem.gcj02_to_wgs84(gcj_lng, gcj_lat)
                    f.write(str(i['count']) + "," + str(lng) + "," + str(lat) + "," + time_now + "\n")
            except IndexError as e:
                pass
                # print("此区域没有点信息")
            except TypeError as e:
                print(node_list)
                raise CookieException
    def remove_duplicate(self,filepath):
        # df = pandas.read_csv(filepath,sep=",")
        df = pandas.read_csv(filepath, sep=',')
        df = df.drop_duplicates()
        csv_name = filepath.replace(".txt", "去重结果.csv")
        df.to_csv(csv_name,index=False)

    def exec(self):
        while True:
            time_now = time.time()
            time_now_str = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(time_now))
            write_log("此轮抓取开始")
            cookie = self.get_cookie()
            i = 1
            params_list = self.initial_paramslist()
            for params in params_list:

                #这部分负责每个qq号码抓取的次数
                if i % settings.fre == 0:
                    cookie = self.get_cookie()
                while True:
                    try:
                        text = self.spyder(cookie, params)
                        self.save(text, time_now_str, file_name=self.filepath + self.filename + time_now_str + ".txt")
                        break
                    except CookieException as e:
                        cookie = self.get_cookie()

                view_bar(i, len(params_list))
                i += 1
            write_log("此轮抓取完成，开始去重")
            self.remove_duplicate(self.filepath + self.filename + time_now_str + ".txt")
            write_log("去重完成,等待下一轮开始")
            time.sleep(settings.sleeptime - int(time.time() - time_now))


def write_log(content):
    with open("log.log",'a',encoding='utf-8') as f:
        info = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())+content+"\n"
        sys.stdout.write(info)
        f.write(info)

def view_bar(num, total):
    rate = float(num) / float(total)
    rate_num = int(rate * 100)
    r = '\r[%s%s]%d%%' % ("="*(rate_num), " "*(100-rate_num), rate_num, )
    sys.stdout.write(r)

if __name__ == "__main__":
    app = easygospider()
    app.exec()