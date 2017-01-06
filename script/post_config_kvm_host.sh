#!/bin/bash
# 宿主机装机之后的初始化脚本.


# 判断是否是虚拟机
if /usr/sbin/dmidecode -s system-product-name |grep -i kvm >/dev/null
then
    echo "KVM guest is running."
    exit 1
fi


# 安装 kvm,  重启 libvirtd
yum -y install qemu-kvm qemu-kvm-tools python-virtinst qemu-img libvirt bridge-utils guestfish
lsmod |grep kvm
service libvirtd restart ||systemctl restart libvirtd.service


# 删除virbr0(virbr0使用的是 NAT 模式,我们使用桥接)
#/bin/rm -rf /etc/libvirt/qemu/networks
virsh net-list
virsh net-destroy default
virsh net-undefine default
service libvirtd restart ||systemctl restart libvirtd.service


# 配置桥接网络
PIP=$(ip a |grep -Po 'inet 10\.\d+\.\d+\.\d+' |awk '{print $2}')

> /etc/sysconfig/network-scripts/ifcfg-br1
cat > /etc/sysconfig/network-scripts/ifcfg-br1 <<EOF
DEVICE="br1"
BOOTPROTO="static"
NM_CONTROLLED="yes"
ONBOOT="yes"
TYPE=Bridge
EOF

> /etc/sysconfig/network-scripts/ifcfg-em1
cat > /etc/sysconfig/network-scripts/ifcfg-em1 <<EOF
DEVICE="em1"
NM_CONTROLLED="yes"
ONBOOT="yes"
TYPE="Ethernet"
BRIDGE=br1
EOF

> /etc/sysconfig/network-scripts/ifcfg-br2
cat > /etc/sysconfig/network-scripts/ifcfg-br2 <<EOF
DEVICE=br2
BOOTPROTO=static
ONBOOT=yes
IPADDR=${PIP}
NETMASK=255.255.255.0
TYPE=Bridge
EOF

> /etc/sysconfig/network-scripts/ifcfg-em2
cat > /etc/sysconfig/network-scripts/ifcfg-em2 << EOF
DEVICE="em2"
NM_CONTROLLED="yes"
ONBOOT="yes"
TYPE="Ethernet"
BRIDGE=br2
EOF

# 对于 kvm_host, 把 route-em2 修改成 route-br2, 否则网关会有问题.
/bin/mv -f /etc/sysconfig/network-scripts/route-em2 /etc/sysconfig/network-scripts/route-br2

service network restart ||systemctl restart network.service
service libvirtd restart ||systemctl restart libvirtd.service


# 定义存储池相关变量
storage_pool="vm_storage_pool"
storage_pool_dev="/dev/sda5"
storage_pool_vg="${storage_pool}_vg"

# 创建存储池
size=`/sbin/vgs |grep ${storage_pool_vg} |awk '{print $NF}'`
num=`echo $size |awk -F. '{print $1}'`
_type=`echo ${size:((${#size} - 1))}`
lvcreate -n vm_storage -L ${num}${_type} ${storage_pool_vg}
mkfs.ext4 /dev/${storage_pool_vg}/vm_storage
mkdir /vm_storage
chown qemu:qemu /vm_storage/
chmod 700 /vm_storage
mount -t ext4 /dev/${storage_pool_vg}/vm_storage /vm_storage
echo "/dev/${storage_pool_vg}/vm_storage /vm_storage ext4    defaults,data=ordered        1 2" >> /etc/fstab
virsh pool-define-as ${storage_pool} --type dir --target /vm_storage
virsh pool-info ${storage_pool}
virsh pool-start ${storage_pool}
virsh pool-autostart ${storage_pool}

