#!/usr/bin/env python
# -*- coding: utf-8 -*-


import subprocess


def shell(cmd):
    """ 执行命令.

    """
    process = subprocess.Popen(
        args=cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    std_out, std_err = process.communicate()
    return_code = process.poll()
    return return_code, std_out, std_err


def kernel_conf(key, value, oper):
    """ 根据条件修改内核参数.

    key 是内核选项;
    value 是内核选项的值;
    oper 是操作方式.

    如果 oper 是 equal 时, 当前系统 key 的值不等于 value 时, 则修改成 value
    如果 oper 是 less 时, 当前系统 key 的值小于 value 时, 则修改成 value
    如果 oper 是 great 时, 当前系统 key 的值大于 value 时, 则修改成 value

    """
    cmd = """sysctl %s |awk -F "=" '{print $NF}'""" % key
    rc, so, se = shell(cmd)
    curr_value = so.strip()
    if oper == "equal":
        if curr_value != str(value):
            cmd = "sysctl -w %s=%s" % (key, value)
            rc, so, se = shell(cmd)
            return so
    elif oper == "less":
        if int(curr_value) < value:
            cmd = "sysctl -w %s=%s" % (key, value)
            rc, so, se = shell(cmd)
            return so
    elif oper == "great":
        if int(curr_value) > value:
            cmd = "sysctl -w %s=%s" % (key, value)
            rc, so, se = shell(cmd)
            return so


def main():
    equal_dict = {
        "vm.swappiness": 0,
        "net.ipv4.tcp_tw_reuse": 1,
        "net.ipv4.tcp_tw_recycle": 0,
        "net.ipv4.conf.default.rp_filter": 1,
        "net.ipv4.tcp_syncookies": 1,
        "kernel.sysrq": 0,
        "kernel.msgmnb": 65536,
        "kernel.msgmax": 65536,
        "kernel.shmmax": 68719476736,
        "kernel.shmall": 4294967296,
        "kernel.panic": 60,
        "net.ipv4.icmp_echo_ignore_broadcasts": 1,
        "net.ipv4.icmp_ignore_bogus_error_responses": 1,
        "net.ipv4.conf.all.accept_redirects": 0,
        "net.ipv4.conf.all.rp_filter": 0,
        "net.ipv4.conf.all.log_martians": 1,
        "net.ipv4.conf.all.arp_announce": 2,
        "net.ipv4.conf.all.arp_ignore": 1,
        "net.ipv4.tcp_timestamps": 0,
        "net.ipv4.tcp_synack_retries": 2,
        "net.ipv4.tcp_syn_retries": 2,
        "net.ipv4.tcp_fin_timeout": 30,
        "net.ipv4.tcp_keepalive_time": 600,
        "net.ipv4.tcp_keepalive_intvl": 15,
        "net.ipv4.tcp_keepalive_probes": 5,   
    }

    less_dict = {
        "net.ipv4.tcp_max_syn_backlog": 65536,
        "net.core.netdev_max_backlog":  32768,
        "net.core.somaxconn": 32768,
        "net.ipv4.tcp_max_orphans": 3276800,
        "net.ipv4.tcp_max_tw_buckets": 524288,
        "fs.file-max": 1024000
    }

    for equal in equal_dict:
        print kernel_conf(equal, equal_dict[equal], "equal")

    for less in less_dict:
        print kernel_conf(less, less_dict[less], "less")

    # 对 net.ipv4.tcp_mem 特殊处理.
    cmd = """sysctl net.ipv4.tcp_mem |awk -F "=" '{print $NF}' |\
            awk '{print $1" "$2" "$3}'""" 
    rc, so, se = shell(cmd)
    if so.strip() != "94500000 915000000 927000000":
        cmd="""sysctl -w net.ipv4.tcp_mem='94500000 915000000 927000000'"""
        rc, so, se = shell(cmd)
        print so

    # 对 net.ipv4.ip_local_port_range 特殊处理.
    cmd = """sysctl net.ipv4.ip_local_port_range |awk -F "=" '{print $NF}' |\
            awk '{print $1}'"""
    rc, so, se = shell(cmd)
    if int(so.strip()) > 10000:
        cmd="""sysctl -w net.ipv4.ip_local_port_range='10000	65535'"""
        rc, so, se = shell(cmd)
        print so


if __name__ == '__main__':
    main()
