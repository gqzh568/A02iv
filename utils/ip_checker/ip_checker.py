import socket
import os
from urllib.parse import urlparse
from typing import Optional, Tuple

import requests
import ipdb

from utils.tools import resource_path


class IPChecker:
    # ========== 这里改成你仓库A的raw链接！！==========
    # 示例模板："https://raw.githubusercontent.com/xxx/repoA/main/utils/ip_checker/data/qqwry.ipdb"
    IPDB_RAW_URL = "https://raw.githubusercontent.com/Guovin/iptv-api/refs/heads/master/utils/ip_checker/data/qqwry.ipdb"

    def __init__(self):
        self.db_path = resource_path("utils/ip_checker/data/qqwry.ipdb")
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)

        self.db: Optional[ipdb.City] = None
        try:
            if not os.path.exists(self.db_path):
                self._download_ipdb_from_repoA()
            self.db = ipdb.City(self.db_path)
        except Exception as e:
            print(f"⚠️ IP库初始化失败（无法从A仓库拉取ipdb），IP归属查询不可用: {e}")

        self.url_host = {}
        self.host_ip = {}
        self.host_ipv_type = {}

    def _download_ipdb_from_repoA(self):
        """从仓库A的github raw链接下载ipdb，保存到B仓库本地对应路径"""
        print(f"本地 qqwry.ipdb 不存在，开始从仓库A下载 -> {self.db_path}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        try:
            resp = requests.get(
                self.IPDB_RAW_URL,
                headers=headers,
                timeout=60,
                stream=True
            )
            resp.raise_for_status()

            with open(self.db_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=128 * 1024):
                    f.write(chunk)

            # 校验：下载完尝试打开，确认文件没有损坏
            test_db = ipdb.City(self.db_path)
            del test_db
            print("✅ 成功从仓库A下载 qqwry.ipdb")
        except Exception as e:
            print(f"❌ 从仓库A下载ipdb失败或文件损坏: {e}")
            # 清理残缺/损坏文件
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            raise

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
