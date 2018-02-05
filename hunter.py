#!/usr/bin/env python3

"""
Created by Wavky on 2018/2/4.
"""

from urllib.parse import urljoin, urlparse
import requests
import re
import threading
from datetime import datetime

# index = 'https://www.apple.com/jp/shop/browse/home/specialdeals/mac/macbook'
index = 'https://www.apple.com/jp/shop/browse/home/specialdeals/mac/macbook_pro'
target_range = '/jp/shop/product/'
keywords = ['言語','8GB']
interval = 5 * 60


# todo: use db to filter out checked url
# todo: get title


def get_host_path(url):
    up = urlparse(url)
    return up.scheme + "://" + up.netloc


def get_base_url(html):
    base = re.search(r'<base *href *= *[\'\"](.*?)[\'\"]', html, re.M | re.S)
    if base:
        base = base.group(1)
    return base


def get_title(link_element):
    """
    in purpose to extract the title text from <a> element
    :param link_element: example: <a>title</a>
    :return: string to title or None
    """
    title = re.search(r'<a\b.*>[^<]\s*(.*?)\s*<', link_element, re.M | re.S)
    if title:
        title = title.group(1)
    return title

def main():
    """
    Check our target is shown up or not.

    target_main refer to the index page
    target_sub refer to the sub page linked by target_main, which as the real working page here
    eureka is a list container for the target link from target_sub if it's page contain the keywords

    host refer to the scheme and host part of target_main site's url
    base refer to the url specified by <base> element
    """
    target_main = index
    host = get_host_path(target_main)

    log("start check")

    # type of result_main is HTML text of index page
    result_main = requests.get(target_main).text
    base = get_base_url(result_main) or ''

    link_elements = re.findall(r'<a\b.*?>.*?</a>', result_main, re.M | re.S)
    url_title_dict = {}
    for element in link_elements:
        url = get_url(element, host, base)
        if url:
            url_title_dict[url] = get_title(element) or ''

    # todo: find another way to shrink the list (replace target_range)
    target_sub = list(filter(lambda link: str(link).find(target_range) > -1, url_title_dict.keys()))
    eureka = []
    for link in target_sub:
        log("checking " + link + " ...")
        result_sub = requests.get(link).text
        for key in keywords:
            if result_sub.find(key) > -1:
                eureka.append((key, link))
    if eureka:
        for eu in eureka:
            log("Eureka! " + 'keyword: ' + eu[0] + '\t' + url_title_dict[eu[1]] + '\t' + eu[1])
    else:
        log("miss")


def get_url(link_element: str, host: str, base: str = ''):
    """
    get a full url from <a> element
    :param link_element:
    :param host: root url of the site
    :param base: <base> element url
    :return: None if there is no url
    """
    res = re.search(r'href *= *[\'\"]([^#].*?)[\'\"]', link_element, re.M | re.S)
    if res:
        res = res.group(1)
        if res.startswith("javascript:"):
            return None
        if res.startswith(("http://", "https://")):
            return res
        if res.startswith('/'):
            return urljoin(host, res)
        # maybe relative link
        return urljoin(base, res)
    return None


def polling():
    """
    setup timer and check
    """
    main()
    timer = threading.Timer(interval, polling)
    timer.start()


def log(text):
    print(get_timestamp() + str(text))


def get_timestamp():
    return str(datetime.now()) + " : "


polling()
