#!/usr/bin/env python3
"""
macOS용 커스텀 패킷 스니퍼 & 실시간 분석기 (Custom Packet Sniffer & Analyzer)

이 스크립트는 지정한 네트워크 인터페이스의 패킷을 실시간으로 캡처하고,
프로토콜별로 색상을 다르게 적용하여 상세 파싱 정보를 터미널에 시각적으로 출력합니다.
보안 교육용으로 제작되어 평문으로 전송되는 민감 정보(비밀번호 등) 감지 시 경고를 띄웁니다.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from typing import Any, Dict, List, Optional

# ANSI Escape Colors for Rich UI/Console Aesthetics
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[90m"
C_RED = "\033[91m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_MAGENTA = "\033[95m"
C_CYAN = "\033[96m"
C_BG_RED = "\033[41m"
C_BG_YELLOW = "\033[43m"

try:
    from scapy.all import (
        ARP,
        DNS,
        DNSQR,
        DNSRR,
        Ether,
        IP,
        IPv6,
        Raw,
        TCP,
        UDP,
        conf,
        get_working_ifaces,
        sniff,
    )
except ImportError as exc:
    sys.exit(
        f"{C_RED}{C_BOLD}Error:{C_RESET} Scapy is required. Install it using:\n"
        f"  {C_CYAN}pip install scapy{C_RESET}\n"
        f"Original error: {exc}"
    )

# 글로벌 통계 데이터를 기록할 딕셔너리
stats: Dict[str, Any] = {
    "start_time": 0.0,
    "total_packets": 0,
    "total_bytes": 0,
    "protocols": Counter(),
    "security_alerts": 0,
    "sensitive_leaks": [],
}

# 탐지할 평문 민감 정보 키워드
SENSITIVE_KEYWORDS = [
    "user", "username", "pass", "password", "login", 
    "secret", "token", "api_key", "apikey", "auth"
]


def display_banner() -> None:
    """멋진 화이트해커 스타일의 아스키 배너를 출력합니다."""
    banner = f"""
{C_CYAN}{C_BOLD}┌──────────────────────────────────────────────────────────────┐
│                                                              │
│   {C_RED}{C_BOLD}⚡ ANTIGRAVITY SECURE PACKET SNIFFER & ANALYZER ⚡{C_RESET}{C_CYAN}{C_BOLD}   │
│   {C_DIM}Education & Vulnerability Research Lab (macOS Mode){C_RESET}{C_CYAN}{C_BOLD}       │
│                                                              │
└──────────────────────────────────────────────────────────────┘{C_RESET}
    """
    print(banner)


def list_and_select_interface() -> str:
    """사용 가능한 모든 네트워크 인터페이스를 나열하고 사용자로부터 하나를 입력받습니다."""
    interfaces = get_working_ifaces()
    
    print(f"{C_BOLD}[*] 사용 가능한 네트워크 인터페이스 목록:{C_RESET}")
    print(f"{C_DIM}{'-' * 70}{C_RESET}")
    
    valid_ifaces: Dict[int, Any] = {}
    for idx, iface in enumerate(interfaces, 1):
        ip_info = iface.ip if iface.ip else "No IP Assigned"
        mac_info = iface.mac if iface.mac else "No MAC"
        print(f"  [{C_GREEN}{idx}{C_RESET}] {C_BOLD}{iface.name.ljust(10)}{C_RESET} | IP: {ip_info.ljust(15)} | MAC: {mac_info}")
        valid_ifaces[idx] = iface.name
        
    print(f"{C_DIM}{'-' * 70}{C_RESET}")
    
    # 기본 인터페이스 가져오기
    default_iface = None
    try:
        default_iface, _, _ = conf.route.route("0.0.0.0")
    except Exception:
        pass
    
    default_prompt = f" (기본: {default_iface})" if default_iface else ""
    
    while True:
        try:
            choice = input(f"{C_BOLD}[?] 스니핑할 인터페이스 번호 선택{default_prompt}: {C_RESET}").strip()
            if not choice and default_iface:
                return default_iface
            
            idx_choice = int(choice)
            if idx_choice in valid_ifaces:
                return valid_ifaces[idx_choice]
            else:
                print(f"{C_RED}[!] 올바른 번호를 선택해 주세요.{C_RESET}")
        except ValueError:
            # 번호가 아닌 이름을 직접 입력했을 경우 확인
            if choice in [iface.name for iface in interfaces]:
                return choice
            print(f"{C_RED}[!] 올바른 번호 또는 인터페이스 이름을 입력해 주세요.{C_RESET}")


def select_protocol_filter() -> Optional[str]:
    """캡처할 프로토콜 필터를 인터랙티브하게 선택받습니다."""
    print(f"\n{C_BOLD}[*] 캡처할 프로토콜 필터 선택:{C_RESET}")
    print(f"  [{C_GREEN}1{C_RESET}] {C_BOLD}ALL{C_RESET}  - 모든 패킷 수집 (기본값)")
    print(f"  [{C_GREEN}2{C_RESET}] {C_BOLD}TCP{C_RESET}  - 웹 트래픽, SSH, 데이터 송수신 등")
    print(f"  [{C_GREEN}3{C_RESET}] {C_BOLD}UDP{C_RESET}  - DNS, 스트리밍 등 비연결형 프로토콜")
    print(f"  [{C_GREEN}4{C_RESET}] {C_BOLD}ICMP{C_RESET} - Ping, 네트워크 진단")
    print(f"  [{C_GREEN}5{C_RESET}] {C_BOLD}DNS{C_RESET}  - 도메인 네임 질의")
    print(f"  [{C_GREEN}6{C_RESET}] {C_BOLD}HTTP{C_RESET} - 평문 웹 사이트 요청/응답")
    
    while True:
        choice = input(f"{C_BOLD}[?] 필터 번호 선택 (기본: 1): {C_RESET}").strip()
        if not choice or choice == "1":
            return None  # Scapy 필터 없음
        elif choice == "2":
            return "tcp"
        elif choice == "3":
            return "udp"
        elif choice == "4":
            return "icmp"
        elif choice == "5":
            return "udp port 53"
        elif choice == "6":
            return "tcp port 80 or tcp port 8080"
        else:
            print(f"{C_RED}[!] 1에서 6 사이의 번호를 입력해 주세요.{C_RESET}")


def analyze_payload_for_credentials(payload_str: str, src_ip: str, dst_ip: str, proto: str) -> None:
    """평문 페이로드에서 비밀번호나 인증 토큰 등 민감한 키워드가 있는지 스캔합니다."""
    payload_lower = payload_str.lower()
    found_keywords = []
    
    # 키워드 매칭 검증
    for keyword in SENSITIVE_KEYWORDS:
        if keyword in payload_lower:
            # 단순 매칭 시 정규표현식이나 추가 검증을 할 수 있으나 교육용으로 간단히 검출
            found_keywords.append(keyword)
            
    if found_keywords:
        stats["security_alerts"] += 1
        alert_info = {
            "time": time.strftime("%H:%M:%S"),
            "src": src_ip,
            "dst": dst_ip,
            "proto": proto,
            "keywords": found_keywords,
            "snippet": payload_str[:150].replace("\n", " ").strip()
        }
        stats["sensitive_leaks"].append(alert_info)
        
        # 경고 박스 출력
        print(f"\n{C_BG_RED}{C_BOLD}[⚠️ SECURE WARNING] 평문 중요 정보 전송 감지!{C_RESET}")
        print(f"{C_RED}  ├─ 발생 시간  : {alert_info['time']}")
        print(f"  ├─ 경로       : {C_BOLD}{src_ip} -> {dst_ip}{C_RESET}{C_RED} ({proto})")
        print(f"  ├─ 감지 키워드: {C_YELLOW}{', '.join(found_keywords)}{C_RESET}{C_RED}")
        print(f"  └─ 페이로드   : {C_DIM}{alert_info['snippet']}{C_RESET}\n")


def parse_packet(packet: Any) -> None:
    """수집된 단일 패킷을 정밀하게 파싱하고 화면에 컬러풀하게 출력합니다."""
    stats["total_packets"] += 1
    stats["total_bytes"] += len(packet)
    
    # 시간 표시
    timestamp = time.strftime("%H:%M:%S")
    packet_len = len(packet)
    
    # 1단계: Ethernet 계층 분석
    eth_src = packet.src if hasattr(packet, "src") else "Unknown"
    eth_dst = packet.dst if hasattr(packet, "dst") else "Unknown"
    
    # 프로토콜 파싱 및 포맷 초기화
    proto_label = "ETHER"
    color = C_DIM
    summary = f"Ethernet II Frame ({eth_src} -> {eth_dst})"
    
    # 2단계: Network 계층 분석 (ARP/IP)
    if packet.haslayer(ARP):
        stats["protocols"]["ARP"] += 1
        proto_label = "ARP"
        color = C_DIM
        arp_layer = packet[ARP]
        if arp_layer.op == 1:
            summary = f"Who has {C_BOLD}{arp_layer.pdst}{C_RESET}{C_DIM}? Tell {arp_layer.psrc}"
        elif arp_layer.op == 2:
            summary = f"{C_BOLD}{arp_layer.psrc}{C_RESET}{C_DIM} is at {arp_layer.hwsrc}"
            
    elif packet.haslayer(IP) or packet.haslayer(IPv6):
        is_ipv6 = packet.haslayer(IPv6)
        ip_layer = packet[IPv6] if is_ipv6 else packet[IP]
        src_ip = ip_layer.src
        dst_ip = ip_layer.dst
        
        # 3단계: Transport 계층 분석 (TCP/UDP/ICMP)
        if packet.haslayer(TCP):
            stats["protocols"]["TCP"] += 1
            proto_label = "TCP"
            color = C_GREEN
            tcp_layer = packet[TCP]
            sport = tcp_layer.sport
            dport = tcp_layer.dport
            
            # TCP 플래그 구체화
            flags = []
            if tcp_layer.flags & 0x02: flags.append("SYN")
            if tcp_layer.flags & 0x10: flags.append("ACK")
            if tcp_layer.flags & 0x01: flags.append("FIN")
            if caz := tcp_layer.flags & 0x04: flags.append("RST")
            if tcp_layer.flags & 0x08: flags.append("PSH")
            flag_str = f"[{'|'.join(flags)}]" if flags else ""
            
            summary = f"{src_ip}:{sport} -> {dst_ip}:{dport} {C_YELLOW}{flag_str}{C_RESET}{C_GREEN} Seq={tcp_layer.seq} Win={tcp_layer.window}"
            
            # HTTP (Port 80, 8080 등 평문 웹트래픽) 분석
            if sport == 80 or dport == 80 or sport == 8080 or dport == 8080:
                proto_label = "HTTP"
                color = C_CYAN
                if packet.haslayer(Raw):
                    payload = packet[Raw].load
                    try:
                        http_data = payload.decode("utf-8", errors="ignore")
                        # HTTP 요청/응답 헤더의 첫 줄 추출
                        first_line = http_data.split("\r\n")[0]
                        summary = f"HTTP Traffic | {src_ip}:{sport} -> {dst_ip}:{dport} | {C_BOLD}{first_line}{C_RESET}"
                        
                        # 민감정보 유출 체크
                        analyze_payload_for_credentials(http_data, src_ip, dst_ip, "HTTP")
                    except Exception:
                        summary = f"HTTP Binary/Encrypted Data ({packet_len} bytes)"
            else:
                # 일반 TCP Payload 내 평문 보안 진단
                if packet.haslayer(Raw):
                    payload = packet[Raw].load
                    try:
                        raw_data = payload.decode("utf-8", errors="ignore")
                        analyze_payload_for_credentials(raw_data, src_ip, dst_ip, "TCP")
                    except Exception:
                        pass

        elif packet.haslayer(UDP):
            stats["protocols"]["UDP"] += 1
            proto_label = "UDP"
            color = C_BLUE
            udp_layer = packet[UDP]
            sport = udp_layer.sport
            dport = udp_layer.dport
            
            summary = f"{src_ip}:{sport} -> {dst_ip}:{dport} (Len={udp_layer.len})"
            
            # DNS (Port 53) 분석
            if packet.haslayer(DNS):
                stats["protocols"]["DNS"] += 1
                proto_label = "DNS"
                color = C_MAGENTA
                dns_layer = packet[DNS]
                dns_info = ""
                
                # DNS Query
                if dns_layer.qr == 0 and packet.haslayer(DNSQR):
                    qname = packet[DNSQR].qname.decode("utf-8", errors="ignore")
                    dns_info = f"Query: {C_BOLD}{qname}{C_RESET}{C_MAGENTA}"
                # DNS Answer
                elif dns_layer.qr == 1 and packet.haslayer(DNSRR):
                    rrname = packet[DNSRR].rrname.decode("utf-8", errors="ignore")
                    rdata = packet[DNSRR].rdata
                    rdata_str = rdata.decode("utf-8", errors="ignore") if isinstance(rdata, bytes) else str(rdata)
                    dns_info = f"Response: {rrname} is at {C_BOLD}{rdata_str}{C_RESET}{C_MAGENTA}"
                
                summary = f"DNS Port 53 | {src_ip}:{sport} -> {dst_ip}:{dport} | {dns_info}"
            else:
                # 일반 UDP Payload 내 평문 보안 진단
                if packet.haslayer(Raw):
                    payload = packet[Raw].load
                    try:
                        raw_data = payload.decode("utf-8", errors="ignore")
                        analyze_payload_for_credentials(raw_data, src_ip, dst_ip, "UDP")
                    except Exception:
                        pass
                
        elif packet.haslayer(Raw) and not packet.haslayer(TCP) and not packet.haslayer(UDP):
            # 기타 Raw IP 패킷
            pass
            
        else:
            # ICMP 등 기타 IP 트래픽
            proto_label = "IP/Other"
            color = C_YELLOW
            # ICMP 체크
            if not is_ipv6 and ip_layer.proto == 1:
                stats["protocols"]["ICMP"] += 1
                proto_label = "ICMP"
                summary = f"ICMP Packet: {src_ip} -> {dst_ip} Type={ip_layer.frag}"
            else:
                summary = f"IP Protocol {ip_layer.proto} ({src_ip} -> {dst_ip})"
                
    # 최종 로그 터미널 출력
    log_line = f"[{C_DIM}{timestamp}{C_RESET}] {color}{C_BOLD}[{proto_label.center(8)}]{C_RESET} {color}{summary}{C_RESET} {C_DIM}({packet_len}B){C_RESET}"
    print(log_line)


def print_summary_dashboard() -> None:
    """Ctrl+C 종료 시 캡처된 패킷 통계를 예쁘게 포맷팅하여 보고서 형태로 출력합니다."""
    end_time = time.time()
    duration = max(end_time - stats["start_time"], 0.1)
    pps = stats["total_packets"] / duration
    bytes_kb = stats["total_bytes"] / 1024
    
    dashboard = f"""
