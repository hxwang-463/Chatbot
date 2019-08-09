import requests
import pytesseract
import re
import os
from lxml import etree
from PIL import Image


def get_flights_list():
    base_url = 'http://www.variflight.com'

    dep = "pek"
    arr = "hrb"

    test = base_url+"/flight/{}-{}.html?AE71649A58c77".format(dep, arr)

    r = requests.get(test)

    selector = etree.HTML(r.text)

    b = selector.xpath('//*[@class="searchlist_innerli"]')

    if b:
        name = selector.xpath('//*[@class="tit"]/h1/@title')[0]
        log = "{0}航班存在信息：".format(name)
        print(log)
        # time.sleep(5)
        r = requests.Session()

        resp = r.get(test)

        selector = etree.HTML(resp.text)

        mylist = selector.xpath('//*[@id="list"]/li')
        # print(mylist)

        for selector in mylist:
            is_share = selector.xpath('a[@class="list_share"]//text()')  # 共享航班
            if (len(is_share) == 1):
                continue
            a = selector.xpath('div[@class="li_com"]/span[1]/b/a//text()')  # 航班信息
            a = a[0] + '' + a[1]

            b = selector.xpath('div[@class="li_com"]/span[2]/@dplan')  # 计划起飞

            c = selector.xpath('div[@class="li_com"]/span[3]/img/@src')  # 实际起飞
            if c:
                url = base_url + c[0]
                resp = r.get(url)
                filename = './pictures' + re.search(r's=(.*?)==', url).group(0) + '.png'
                with open(filename, 'wb') as f:
                    f.write(resp.content)
                c = pytesseract.image_to_string(Image.open(filename))
                os.remove(filename)
                if len(c) < 5:  # 若识别不出‘:’或者‘.’ 进行拼接
                    c = c[:2] + ':' + c[2:]
            else:
                c = '--:--'

            d = selector.xpath('div[@class="li_com"]/span[4]/text()')  # 出发地

            e = selector.xpath('div[@class="li_com"]/span[5]/@aplan')  # 计划到达

            f = selector.xpath('div[@class="li_com"]/span[6]/text()')  # 实际到达
            f = re.sub(r"[\s+\.\!\/_,$%^*(+\"\')]+|[+?【】？~@#￥%……&*]+|\\n+|\\r+|(\\xa0)+|(\\u3000)+|\\t", "",
                       str(f[0]))
            if f:
                f = '--:--'
            else:
                f = selector.xpath('div[@class="li_com"]/span[6]/img/@src')  # 实际到达
                url = base_url + f[0]
                resp = r.get(url)
                filename = './pictures' + re.search(r's=(.*?)==', url).group(0) + '.png'
                with open(filename, 'wb') as f:
                    f.write(resp.content)
                f = pytesseract.image_to_string(Image.open(filename))
                os.remove(filename)
                if len(f) < 5:
                    f = f[:2] + ':' + f[2:]

            g = selector.xpath('div[@class="li_com"]/span[7]/text()')  # 到达地

            h = selector.xpath('div[@class="li_com"]/span[8]/img/@src')  # 准点率

            i = selector.xpath('div[@class="li_com"]/span[9]/text()')  # 状态

            h = base_url + h[0]  # 准点率
            filename = './pictures' + re.search(r's=(.*?)=', h).group(0) + '.png'

            q = r.get(h)

            with open(filename, 'wb') as t:
                t.write(q.content)
            q = pytesseract.image_to_string(Image.open(filename))
            os.remove(filename)
            if len(q) < 5:
                q = q[:2] + ':' + q[2:]

            mydict = {
                "title": a,  # 航班信息
                "start_time": b[0],  # 计划起飞
                "actual_start_time": c,  # 实际起飞
                "start_place": d[0],  # 出发地
                "arrive_time": e[0],  # 计划到达
                "actual_arrive_time": f,  # 实际到达
                "arrive_place": g[0],  # 到达地
                "on-time rate": q,  # 准点率
                "status": i[0],  # 状态
            }

            print(mydict)
    else:
        name = selector.xpath('//*[@id="byNumInput"]/@value')[0]
        log = "{0}航班不存在信息".format(name)
        print(log)


get_flights_list()
