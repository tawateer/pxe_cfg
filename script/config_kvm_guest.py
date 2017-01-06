#!/bin/env python
# -*- coding: utf-8 -*-

""" 虚拟机装机阶段的初始化脚本.

"""

import sys
import subprocess
import logging

import requests


logging.basicConfig(
    level=logging.DEBUG, stream=sys.stdout, format='%(message)s')


def shell(cmd, exception=True, strip=False):
    process = subprocess.Popen(args = cmd, 
        stdout = subprocess.PIPE, stderr = subprocess.PIPE, 
        shell = True)
    std_out, std_err = process.communicate()
    return_code = process.poll()

    if return_code == 0:
        logging.info("cmd:{cmd}, stdout:{std_out}".format(cmd=cmd, std_out=std_out))
    else:
        message = "cmd:{cmd}, std_err:{std_err}".format(cmd=cmd, std_err=std_err)
        logging.warning(message)
        if exception:
            raise Exception(message)
        else:
            return
    if strip:
        return std_out.strip()
    else:
        return std_out


def get_hostname(ip):
    """ 和物理机去资产系统请求不同, 此处根据 ip 向虚拟机管理系统请求 hostname
        (虚拟机管理系统已向资产申请好 hostname 和 ip).

    """
    url = "http://wdstack.internal.DOMAIN.COM/api/v1/vm/query/?ip=%s" % ip
    return requests.get(url).json()


def main():
    # 获取内网 ip.
    ip_cmd = r"ip a | grep -Po 'inet 10\.\d+\.\d+\.\d+' | awk '{print $2}'"
    ip = shell(ip_cmd, strip=True)
    logging.info(ip)

    # 去虚拟机管理系统请求 hostname, netmask, gateway.
    data = get_hostname(ip)
    hostname = data["hostname"]
    netmask = data["netmask"]
    gateway = data["gateway"]
    logging.info([hostname, netmask, gateway])

    # 配置 hostname.
    shell("echo %s >/etc/hostname" % hostname) 
    hostname_conf = """NETWORKING=yes
NETWORKING_IPV6=no
HOSTNAME=%s
""" % hostname
    with open("/etc/sysconfig/network", 'w') as f:
        f.write(hostname_conf)

    # 设置网关.
    with open("/etc/sysconfig/network-scripts/route-em2", 'w') as f:
        f.write("192.168.0.0/16 via %s\n" % gateway)
        f.write("10.0.0.0/8 via %s\n" % gateway)
        f.write("100.64.0.0/16 via %s\n" % gateway)
        f.write("0.0.0.0/0 via %s\n" % gateway)

    # 设置内网 ip.
    int_device_conf = """DEVICE=em2
BOOTPROTO=static
IPADDR=%s
NETMASK=%s
ONBOOT=yes
TYPE=Ethernet""" % (ip, netmask)
    with open("/etc/sysconfig/network-scripts/ifcfg-em2", 'w') as f:
        f.write(int_device_conf)

    # 删除 eth0.
    deleth0_cmd = "/bin/rm -f /etc/sysconfig/network-scripts/ifcfg-eth0"
    shell(deleth0_cmd)


if __name__ == '__main__':
    main()