\n
{C_CYAN}{C_BOLD}┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│             📊 ANTIGRAVITY PACKET CAPTURE SESSION SUMMARY 📊                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘{C_RESET}

  {C_BOLD}■ 일반 통계 (General Statistics){C_RESET}
    ├─ 모니터링 시간  : {C_GREEN}{duration:.2f} 초{C_RESET}
    ├─ 수집된 총 패킷 : {C_GREEN}{stats['total_packets']:,} 개{C_RESET} (평균 {pps:.2f} Pkts/Sec)
    └─ 수집된 총 데이터 : {C_GREEN}{bytes_kb:.2f} KB{C_RESET} ({stats['total_bytes']:,} Bytes)

  {C_BOLD}■ 프로토콜 분포 (Protocol Distribution){C_RESET}"""
    
    print(dashboard)
    
    # 프로토콜별 통계 막대그래프 시각화
    total_proto_count = sum(stats["protocols"].values())
    if total_proto_count > 0:
        for proto, count in stats["protocols"].most_common():
            percentage = (count / stats["total_packets"]) * 100
            bar_len = int(percentage / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            print(f"    ├─ {proto.ljust(8)} : {C_BLUE}{count:5,} 개{C_RESET} ({percentage:5.1f}%)  [{C_CYAN}{bar}{C_RESET}]")
    else:
        print(f"    {C_DIM}※ 프로토콜 통계 없음 (비IP 계층 트래픽만 수집되었을 수 있습니다.){C_RESET}")
        
    print(f"\n  {C_BOLD}■ 화이트해커 보안 분석 리포트 (Security Alert Report){C_RESET}")
    print(f"    ├─ 평문 중요 정보 경고 횟수: {C_RED if stats['security_alerts'] > 0 else C_GREEN}{C_BOLD}{stats['security_alerts']} 회{C_RESET}")
    
    if stats["sensitive_leaks"]:
        print(f"    └─ {C_RED}{C_BOLD}감지된 취약점 리스트 (Plaintext Credentials Leaks):{C_RESET}")
        print(f"       {C_DIM}{'=' * 72}{C_RESET}")
        for idx, alert in enumerate(stats["sensitive_leaks"], 1):
            keywords_str = ", ".join(alert["keywords"])
            print(f"       [{C_RED}{idx}{C_RESET}] [{alert['time']}] {C_BOLD}{alert['src']} -> {alert['dst']}{C_RESET} ({alert['proto']})")
            print(f"           ↳ 감지 키워드: {C_YELLOW}{keywords_str}{C_RESET}")
            print(f"           ↳ 평문 유출 데이터: {C_DIM}{alert['snippet']}{C_RESET}")
            print(f"       {C_DIM}{'-' * 72}{C_RESET}")
            if idx >= 5:
                print(f"       {C_DIM}... 외 {len(stats['sensitive_leaks']) - 5}건 추가 감지됨 ...{C_RESET}")
                break
    else:
        print(f"    └─ {C_GREEN}안전성 평가: 모니터링 동안 평문 자격증명 노출이 감지되지 않았습니다. {C_RESET}👍")
        
    print(f"""
{C_CYAN}{C_BOLD}┌──────────────────────────────────────────────────────────────────────────────┐
│  {C_YELLOW}💡 화이트해커의 권장 사항 (White-hat Hacker Recommendations):{C_RESET}{C_CYAN}{C_BOLD}             │
│  {C_RESET}1. 암호화되지 않은 프로토콜(HTTP, FTP, Telnet 등)은 패킷 스니핑에 취약합니다.   │
│  2. 모든 중요 자격증명 전송 및 웹 통신에는 {C_GREEN}HTTPS (TLS/SSL){C_RESET}를 강제 적용하십시오.      │
│  3. 패킷 데이터 암호화(WPA3, VPN) 및 내부 서브넷 세분화로 도청 위험을 차단하십시오. │
└──────────────────────────────────────────────────────────────────────────────┘{C_RESET}
\n""")


def main() -> None:
    display_banner()
    
    # 1. 인터페이스 선택
    iface = list_and_select_interface()
    
    # 2. 필터 선택
    bpf_filter = select_protocol_filter()
    
    # BPF 필터 디버깅 레이블
    filter_label = bpf_filter if bpf_filter else "ALL"
    print(f"\n{C_BOLD}{C_GREEN}[*] 패킷 캡처를 시작합니다...{C_RESET}")
    print(f"  ├─ 인터페이스 : {C_BOLD}{C_GREEN}{iface}{C_RESET}")
    print(f"  ├─ 필터       : {C_BOLD}{C_GREEN}{filter_label}{C_RESET}")
    print(f"  └─ 중단하려면 {C_RED}{C_BOLD}Ctrl+C{C_RESET}를 누르세요.\n")
    print(f"{C_DIM}{'=' * 90}{C_RESET}")
    
    # 시작 시간 설정
    stats["start_time"] = time.time()
    
    # 3. 스니핑 동작 루프 시작 (에러 처리 및 Ctrl+C 트랩)
    try:
        sniff(
            iface=iface,
            filter=bpf_filter,
            prn=parse_packet,
            store=False  # 메모리 과부하 방지 위해 패킷 객체 누적 저장 비활성화
        )
    except (PermissionError, OSError) as e:
        # macOS의 BPF 디바이스 또는 로 소켓 권한 오류를 포착합니다.
        err_msg = str(e).lower()
        if "permission" in err_msg or "bpf" in err_msg or "root" in err_msg or "operation not permitted" in err_msg:
            print(f"\n{C_BG_RED}{C_BOLD}[ERROR] 권한 오류 (Permission Denied){C_RESET}")
            print(f"{C_RED}패킷 스니핑은 로(Raw) 소켓 및 네트워크 인터페이스 디바이스 접근이 필요하므로")
            print(f"반드시 {C_BOLD}루트(sudo) 권한{C_RESET}{C_RED}이 있어야 실행할 수 있습니다.{C_RESET}")
            print(f"\n{C_BOLD}실행 방법:{C_RESET}")
            print(f"  {C_CYAN}sudo .venv/bin/python3 Scanning/packet_sniffer.py{C_RESET}\n")
            sys.exit(1)
        else:
            print(f"\n{C_BG_RED}{C_BOLD}[ERROR] 운영체제 오류 발생{C_RESET}")
            print(f"{C_RED}{e}{C_RESET}")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n{C_YELLOW}[*] 사용자 요청에 의해 패킷 수집이 중단되었습니다.{C_RESET}")
        print_summary_dashboard()
    except Exception as e:
        print(f"\n{C_BG_RED}{C_BOLD}[ERROR] 스니핑 중 예상치 못한 오류 발생{C_RESET}")
        print(f"{C_RED}{e}{C_RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
