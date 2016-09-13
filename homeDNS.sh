#!/bin/bash

rm -f /etc/resolv.conf
echo "search localdomain" > /etc/resolv.conf
echo "nameserver 208.67.222.222" >> /etc/resolv.conf
echo "nameserver 208.67.220.220" >> /etc/resolv.conf
exit 0
