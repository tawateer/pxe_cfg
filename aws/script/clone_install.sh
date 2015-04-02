#!/bin/bash


region=


hostname=
hostname $hostname
sed -i "s/^HOSTNAME=.*/HOSTNAME=$hostname/g" /etc/sysconfig/network


sed -i "#/home/#d" /etc/fstab
/sbin/blkid |egrep -v "vda" |sort -u -k1 |awk '{print $2" /home/ ext4    nosuid,noatime   1 2"}' >>/etc/fstab

/bin/rm -rf /var/lib/puppet/


dns_vip=
sed -i "/nameserver/s/.*/nameserver ${dns_vip}/g" /etc/resolv.conf


yum -y install bind
ns_servers=

private_key_path="Kamazonaws.com.cn.+157+30769.private"
cat >${private_key_path} <<EOF
Private-key-format: v1.3
Algorithm: 157 (HMAC_MD5)
Key: faFypFIday6z+LXB1+jQlMdH5kNPQuYHYo1HkNHjaFhT678x82R12OgyRB6sUta1xTXmEjdbHm0YiTTs1DKfLQ==
Bits: AAA=
Created: 20140827035505
Publish: 20140827035505
Activate: 20140827035505
EOF
chmod 400 ${private_key_path}
public_key_path="Kamazonaws.com.cn.+157+30769.key"
echo "amazonaws.com.cn. IN KEY 0 3 157 faFypFIday6z+LXB1+jQlMdH5kNPQuYHYo1HkNHjaFhT678x82R12Ogy RB6sUta1xTXmEjdbHm0YiTTs1DKfLQ==" >${public_key_path}

local_domain=$(curl -w "\n" http://169.254.169.254/latest/meta-data/local-hostname |sed "s/^[^.]\+.//g")
local_ipv4=$(curl http://169.254.169.254/latest/meta-data/local-ipv4)
local_ipv4_reverse=$(echo ${local_ipv4} |awk -F"." '{print $4"."$3"."$2"."$1}')


for ns_server in ${ns_servers}
do
	cat <<EOF | /usr/bin/nsupdate -k ${private_key_path} -v
server ${ns_server}
zone ${local_domain}
update delete ${hostname}.${local_domain} A
update add ${hostname}.${local_domain} 60 A ${local_ipv4}
show
send
EOF

	cat <<EOF | /usr/bin/nsupdate -k ${private_key_path} -v
server ${ns_server}
zone in-addr.arpa
update delete ${local_ipv4_reverse}.in-addr.arpa PTR
update add ${local_ipv4_reverse}.in-addr.arpa 60 PTR ${hostname}.${local_domain}
show
send
EOF
done


/bin/rm -rf ${private_key_path}
/bin/rm -rf ${public_key_path}
if ! echo $hostname |grep dns 
then
	/bin/rpm -e bind
fi


region="ap-southeast-1"
/bin/rm -f /etc/yum.repos.d/*
rpm --force -Uvh http://${region}.repo.nosa.com/nosa/6/x86_64/nosa-release-0.0.18-1.el6.x86_64.rpm
yum -y install puppet
/usr/bin/puppet agent --onetime --no-daemonize --server=${region}.puppetlb.nosa.com --ca_server=${region}.puppetca.nosa.com


reboot
