#!/usr/bin/env python3

"""
Created by Wavky on 2018/2/4.
"""

import re
import sys
import threading
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
import yagmail
from bs4 import BeautifulSoup

index = 'https://www.apple.com/jp/shop/browse/home/specialdeals/mac/macbook'
# index = 'https://www.apple.com/jp/shop/browse/home/specialdeals/mac/macbook_pro'
target_range = '/jp/shop/product/'
keywords = ['言語']
interval = 5 * 60


# todo: use db to filter out checked url


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
    Check our target is shown up or not.

    target_main refer to the index page
    target_sub refer to the sub page linked by target_main, which as the real working page here
    eureka is a list container for the target link from target_sub if it's page contain the keywords

    host refer to the scheme and host part of target_main site's url
    base refer to the url specified by <base> element
    """
    log("start check")

    # type of index_html is HTML text of index page
    index_html = ''
    try:
        index_html = requests.get(index).text
    except BaseException as errormsg:
        connection_error_process(index, str(errormsg))

    host = get_host_path(index)
    base = get_base_url(index_html) or ''

    url_title_dict = get_subject_links_from_index(index_html, host, base)
    eureka = find_target_from_subjects(url_title_dict.keys())

    if eureka:
        title = 'Eureka! From ' + urlparse(host).hostname
        msg = ''
        for eu in eureka:
            eu_msg = 'Keyword: ' + eu[0] + '\t\t' + url_title_dict[eu[1]] + '\t' + eu[1]
            log("Eureka! " + eu_msg)
            msg += eu_msg + '\n\n'
        send_mail(title, msg)
        log('Targets found, service shutting down...')
        sys.exit()
    else:
        log("miss")


def get_subject_links_from_index(index_html, host, base):
    """
    find targets link url and it's title
    :param index_html:
    :param host:
    :param base:
    :return: dict of (url, title)
    """
    link_elements = re.findall(r'<a\b.*?>.*?</a>', index_html, re.M | re.S)
    entire_url_title_dict = {}
    for element in link_elements:
        url = get_url(element, host, base)
        if url:
            title = BeautifulSoup(element, "html.parser").getText().strip()
            if url in entire_url_title_dict:
                entire_url_title_dict[url] = entire_url_title_dict[url] + ", " + title
            else:
                entire_url_title_dict[url] = title

    # todo: find another way to shrink the list (replace target_range)
    target_url_title_dict = dict(
        filter(lambda item: str(item[0]).find(target_range) > -1, entire_url_title_dict.items()))
    return target_url_title_dict


def find_target_from_subjects(subject_links):
    """
    :param subject_links: urls
    :return: subjects match keywords, dict of (keyword, url), or empty dict
    """
    eureka = []
    for link in subject_links:
        log("checking " + link + " ...")
        html_sub = ''
        try:
            html_sub = requests.get(link).text
        except BaseException as errormsg:
            connection_error_process(link, str(errormsg))

        for key in keywords:
            if html_sub.find(key) > -1:
                eureka.append((key, link))
    return eureka


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


def start_polling():
    """
    setup timer and check
    """
    main()
    timer = threading.Timer(interval, start_polling)
    timer.start()


def log(text):
    print(get_timestamp() + str(text))


def log_error(error_text):
    log('<<<Error>>> ' + error_text)


def get_timestamp():
    return str(datetime.now()) + " : "


def send_mail(title: str, body: str):
    try:
        account = 'wavky@foxmail.com'
        password = 'wbwxdgksyqjfbgce'
        host = 'smtp.qq.com'
        port = '465'
        send_to = 'wavky@icloud.com'
        yag = yagmail.SMTP(account, password, host, port)
        yag.send(send_to, title, body)
        log('mailing to ' + send_to)
    except BaseException as error:
        log_error(str(error))


def connection_error_process(url: str, errormsg: str):
    body_message = 'Access failed on ' + url + ', service shutting down...\n\nError message:\n' + errormsg
    log_error(body_message)
    send_mail('<<<Error>>>', body_message)
    sys.exit()


start_polling()
