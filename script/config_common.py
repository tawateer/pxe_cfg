#!/bin/env python
# -*- coding: utf-8 -*-

""" 物理机装机阶段的初始化脚本.

"""

import json
import subprocess
import sys
import logging

from assetapi import apply_hostname_ip
from wdstackapi import get_idc_usage, set_hostname_ip


logging.basicConfig(
    level=logging.DEBUG, stream=sys.stdout, format='%(message)s')


PUPPET_CA_HOST = "puppetca.corp.DOMAIN.COM:8140"


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


def main():
    # 获取到内网 ip, network 和网关.
    ip_cmd = r"ip a | grep -Po 'inet 10\.\d+\.\d+\.\d+' | awk '{print $2}'"
    ip = shell(ip_cmd, strip=True)
    netmask = "255.255.255.0"
    network = ".".join(ip.split(".")[:-1]) + ".0/24"
    gateway = ".".join(ip.split(".")[:-1]) + ".1"
    logging.info([ip, netmask, network, gateway])

    # 获取 sn.
    sn_cmd = "/usr/sbin/dmidecode -s system-serial-number"
    sn = shell(sn_cmd, strip=True)
    logging.info(sn)

    # 首选去物理装机系统拿到 sn 的 idc 和 usage, 以此到资产请求可用的 hostname.
    data = get_idc_usage(sn)
    idc = data["idc"]
    usage = data["usage"]
    logging.info([idc, usage])

    # 去资产请求 hostname 和 ip.
    import re
    if re.match("vmh", usage) is None:
        _type = "raw"
    else:
        _type = "kvm"
    hostname, ip = apply_hostname_ip(sn, _type, usage, idc, network)
    logging.info([hostname, ip])

    # 把获取到 hostname, ip, post 到装机系统, 以便装机系统统一处理.
    set_hostname_ip(sn, hostname, ip)

    # 配置 hostname.
    cmds = [
        "echo %s > /etc/hostname" % hostname,
        "sed -i '/HOSTNAME/s/.*/HOSTNAME=%s/g' /etc/sysconfig/network" % hostname,
        "hostname -F /etc/hostname"
    ]
    map(shell, cmds)

    # 配置网关.
    # 这里有一个坑, 在装 kvm_host 的情况下, 重启之后会把内网 ip
    # 配置在 br2 上面, route-em2 需要改成 route-br2, 否则 kvm_host
    # 网关有问题, 导致装机失败.
    with open("/etc/sysconfig/network-scripts/route-em2", 'w') as f:
        f.write("192.168.0.0/16 via %s\n" % gateway)
        f.write("10.0.0.0/8 via %s\n" % gateway)
        f.write("100.64.0.0/16 via %s\n" % gateway)
        f.write("0.0.0.0/0 via %s\n" % gateway)

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
service network restart || systemctl restart network.service

EOF
echo "cd /tmp/install && sh -x post_nic_setup.sh &>/tmp/post_nic_setup.log " >>/etc/rc.d/rc.local

echo "yum -y install puppet ; /usr/bin/puppet agent --onetime --no-daemonize --server=puppetlb.corp.DOMAIN.COM --ca_server=puppetca.corp.DOMAIN.COM --debug &>/tmp/post-puppet.log ; sed -i '/puppet/d' /etc/rc.d/rc.local && /bin/rm -rf /tmp/install " >>/etc/rc.d/rc.local
""" % (ip, netmask)
    shell(cmd)


if __name__ == '__main__':
    main()
