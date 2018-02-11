#!/usr/bin/env python3

"""
Created by Wavky on 2018/2/4.
"""

import pickle
import re
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
import yagmail
from bs4 import BeautifulSoup
from loopytimer import LoopyTimer

index = 'https://www.apple.com/jp/shop/browse/home/specialdeals/mac/macbook'
# index = 'https://www.apple.com/jp/shop/browse/home/specialdeals/mac/macbook_pro'
target_range = '/jp/shop/product/'
keywords = ['言語']
check_interval = 5 * 60
status_report_interval = 3 * 60 * 60

cache_filename = 'cache.pkl'
log_filename = 'log.txt'


class Cache(object):

    def __init__(self, missed: list = (), found: list = ()):
        self.missed_list = missed
        self.found_list = found

    def __contains__(self, url):
        return url in self.missed_list + self.found_list


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

    cache = restore_cache()
    if cache is None:
        cache = Cache()

    # type of index_html is HTML text of index page
    index_html = ''
    try:
        index_html = requests.get(index).text
    except BaseException as errormsg:
        connection_error_process(index, str(errormsg))

    host = get_host_path(index)
    base = get_base_url(index_html) or ''

    url_title_dict = get_subject_links_from_index(index_html, host, base)
    # filter out that links have been log in cache before, no need to recheck
    latest_url_title_dict = dict(filter(lambda url_title: url_title[0] not in cache, url_title_dict.items()))

    eureka = find_target_from_subjects(latest_url_title_dict.keys())

    cache.found_list += [item[1] for item in eureka]
    cache.missed_list += set(latest_url_title_dict.keys()) - set(cache.found_list)
    serialize_cache(cache)

    if eureka:
        title = 'Eureka! From ' + urlparse(host).hostname
        msg = ''
        for eu in eureka:
            eu_msg = 'Keyword: ' + eu[0] + '\t【【' + latest_url_title_dict[eu[1]] + '】】\t' + eu[1]
            log("Eureka! " + eu_msg)
            msg += eu_msg + '\n\n'
        send_mail(title, msg)
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
    :return: subjects match keywords, list of (keyword, url), or empty dict
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
    setup timer and go
    """
    # initial run
    main()

    check_timer = LoopyTimer(check_interval, main)
    check_timer.start()

    report_timer = LoopyTimer(status_report_interval, report_status)
    report_timer.start()


def report_status():
    cache = restore_cache()
    found = ''
    if cache:
        found = str(cache.found_list)
    title = 'Treasure Hunter Status OK'
    body = get_timestamp() + '\nFound: ' + (found or 'Nothing.') + '\nReport over.'
    to = 'wavky@foxmail.com'
    send_mail(title, body, to)


def log(text):
    logmsg = get_timestamp() + str(text)
    print(logmsg)
    try:
        with open(log_filename, 'a', encoding='utf-8') as cache_file:
            cache_file.write(logmsg + '\n')
            cache_file.flush()
    except:
        print('<<<Error>>> Failed to write the log file.')


def log_error(error_text):
    """
    base on log(), don't invoke this from log()

    :param error_text:
    :return:
    """
    log('<<<Error>>> ' + error_text)


def get_timestamp():
    return str(datetime.now()) + " : "


def serialize_cache(cache: Cache):
    try:
        with open(cache_filename, 'wb') as cache_file:
            pickle.dump(cache, cache_file)
    except:
        log_error('Cache writen failure.')


def restore_cache():
    cache = None
    try:
        with open(cache_filename, 'rb') as cache_file:
            cache = pickle.load(cache_file)
    except:
        log_error('Cache read failure.')
    finally:
        return cache


def send_mail(title: str, body: str, to: str = 'wavky@icloud.com'):
    try:
        account = 'wavky@foxmail.com'
        password = 'wbwxdgksyqjfbgce'
        host = 'smtp.qq.com'
        port = '465'
        yag = yagmail.SMTP(account, password, host, port)
        yag.send(to, title, body)
        log('mailing to ' + to)
    except BaseException as error:
        log_error(str(error))


def connection_error_process(url: str, errormsg: str):
    body_message = 'Access failed on ' + url + ', service shutting down...\n\nError message:\n' + errormsg
    log_error(body_message)
    send_mail('<<<Error>>>', body_message)
    sys.exit()


start_polling()
