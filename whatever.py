
import sqlite3
import requests
import pytesseract
import re
import os
from lxml import etree
from PIL import Image

dep = "pek"
arr = "hrb"
base_url = 'http://www.variflight.com'
url = base_url+"/flight/{}-{}.html?AE71649A58c77&fdate=20190809".format(dep, arr)

conn = sqlite3.connect('flight.db')
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS flight(f0 int,f1 text,f2 text,f3 text,f4 text,f5 text,"
              "f6 text,f7 text,f8 text,f9 text,f10 text,f11 text)")
c.execute("DELETE from flight")

base_url = 'http://www.variflight.com'
r = requests.get(url)
selector = etree.HTML(r.text)
b = selector.xpath('//*[@class="searchlist_innerli"]')
num = 0
if b:
    name = selector.xpath('//*[@class="tit"]/h1/@title')[0]
    log = "{0}航班存在信息：".format(name)
    r = requests.Session()
    resp = r.get(url)
    selector = etree.HTML(resp.text)
    mylist = selector.xpath('//*[@id="list"]/li')

    for selector in mylist:
        is_share = selector.xpath('a[@class="list_share"]//text()')  # 共享航班
        if (len(is_share) == 1):
            continue
        a = selector.xpath('div[@class="li_com"]/span[1]/b/a//text()')  # 航班信息
        f1 = a[0]
        f2 = a[1][:2]
        f3 = a[1]
        f4 = selector.xpath('div[@class="li_com"]/span[2]/@dplan')  # 计划起飞
        f5 = selector.xpath('div[@class="li_com"]/span[3]/img/@src')  # 实际起飞
        if f5:
            url = base_url + f5[0]
            resp = r.get(url)
            filename = './pictures' + '.png'
            with open(filename, 'wb') as f:
                f.write(resp.content)
            f5 = pytesseract.image_to_string(Image.open(filename))
            os.remove(filename)
            if len(f5) < 5:  # 若识别不出‘:’或者‘.’ 进行拼接
                f5 = f5[:2] + ':' + f5[2:]
        else:
            f5 = '--:--'

        f6 = selector.xpath('div[@class="li_com"]/span[4]/text()')  # 出发地
        f7 = selector.xpath('div[@class="li_com"]/span[5]/@aplan')  # 计划到达
        f8 = selector.xpath('div[@class="li_com"]/span[6]/text()')  # 实际到达
        f8 = re.sub(r"[\s+\.\!\/_,$%^*(+\"\')]+|[+?【】？~@#￥%……&*]+|\\n+|\\r+|(\\xa0)+|(\\u3000)+|\\t", "",
                    str(f8[0]))
        if f8:
            f8 = '--:--'
        else:
            f8 = selector.xpath('div[@class="li_com"]/span[6]/img/@src')  # 实际到达
            url = base_url + f8[0]
            resp = r.get(url)
            filename = './pictures' + '.png'
            with open(filename, 'wb') as f8:
                f8.write(resp.content)
            f8 = pytesseract.image_to_string(Image.open(filename))
            os.remove(filename)
            if len(f8) < 5:
                f8 = f8[:2] + ':' + f8[2:]

        f9 = selector.xpath('div[@class="li_com"]/span[7]/text()')  # 到达地
        h = selector.xpath('div[@class="li_com"]/span[8]/img/@src')  # 准点率
        f11 = selector.xpath('div[@class="li_com"]/span[9]/text()')  # 状态
        h = base_url + h[0]  # 准点率
        filename = './pictures' + '.png'

        q = r.get(h)
        with open(filename, 'wb') as t:
            t.write(q.content)
        q = pytesseract.image_to_string(Image.open(filename))
        os.remove(filename)
        if q == "100%":
            q = "99.99%"
        if len(q) < 6:
            q = q[:2] + '.' + q[2:]
        f10 = q[:5]

        value = "VALUES({},'{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')"\
            .format(num, f1, f2, f3, f4[0], f5, f6[0], f7[0], f8, f9[0], f10, f11[0])
        c.execute("INSERT INTO flight(f0,f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11) {}".format(value))
        num = num + 1

else:
    name = selector.xpath('//*[@id="byNumInput"]/@value')[0]
    log = "{0}航班不存在信息".format(name)

c.execute("commit")


c.execute("SELECT * FROM flight")

print(c.fetchall())
