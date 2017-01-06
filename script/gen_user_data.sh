#!/bin/bash

sed -i '/gen_user_data.sh/d' /etc/rc.d/rc.local

hostname=$(hostname)

# 获取装机之后的自定义脚本并执行
cmd="import requests; print requests.get('http://wdstack.internal.DOMAIN.COM/api/v1/user_data/?hostname=$hostname').json()"
python -c "$cmd" >/root/user_data
chmod 777 /root/user_data
cd /root && /root/user_data &>>/root/user_data.log
