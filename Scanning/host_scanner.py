#!/usr/bin/env python3
"""
macOS용 ARP 기반 호스트 스캐너

이 스크립트는 현재 라우터 네트워크 내에서 ARP 요청을 브로드캐스트하고
응답을 수집하여 응답하는 모든 IPv4 호스트를 나열합니다.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import List, Optional

try:
    from scapy.all import ARP, Ether, conf, srp  # type: ignore
except Exception as exc:  # pragma: no cover - dependency notice
    # Scapy가 필요합니다. 설치되지 않았다면 사용자가 설치하라는 메시지를 출력하고 종료합니다.
    print(exc)
    sys.exit(
        "Scapy is required for this script. Install it with 'pip install scapy'.\n"
        f"Original import error: {exc}"
    )


@dataclass
class HostInfo:
    ip: str
    mac: str
    vendor: str


def run_command(cmd: List[str]) -> str:
    """시스템 명령을 실행하고 표준출력(stdout)을 스트립한 문자열을 반환합니다."""
    return subprocess.check_output(cmd, text=True).strip()


def resolve_cidr_from_iface(iface: str) -> ipaddress.IPv4Network:
    """
    macOS의 ipconfig를 사용해 인터페이스의 로컬 IPv4 네트워크(CIDR)를 결정합니다.

    macOS 설치에는 항상 ipconfig가 있으므로 이를 사용해 IP 주소와 서브넷 마스크를 얻습니다.
    """
    try:
        ip = run_command(["ipconfig", "getifaddr", iface])
        mask = run_command(["ipconfig", "getoption", iface, "subnet_mask"])
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Unable to read IP configuration for interface {iface}"
        ) from exc

    cidr = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
    return cidr


def pick_interface(user_iface: Optional[str]) -> str:
    """
    사용자가 지정한 인터페이스가 있으면 그것을 사용하고, 없으면 Scapy의 기본 라우트 인터페이스를 사용합니다.
    """
    if user_iface:
        return user_iface

    iface, _, _ = conf.route.route("0.0.0.0")
    if not iface:
        raise RuntimeError("Unable to determine default interface")
    return iface


def scan_hosts(network: ipaddress.IPv4Network, iface: str, timeout: float) -> List[HostInfo]:
    """
    주어진 네트워크에 ARP 브로드캐스트 요청을 보내고 응답을 수집합니다.

    반환된 응답에서 IP, MAC, 벤더 정보를 추출해 HostInfo 목록으로 반환합니다.
    """
    print("SCANNING HOSTS...")
    
    packet = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=str(network))
    answered, _ = srp(packet, timeout=timeout, iface=iface, inter=0.1, verbose=False)
    print(f"Received {len(answered)} responses")
    
    hosts: List[HostInfo] = []
    for _, reply in answered:
        mac = reply.hwsrc
        hosts.append(
            HostInfo(
                ip=reply.psrc,
                mac=mac,
                vendor=lookup_vendor(mac),
            )
        )
    hosts.sort(key=lambda host: ipaddress.IPv4Address(host.ip))
    return hosts


def lookup_vendor(mac: str) -> str:
    """
    MAC 주소의 OUI(벤더 접두사)를 로컬 macOS 데이터베이스로부터 확인하려는 자리입니다.

    macOS는 벤더 조회용 별도 CLI를 제공하지 않으므로, 의존성을 늘리지 않기 위해
    간단히 MAC의 앞 3바이트(접두사)를 반환합니다. 필요하면 이후에 외부 DB로 확장 가능합니다.
    """
    # 간단히 MAC 앞 3옥텟(예: 'AA:BB:CC')을 대문자로 반환합니다.
    prefix = mac.upper()[0:8]
    return prefix


def to_json(hosts: List[HostInfo]) -> str:
    """호스트 목록을 JSON 문자열로 직렬화합니다."""
    return json.dumps([asdict(host) for host in hosts], indent=2)


def render_table(hosts: List[HostInfo]) -> str:
    """
    CLI 출력용으로 호스트 데이터를 간단한 정렬된 표 형태 문자열로 렌더링합니다.
    """
    if not hosts:
        return "No hosts responded."

    ip_width = max(len(host.ip) for host in hosts)
    mac_width = max(len(host.mac) for host in hosts)
    vendor_width = max(len(host.vendor) for host in hosts)

    header = f"{'IP Address'.ljust(ip_width)}  {'MAC Address'.ljust(mac_width)}  {'Vendor'.ljust(vendor_width)}"
    separator = "-" * len(header)
    rows = [header, separator]
    for host in hosts:
        rows.append(
            f"{host.ip.ljust(ip_width)}  {host.mac.ljust(mac_width)}  {host.vendor.ljust(vendor_width)}"
        )
    return "\n".join(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="로컬 라우터 네트워크에서 현재 도달 가능한 모든 호스트를 나열합니다."
    )
    parser.add_argument(
        "--iface",
        help="Network interface to scan (defaults to the primary interface).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=1.5,
        help="각 ARP 프로브의 응답 타임아웃(초).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a table.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    iface = pick_interface(args.iface)
    print(f"Using interface: {iface}")
    network = resolve_cidr_from_iface(iface)
    print(f"Resolved network: {network}")
    
    hosts = scan_hosts(network, iface, args.timeout)
    if args.json:
        print(to_json(hosts))
    else:
        print(f"인터페이스 {iface}에서 네트워크 {network} 스캔 중")
        print(render_table(hosts))


if __name__ == "__main__":
    main()
