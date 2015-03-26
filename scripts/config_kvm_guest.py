#!/bin/env python
# -*- coding: utf-8 -*-
# 虚拟机装机阶段的初始化脚本。


import os
import json
import urllib
import urllib2
import subprocess


def shell(cmd):
    process = subprocess.Popen(
        args=cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    std_out, std_err = process.communicate()
    return_code = process.poll()
    return return_code, std_out, std_err


def gethostname(url, ip):
    """ 和物理机去资产系统请求不同, 
        此处根据IP向虚拟机管理系统请求hostname
        (虚拟机管理系统已向资产申请好hostname和ip)
    """
    postdata = urllib.urlencode({"ip": ip})
    request = urllib2.Request(url, postdata)
    response = urllib2.urlopen(request)
    result = json.loads(response.read())
    return result["message"]


def main():
    # 虚拟机管理系统的url
    vmurl = "http://wdstack.hy01.nosa.com/api/v1/vm/query/"

    # 获取内网IP
    ip_cmd = r"ip a | grep -Po 'inet 10\.\d+\.\d+\.\d+' | awk '{print $2}'"
    rc, so, se = shell(ip_cmd)
    ip = so.strip()
    print ip

    # 去虚拟机管理系统请求hostname,netmask,gateway.
    data = gethostname(vmurl, ip)
    hostname = data["hostname"]
    netmask = data["netmask"]
    gateway = data["gateway"]
    print hostname, netmask, gateway

    # 配置hostname
    shell("echo %s >/etc/hostname" % hostname) 
    _hostname_conf = """NETWORKING=yes
NETWORKING_IPV6=no
HOSTNAME=%s
""" % hostname
    with open("/etc/sysconfig/network", 'w') as f:
        f.write(_hostname_conf)

    # 设置网关
    _gateway_conf = """any net 172.16.0.0/12 gw %s
any net 192.168.0.0/16 gw %s
any net 10.0.0.0/8 gw %s
any net 100.64.0.0/16 gw %s
any net 0.0.0.0/0 gw %s """ % (gateway, gateway, gateway, gateway, gateway)
    with open("/etc/sysconfig/static-routes", 'w') as f:
        f.write(_gateway_conf)

    # 设置内网IP
    _internal_device_conf = """DEVICE=em2
BOOTPROTO=static
IPADDR=%s
NETMASK=%s
ONBOOT=yes
TYPE=Ethernet""" % (ip, netmask)
    with open("/etc/sysconfig/network-scripts/ifcfg-em2", 'w') as f:
        f.write(_internal_device_conf)

    # 删除eth0
    deleth0_cmd = "/bin/rm -f /etc/sysconfig/network-scripts/ifcfg-eth0 "
    shell(deleth0_cmd)


if __name__ == '__main__':
    main()
