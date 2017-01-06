#!/bin/bash -x

install_type=$1
install_ver=$2


script_url="http://pxe.internal.DOMAIN.COM/script"


# 修复安装之后的 Puppet 问题
echo "search DOMAIN.COM" >>/etc/resolv.conf


# 同步时间, 否则请求 Puppet ca 可能失败
ntpdate ntp.DOMAIN.COM &>/dev/null ; /sbin/hwclock -w


# Centos 7 需要加权限否则开机不执行 rc.local
chmod +x /etc/rc.d/rc.local


# 创建临时目录,机器安装完成之后会删除此目录
mkdir -p /tmp/install
cd /tmp/install


# 添加源(wandoulabs-release 是一个坑, 以后更新 wandoulabs-release 的话 此文件可能会被删除)
/bin/rm -f /etc/yum.repos.d/CentOS*
rpm -Uvh http://mirrors.internal.DOMAIN.COM/wandoulabs/6/x86_64/wandoulabs-release-0.0.24-1.el6.x86_64.rpm


# 安装 requests 模块, 请求资产和 DNS 系统会用到.
yum -y install python-requests


# 根据资产系统拿到主机名和ip, 并下载dns相关脚本
wget ${script_url}/assetapi.py
wget ${script_url}/wdstackapi.py


# 对 kvm_guest 执行初始化
if [[ "$install_type" == "kvm_guest" ]]
then
    wget -q -O- ${script_url}/config_kvm_guest.py |python

    # 重启之后虚拟机没网络, 所以先下好脚本
    wget -q ${script_url}/post_config_kvm_guest.sh -O post_config_kvm_guest.sh
    echo "cd /tmp/install &&sh -x post_config_kvm_guest.sh &>>/tmp/.post_config_kvm_guest.log ;sed -i '/post_config_kvm_guest.sh/d' /etc/rc.d/rc.local" >> /etc/rc.d/rc.local
    exit 0
fi


# 非虚拟机执行通用脚本
wget -q -O- ${script_url}/config_common.py |python


if [[ "$install_type" == "kvm_host" ]]
then
    # 如果此时用 yum 安装 kvm, 对于 Centos7 会有很奇怪的问题, 现象是机器启动卡住, /etc/rc.d/rc.local 不执行,
    # 原因待解, 把 安装 kvm 命令放在 post_config_kvm_host.sh 就没问题. 
    #yum -y install qemu-kvm qemu-kvm-tools python-virtinst qemu-img libvirt bridge-utils guestfish
    echo "wget -q -O- ${script_url}/post_config_kvm_host.sh |bash &>>/tmp/.post_config_kvm_host.log ;sed -i '/post_config_kvm_host.sh/d' /etc/rc.d/rc.local" >>/etc/rc.d/rc.local

elif [[ "$install_type" == "docker_host" ]]
then
    # Create Logical Volumes for Docker
    lvcreate -y -n docker -l 100%VG docker
    mkfs.btrfs /dev/docker/docker
    echo '/dev/docker/docker /var/lib/docker btrfs defaults 0 2' >>/etc/fstab

    yum -y install docker-engine
    systemctl enable docker

    ## Disable SELinux feature and enforce insecure registry
    ## Disable Red Hat registry and Docker.io registry, enable private registry
	echo "SELINUX=disabled
SELINUXTYPE=targeted" > /etc/selinux/config

   echo "ADD_REGISTRY='--add-registry hub.internal.DOMAIN.COM'
BLOCK_REGISTRY=''
OPTIONS='--selinux-enabled --log-driver=journald --insecure-registry hub.internal.DOMAIN.COM --debug=true -H unix:///var/run/docker.sock'" > /etc/sysconfig/docker

   mkdir -p /etc/systemd/system/docker.service.d
   echo '[Service]
EnvironmentFile=-/etc/sysconfig/docker
EnvironmentFile=-/etc/sysconfig/docker-storage
EnvironmentFile=-/etc/sysconfig/docker-network
ExecStart=
ExecStart=/usr/bin/dockerd $OPTIONS \
          $DOCKER_STORAGE_OPTIONS \
          $DOCKER_NETWORK_OPTIONS \
          $BLOCK_REGISTRY \
          $INSECURE_REGISTRY' > /etc/systemd/system/docker.service.d/docker.conf

    yum -y install td-agent
    systemctl enable td-agent
    td-agent-gem install --http-proxy http://sa-monitor-proxy-ct0.db01:8080 fluent-plugin-forest fluent-plugin-rewrite-tag-filter fluent-plugin-record-reformer
fi


# 物理机装机之后执行自定义脚本, 虚拟机不在此
if [[ "$install_type" != "kvm_guest" ]]
then
    wget "http://wdstack.internal.DOMAIN.COM/script/gen_user_data.sh" -O /root/gen_user_data.sh
    echo "sh /root/gen_user_data.sh &>>/root/gen_user_data.log" >>/etc/rc.d/rc.local
fi
