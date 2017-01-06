#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import urllib2
import cookielib
import urllib
import json


WDSTACK_HOST = "pxe.internal.DOMAIN.COM"
WDSTACK_AUTH_USERNAME= "autodeploy"
WDSTACK_AUTH_PASSWD = ''
WDSTACK_AUTH_API = ''


class WdstackApi(object):
    def __init__(self, host_url=WDSTACK_HOST, username=WDSTACK_AUTH_USERNAME, \
            password=WDSTACK_AUTH_PASSWD, auth_uri=WDSTACK_AUTH_API):
        self.is_login = False
        self.host_url = host_url
        self.username = username
        self.password = password
        self.auth_uri = auth_uri

        self.login()
        if not self.is_login:
            raise LoginException("asset auth failed.")

    def login(self):
        auth_url = r"http://" + self.host_url + r"/" + self.auth_uri
        cookie = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
        urllib2.install_opener(opener)
        data = urllib.urlencode({"username": self.username, 'password': self.password})
        login_response = urllib2.urlopen(auth_url, data)
        response = login_response.read()

        ret_dict = json.loads(response)

        # update to check the response content to check if passed
        # authentication
        if ret_dict["result"] == "success":
            self.is_login = True
        else:
            self.is_login = False

    def post_wrapper(self, url, data_dict, json_loads=True):
        data = urllib.urlencode(data_dict)
        visit_url = r"http://" + self.host_url + r"/" + url
        login_response = urllib2.urlopen(visit_url, data)
        response = login_response.read()
        if json_loads:
            return json.loads(response)
        else:
            return response

    def get_wrapper(self, url, data_dict, json_loads=True):
        data = urllib.urlencode(data_dict)
        visit_url = r"http://" + self.host_url + r"/" + url
        login_response = urllib2.urlopen(visit_url + "?" + data)
        response = login_response.read()
        if json_loads:
            return json.loads(response)
        else:
            return response


def get_idc_usage(sn):

    _wdstack_oj = WdstackApi()

    data_dict = {
        "sn": sn
    }

    ret = _wdstack_oj.get_wrapper("api/v1/pm/message", data_dict)
    return ret


def set_hostname_ip(sn, hostname, ip):

    _wdstack_oj = WdstackApi()

    data_dict = {
        "sn": sn,
        "hostname": hostname,
        "ip": ip
    }

    ret = _wdstack_oj.post_wrapper("api/v1/pm/message", data_dict, json_loads=False)
    return ret
