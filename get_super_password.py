#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天邑 TEWA-1100G / 博通版光猫 超级管理员密码一键获取脚本
仅限自己的设备使用。

用法:
    python get_super_password.py --mac 你的光猫MAC --password 光猫背面密码
    python get_super_password.py -m 你的光猫MAC -p 光猫背面密码 -i 192.168.1.1

流程:
    登录8080后台 -> 抓 set3_sessionKey -> 开Telnet -> Telnet登录
    -> su提权(SU密码由MAC算出) -> telecomadmin get 读超密 -> 关Telnet
全程可逆，不修改宽带/WiFi/拨号配置。

⚠️ 仅适用于博通版（板卡 TY968xxx）。
   海思版（Hi5682 等）SU 算法不同，本脚本不适用，请先确认机型。
"""
import argparse
import base64
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    import http.cookiejar as cookiejar
except ImportError:
    import cookielib as cookiejar


# ---------------------------------------------------------------- SU 密码算法
def generate_su_passwords(mac):
    ct1 = 'QbNUTaMecPWVSKdCgXIJRrsfYXwyqpvnDHWzQuPmAGtAxRTphBcwBnNkjbFmvVMqaFkEutSrDCxsCKjBzEyDEUJTZfHZghMHYFdeASGNaUgFtdbYRkshJHkFNXMcKdfw'
    ct2 = 'NXMcKdfwRkshJHkFaUgFtdbYYFdeASGNZfHZghMHzEyDEUJTDCxsCKjBaFkEutSrjbFmvVMqhBcwBnNkAGtAxRTpDHWzQuPmYXwyqpvngXIJRrsfcPWVSKdCQbNUTaMe'
    ct3 = 'eMaTUNbQCdKSVWPcfsrRJIXgnvpqywXYmPuQzWHDpTRxAtGAkNnBwcBhqMVvmFbjrStuEkFaBjKCsxCDTJUEDyEzHMhgZHfZNGSAedFYYbdtFgUaFkHJhskRwfdKcMXN'

    hex_clean = ''.join(c for c in mac.upper() if c in '0123456789ABCDEF')
    if len(hex_clean) < 12:
        return ['MAC地址格式错误']

    v19 = [ord(c) for c in hex_clean[-8:]][::-1]
    v10 = 5
    for j in range(len(v19)):
        c = v19[j]
        if 49 <= c <= 57:
            v10 = (c - 48) | j
            break

    a1, a2, a3 = [], [], []
    for k in range(len(v19)):
        v15 = (v19[k] & v19[7 - k]) if k < 4 else (v19[k] | v19[k - 4])
        v16 = v15 + v10
        if v16 > 127:
            v16 = k
            v10 = k
        a1.append(ct1[v16])
        a2.append(ct2[v16])
        a3.append(ct3[v16])
        v10 += max(k, 1)
    return [''.join(a1), ''.join(a2), ''.join(a3)]


# ---------------------------------------------------------------- HTTP 会话
def make_opener():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    cj = cookiejar.CookieJar()
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPSHandler(context=ctx),
    )


class TelnetShell:
    def __init__(self, host, port=23):
        self.s = socket.create_connection((host, port), timeout=5)

    def _read(self, timeout=2.0):
        self.s.settimeout(timeout)
        data = b""
        try:
            while True:
                chunk = self.s.recv(4096)
                if not chunk:
                    break
                data += chunk
                time.sleep(0.1)
        except socket.timeout:
            pass
        return data

    def send(self, line, wait=1.0, timeout=2.5):
        self.s.sendall((line + "\r\n").encode())
        time.sleep(wait)
        return self._read(timeout)

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="天邑TEWA-1100G博通版超密获取")
    ap.add_argument("-i", "--ip", default="192.168.1.1", help="光猫地址")
    ap.add_argument("-m", "--mac", required=True, help="光猫MAC，任意格式")
    ap.add_argument("-u", "--user", default="useradmin", help="普通用户名")
    ap.add_argument("-p", "--password", required=True, help="光猫背面普通密码")
    ap.add_argument("--port", default="8080", help="维护后台端口")
    args = ap.parse_args()

    base = "http://%s:%s" % (args.ip, args.port)
    op = make_opener()

    def get(path, post=None):
        h = {"User-Agent": "Mozilla/5.0"}
        if post:
            req = urllib.request.Request(
                base + path,
                data=urllib.parse.urlencode(post).encode(),
                headers={**h, "Content-Type": "application/x-www-form-urlencoded"},
            )
        else:
            req = urllib.request.Request(base + path, headers=h)
        try:
            return op.open(req, timeout=10).read()
        except urllib.error.HTTPError as e:
            return e.read()
        except Exception as e:
            return ("__ERR__" + repr(e)).encode()

    print("[*] 登录 %s (用户 %s)" % (base, args.user))
    raw = get("/login.html").decode("latin1")
    i = raw.find('name="sessionKey"')
    if i < 0:
        print("[!] 未找到登录页 sessionKey，检查 IP/端口")
        return 1
    m = re.search(r"'(\d+)'", raw[i:i + 120])
    if not m:
        print("[!] 登录页 sessionKey 解析失败")
        return 1
    sk_login = m.group(1)

    pwd_b64 = base64.b64encode(args.password.encode()).decode()
    raw = get("/login.cgi", post={
        "username": args.user, "password": pwd_b64, "sessionKey": sk_login,
    }).decode("latin1")
    if args.user not in raw:
        print("[!] 登录失败，检查账号密码（输错3次会锁1分钟）")
        return 1
    print("[+] 登录成功")

    print("[*] 抓 set3_sessionKey")
    raw = get("/MD_Device_user.html").decode("latin1")
    # 宽松匹配：set3_sessionKey 后面第一个 10~20 位纯数字
    m = re.search(r"set3_sessionKey[^0-9]*'(\d{10,20})'", raw)
    if not m:
        m = re.search(r"set3_sessionKey=(\d{10,20})", raw)
    if not m:
        print("[!] 未找到 set3_sessionKey，可能是海思版或固件差异")
        return 2
    set3 = m.group(1)
    print("[+] set3_sessionKey =", set3)

    def tel_and_ftp(enable):
        url = ("/telandftpcfg.cmd?action=add&telusername=admin&telpwd=admin"
               "&telport=23&telenable=%d&ftpusername=useradmin&ftppwd=ftpadmin"
               "&ftpport=21&ftpenable=1&set3_sessionKey=%s" % (enable, set3))
        return get(url)

    print("[*] 开启 Telnet")
    tel_and_ftp(1)
    print("[*] 等待 3 秒让 23 端口就绪...")
    time.sleep(3)

    print("[*] Telnet 登录 + su 提权")
    su_cands = generate_su_passwords(args.mac)
    print("[+] SU 密码候选:", su_cands)

    try:
        ts = TelnetShell(args.ip)
    except Exception as e:
        print("[!] Telnet 连接失败（可能不是博通版或23端口没开）:", e)
        return 3

    ts._read(1.5)
    ts.send("admin", 0.4, 1.5)
    ts.send("admin", 0.4, 1.5)

    ok = False
    for pw in su_cands:
        ts.send("su", 0.5, 1.5)
        d = ts.send(pw, 0.6, 1.5)
        if b"#" in d:
            print("[+] SU 提权成功:", pw)
            ok = True
            break
        # 失败会弹回 $，下一轮循环会重新 su

    if not ok:
        print("[!] SU 密码全部失败，大概率是海思版，本算法不适用")
        ts.close()
        return 3

    print("[*] 读取超级密码")
    ts.send("exit", 0.6, 1.5)
    d = ts.send("telecomadmin get", 0.8, 2.0)
    m = re.search(r"passwd=(\S+)", d)
    if not m:
        print("[!] 未读到密码，原始输出:\n", d)
        ts.close()
        return 4
    super_pwd = m.group(1)
    ts.close()

    print("[*] 关闭 Telnet（恢复原状）")
    tel_and_ftp(0)
    time.sleep(1)

    print("\n" + "=" * 50)
    print("  超级管理员账号: telecomadmin")
    print("  超级管理员密码:", super_pwd)
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
