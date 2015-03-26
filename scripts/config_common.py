#!/bin/env python
# -*- coding: utf-8 -*-
# 物理机装机阶段的初始化脚本。


import json
import urllib
import urllib2
import subprocess
import os
import sys
import time

from assetapi import get_hostname, get_ip 
from wdstackapi import get_idc_usage, set_hostname_ip


def shell(cmd):
    process = subprocess.Popen(
        args=cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    std_out, std_err = process.communicate()
    return_code = process.poll()
    return return_code, std_out, std_err


def main():
    # 获取到内网IP, network和网关
    ip_cmd = r"ip a | grep -Po 'inet 10\.\d+\.\d+\.\d+' | awk '{print $2}'"
    rc, so, se = shell(ip_cmd)
    ip = so.strip()
    netmask = "255.255.255.0"
    network = ".".join(ip.split(".")[:-1]) + ".0"
    gateway = ".".join(ip.split(".")[:-1]) + ".1"
    print ip, netmask, network, gateway

    # 获取sn
    sn_cmd = """/usr/sbin/dmidecode -s system-serial-number"""
    rc, so, se = shell(sn_cmd)
    sn = so.strip()
    print sn

    # 首选去物理装机系统拿到sn的idc和usage, 以此到资产请求可用的hostname 
    data = get_idc_usage(sn)
    idc = data["message"]["idc"]
    usage = data["message"]["usage"]
    print idc, usage

    # 去资产请求hostname和ip
    hostname = get_hostname(idc, usage)["hostname"]
    print hostname

    ip = get_ip("%s/24" % network)["msg"]
    print ip

    # 把获取到hostname,ip,post到装机系统,以便装机系统统一处理
    print set_hostname_ip(sn, hostname, ip)

    # 配置hostname
    shell("echo %s >/etc/hostname" % hostname)
    _hostname_conf = """NETWORKING=yes
NETWORKING_IPV6=no
HOSTNAME=%s
""" % hostname
    with open("/etc/sysconfig/network", 'w') as f:
        f.write(_hostname_conf)

    # 配置网关
    _gateway_conf = """any net 172.16.0.0/12 gw %s
any net 192.168.0.0/16 gw %s
any net 10.0.0.0/8 gw %s
any net 100.64.0.0/16 gw %s
any net 0.0.0.0/0 gw %s """ % (gateway, gateway, gateway, gateway, gateway)
    with open("/etc/sysconfig/static-routes", 'w') as f:
        f.write(_gateway_conf)

    # 开机之后配置内网IP,DNS和Puppet
    cmd = r"""
cat > post_nic_setup.sh << EOF
#/bin/bash

sed -i "/post_nic_setup.sh/d" /etc/rc.d/rc.local

echo "DEVICE=em2
BOOTPROTO=static
IPADDR=%s
NETMASK=%s
ONBOOT=yes
TYPE=Ethernet" > /etc/sysconfig/network-scripts/ifcfg-em2
service network restart ||systemctl restart network.service

EOF
echo "cd /tmp/install &&sh -x post_nic_setup.sh &>post_nic_setup.log " >>/etc/rc.d/rc.local

echo "cd /tmp/install &&python wddns -a |grep -i success ;sed -i '/wddns/d' /etc/rc.d/rc.local " >>/etc/rc.d/rc.local

echo "yum -y install puppet ;chkconfig puppet on ;puppet agent -t --server puppetlb.corp.nosa.com --ca_server puppetca.corp.nosa.com ;sed -i '/puppet/d' /etc/rc.d/rc.local && /bin/rm -rf /tmp/install " >>/etc/rc.d/rc.local
""" % (ip, netmask)
    shell(cmd)


if __name__ == '__main__':
    main()
