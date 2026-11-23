import socket
import os
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Tuple

import requests
import ipdb

from utils.tools import resource_path

# False = 开发模式：下载到当前目录下的 data/qqwry.ipdb（B仓库内）
# True  = 打包模式：使用 resource_path
IS_BUNDLED = False


class IPChecker:
    IPDB_RAW_URL = "https://raw.githubusercontent.com/你的用户名/A仓库名/main/utils/ip_checker/data/qqwry.ipdb"

    def __init__(self):
        if IS_BUNDLED:
            self.db_path = resource_path("utils/ip_checker/data/qqwry.ipdb")
        else:
            # 当前 ip_checker.py 所在目录
            this_file = Path(__file__).resolve()
            checker_dir = this_file.parent  # utils/ip_checker
            self.db_path = checker_dir / "data" / "qqwry.ipdb"

        db_dir = self.db_path.parent
        db_dir.mkdir(parents=True, exist_ok=True)

        self.db: Optional[ipdb.City] = None
        try:
            if not self.db_path.exists():
                self._download_ipdb_from_private_repoA()
            self.db = ipdb.City(str(self.db_path))
            print(f"📁 ipdb加载路径：{self.db_path}")
        except Exception as e:
            print(f"⚠️ IP库初始化失败（无法从私有A仓库拉取ipdb），IP归属查询不可用: {e}")

        self.url_host = {}
        self.host_ip = {}
        self.host_ipv_type = {}

    def _download_ipdb_from_private_repoA(self):
        gh_token = os.getenv("GH_TOKEN")
        if not gh_token:
            raise RuntimeError("未设置环境变量 GH_TOKEN，私有仓库无法下载文件！")

        print(f"本地 qqwry.ipdb 不存在，开始从私有仓库A下载 -> {self.db_path}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Authorization": f"token {gh_token}"
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

            test_db = ipdb.City(str(self.db_path))
            del test_db
            print("✅ 成功从私有仓库A下载 qqwry.ipdb，保存到B仓库 utils/ip_checker/data/")
        except Exception as e:
            print(f"❌ 从私有A仓库下载ipdb失败或文件损坏: {e}")
            if self.db_path.exists():
                self.db_path.unlink()
            raise

    def get_host(self, url: str) -> str:
        if url in self.url_host:
            return self.url_host[url]
        host = urlparse(url).hostname or url
        self.url_host[url] = host
        return host

    def get_ip(self, url: str) -> Optional[str]:
        host = self.get_host(url)
        if host in self.host_ip:
            return self.host_ip[host]
        self.get_ipv_type(url)
        return self.host_ip.get(host)

    def get_ipv_type(self, url: str) -> str:
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
