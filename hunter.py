#!/usr/bin/env python3

"""
Created by Wavky on 2018/2/4.
"""

from urllib.parse import urljoin, urlparse
import requests
import re
import threading
from datetime import datetime

index = 'https://www.apple.com/jp/shop/browse/home/specialdeals/mac/macbook'
# index = 'https://www.apple.com/jp/shop/browse/home/specialdeals/mac/macbook_pro'
target_range = '/jp/shop/product/'
keywords = '言語'
interval = 5 * 60


# todo: use db to filter out checked url
# todo: support multiple keywords


def get_host_path(url):
    up = urlparse(url)
    return up.scheme + "://" + up.netloc


def get_base_url(html):
    base = re.search(r'<base *href *= *[\'\"](.*?)[\'\"]', html, re.M | re.S)
    if base:
        base = base.group(1)
    return base


def main():
    """
    check our target is shown up or not
    """
    # index
    target_main = index
    host = get_host_path(target_main)

    log("start check")

    # HTML text of index page
    result_main = requests.get(target_main).text
    base = get_base_url(result_main) or ''
    print(base)

    link_elements = re.findall(r'<a[ >].*?</a>', result_main, re.M | re.S)
    urls = set()
    for element in link_elements:
        url = get_url(element, host, base)
        if url:
            urls.add(url)


    # todo: find another way to shrink the list
    # products
    target_sub = list(filter(lambda link: str(link).find(target_range) > -1, urls))
    eureka = []
    for link in target_sub:
        log("check " + link + " ...")
        result_sub = requests.get(link).text
        if result_sub.find(keywords) > -1:
            eureka.append(link)
    if eureka:
        log(eureka)
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
