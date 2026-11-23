import socket
import os
from urllib.parse import urlparse
from typing import Optional, Tuple

import requests
import ipdb

from utils.tools import resource_path


class IPChecker:
    IPDB_URLS = [
        "hhttps://raw.githubusercontent.com/gqzh568/iptv1/refs/heads/master/utils/ip_checker/data/qqwry.ipdb",
        "https://cdn.jsdelivr.net/npm/qqwry.ipdb/qqwry.ipdbb",
    ]

    def __init__(self):
        self.db_path = resource_path("utils/ip_checker/data/qqwry.ipdb")
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)

        self.db: Optional[ipdb.City] = None
        # 尝试加载/下载ip库
        try:
            if not os.path.exists(self.db_path):
                self._download_ipdb()
            self.db = ipdb.City(self.db_path)
        except Exception as e:
            print(f"⚠️ IP库初始化失败，IP归属查询功能不可用: {e}")

        self.url_host = {}
        self.host_ip = {}
        self.host_ipv_type = {}

    def _download_ipdb(self):
        print(f"本地ip库不存在，开始自动下载 qqwry.ipdb -> {self.db_path}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        for url in self.IPDB_URLS:
            try:
                resp = requests.get(url, headers=headers, timeout=30, stream=True)
                resp.raise_for_status()
                with open(self.db_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 128):
                        f.write(chunk)
                # 简单校验：下载后尝试打开，打不开就删掉坏文件
                test_db = ipdb.City(self.db_path)
                del test_db
                print(f"✅ ipdb下载成功，来源：{url}")
                return
            except Exception as e:
                print(f"❌ 从 {url} 下载失败或文件损坏: {e}，尝试下一个源")
                # 清理损坏文件
                if os.path.exists(self.db_path):
                    os.remove(self.db_path)
        raise RuntimeError("所有ipdb下载源均失败，请检查网络！")

    def get_host(self, url: str) -> str:
        """Get the host from a URL"""
        if url in self.url_host:
            return self.url_host[url]

        host = urlparse(url).hostname or url
        self.url_host[url] = host
        return host

    def get_ip(self, url: str) -> Optional[str]:
        """Get the IP from a URL"""
        host = self.get_host(url)
        if host in self.host_ip:
            return self.host_ip[host]

        self.get_ipv_type(url)
        return self.host_ip.get(host)

    def get_ipv_type(self, url: str) -> str:
        """Get the IPv type of URL"""
        host = self.get_host(url)
        if host in self.host_ipv_type:
            return self.host_ipv_type[host]

        try:
            addr_info = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            ip = next((info[4][0] for info in addr_info if info[0] == socket.AF_INET6), None)
            if not ip:
                ip = next((info[4][0] for info in addr_info if info[0] == socket.AF_INET), None)
            ipv_type = "ipv6" if any(info[0] == socket.AF_INET6 for info in addr_info) else "ipv4"
        except Exception as e:
            print(f"Error on getting IPv type for {host}: {e}")
            ip = None
            ipv_type = "ipv4"

        self.host_ip[host] = ip
        self.host_ipv_type[host] = ipv_type
        return ipv_type

    def find_map(self, ip: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Find the IP address and return the location and ISP
        :param ip: The IP address to find
        :return: A tuple of (location, ISP)
        """
        if self.db is None:
            return None, None
        try:
            result = self.db.find_map(ip, "CN")
            if not result:
                return None, None

            location_parts = [
                result.get('country_name', ''),
                result.get('region_name', ''),
                result.get('city_name', '')
            ]
            location = "-".join(filter(None, location_parts))
            isp = result.get('isp_domain', None)

            return location, isp
        except Exception as e:
            print(f"Error on finding ip location and ISP: {e}")
            return None, None
