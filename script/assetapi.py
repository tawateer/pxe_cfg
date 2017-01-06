#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
import json
import requests


logging.basicConfig(
    level=logging.DEBUG, stream=sys.stdout, format='%(message)s')

ASSET_HOST = "loki.hy01.internal.DOMAIN.COM"
ASSET_APPLY_API = "/api/asset/apply"


def apply_hostname_ip(sn, _type, hostname_key, idc, network):
    """ 从资产系统获取主机名和 IP.

    对于物理机, sn 即是它的 sn, 对于虚拟机需要先生成一个 sn(uuid).

    _type 表示机器类型, 有三种 vm, kvm, raw

    hostname_key 和 idc 决定主机名;
    network 决定 ip.

    """
    if "*" in hostname_key:
        key = "hostname_pattern"
	hostname_key = hostname_key + "." + idc
    else:
        key = "hostname_prefix"
    url = "http://" + ASSET_HOST + ASSET_APPLY_API
    data = {
        "sn": sn,
        "type": _type,
        key: hostname_key,
        "idc": idc,
        "network": network
    }
    headers = {"Content-Type": "application/json"}

    return_text = requests.post(url, data=json.dumps(data), headers=headers)
    return_json = return_text.json()
    logging.info([return_text.status_code, return_text.text])
    return return_json["hostname"], return_json["private_ip"]
