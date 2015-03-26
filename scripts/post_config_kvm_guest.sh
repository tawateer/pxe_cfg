#!/bin/bash
# 虚拟机安装第一次重启之后执行的脚本,主要是修改网卡,配置数据盘等操作,执行完之后会再次重启.


ext_device="em1"
intra_device="em2"


# 更改外网卡名称
/bin/sed -i "s/eth1/${ext_device}/g" /etc/udev/rules.d/70-persistent-net.rules
/bin/sed -i "s/eth0/${intra_device}/g" /etc/udev/rules.d/70-persistent-net.rules


# Define data partition
vm_data_dev="vdb"
vm_data_vg="datavg"
vm_data_lv="home"
vm_data_dir="/home"


vm_data_dev_path="/dev/${vm_data_dev}"


if /bin/df |grep /home >/dev/null
then
    echo "Partition /home exist."
    exit 1
fi

if [ ! -b ${vm_data_dev_path} ]
then
    echo "Device ${vm_data_dev_path} doesn't exist."
    exit 1
fi


pvcreate ${vm_data_dev_path} ||exit 1
vgcreate ${vm_data_vg} ${vm_data_dev_path} ||exit 1
lvcreate -n ${vm_data_lv} -l 100%FREE ${vm_data_vg} || exit 1
mkfs.ext4 /dev/${vm_data_vg}/${vm_data_lv} || exit 1


/bin/cp -a ${vm_data_dir} /tmp/.${vm_data_dir}_bak
rm -rf ${vm_data_dir}
mkdir ${vm_data_dir}


echo "/dev/${vm_data_vg}/${vm_data_lv}                ${vm_data_dir}                  ext4    defaults,data=ordered,nodev,nosuid        1 2" >> /etc/fstab
mount -a || exit 1


/bin/cp -ra /tmp/.${vm_data_dir}_bak/* ${vm_data_dir}


# 增加clocksource, 修复 unstable clocksource in virtualised CentOS
sed -i "/vmlinuz-2.6.32-279.el6.x86_64/s/$/ clocksource_failover=acpi_pm/g" /boot/grub/grub.conf


# 重启之后增加DNS, 执行Puppet 
echo "cd /tmp/install &&python wddns -a &&sed -i '/wddns/d' /etc/rc.d/rc.local 

yum -y install puppet ;chkconfig puppet on ;puppet agent -t --server puppetlb.corp.nosa.com --ca_server puppetca.corp.nosa.com ;sed -i '/puppet/d' /etc/rc.d/rc.local ;/bin/rm -rf /tmp/install/* " >> /etc/rc.d/rc.local


# 装机之后执行自定义脚本
echo '''#!/bin/bash
sed -i '/post_custom.sh/d' /etc/rc.d/rc.local

sn=$(dmidecode -s system-serial-number)
if echo $sn |grep -i Specified
then
   if test -f /etc/sn
   then
       sn=$(cat /etc/sn)
   else
       echo "v-"$(/usr/bin/uuidgen) >/etc/sn
       sn=$(cat /etc/sn)
   fi
fi

# 获取装机之后的自定义脚本并执行
curl http://wdstack.hy01.nosa.com/api/v1/postcustom/?sn=$sn >/root/post_custom
chown 777 /root/post_custom
/root/post_custom &>>/root/post_custom.log
''' >/root/gen_post_custom.sh

echo "sh /root/gen_post_custom.sh &>>/root/gen_post_custom.log ;sed -i '/gen_post_custom.sh/d' /etc/rc.d/rc.local" >>/etc/rc.d/rc.local


# 操作完成之后重启使网卡生效
reboot
