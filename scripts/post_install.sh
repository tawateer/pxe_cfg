#!/bin/bash -x

install_type=$1
install_ver=$2


script_url="http://pxe.hy01.nosa.com/script"


# 修复安装之后的 Puppet 问题
echo "search nosa.com" >>/etc/resolv.conf


# Centos 7 需要加权限否则开机不执行 rc.local
chmod +x /etc/rc.d/rc.local


# 创建临时目录,机器安装完成之后会删除此目录
mkdir -p /tmp/install
cd /tmp/install


# 添加源(wandoulabs-release 是一个坑, 以后更新 wandoulabs-release 的话 此文件可能会被删除)
/bin/rm -f /etc/yum.repos.d/CentOS*
rpm -Uvh http://mirrors.internal.nosa.com/wandoulabs/6/x86_64/wandoulabs-release-0.0.17-1.el6.x86_64.rpm


# 安装 requests 模块, 请求资产和 DNS 系统会用到.
yum -y install python-requests


# 根据资产系统拿到主机名和ip, 并下载dns相关脚本
wget ${script_url}/assetapi.py
wget ${script_url}/wdstackapi.py
wget ${script_url}/dnsapi.py
wget ${script_url}/wddns


# 对 kvm_guest 执行初始化
if [[ "$install_type" == "kvm_guest" ]]
then
    wget -q -O- ${script_url}/config_kvm_guest.py |python

    echo "wget -q -O- ${script_url}/post_config_kvm_guest.sh |bash &>>/tmp/.post_config_kvm_guest.log ;sed -i '/post_config_kvm_guest.sh/d' /etc/rc.d/rc.local" >> /etc/rc.d/rc.local
    exit 0 
fi


# 非虚拟机执行通用脚本
wget -q -O- ${script_url}/config_common.py |python


if [[ "$install_type" == "kvm_host" ]]
then
    yum -y install qemu-kvm qemu-kvm-tools python-virtinst qemu-img libvirt bridge-utils guestfish
    echo "wget -q -O- ${script_url}/post_config_kvm_host.sh |bash &>>/tmp/.post_config_kvm_host.log ;sed -i '/post_config_kvm_host.sh/d' /etc/rc.d/rc.local" >> /etc/rc.d/rc.local

elif [[ "$install_type" == "docker_host" ]]
then
    lvcreate -Zy -n metadata -l 1%VG  docker
    lvcreate -Wy -n data     -l 49%VG docker
    lvcreate -Wy -n volumes  -l 50%VG docker
    mkfs.ext4 /dev/docker/volumes
    echo '/dev/docker/volumes /volumes ext4 defaults 0 2' >> /etc/fstab

    yum -y -q install docker

    # Minor hack for Docker
    mkdir /etc/systemd/system/docker.service.d/
    cat >> /etc/systemd/system/docker.service.d/no-private-mount.conf << EOF
[Service]
MountFlags=
EOF

fi
