# 电信天邑 TEWA-1100G 光猫超级管理员密码获取教程（避坑版）

> 仅限你自己的光猫设备，用于找回忘记的管理密码、改桥接、做端口映射或安全自查。
> 全程可逆：拿到密码后 Telnet 会被关闭，宽带/WiFi/拨号配置一字不改。

\---

## 〇、先判断你的机型：博通版 or 海思版？（最关键）

**本教程的 SU 密码算法只适用于「博通版」。** 天邑 TEWA-1100 系列存在博通 / 海思两种芯片方案，
海思版 SU 算法不同，照本教程会卡死在 su 提权。

### 判断方法（任选其一）

1. **看板卡号（最准）**：登录 8080 后台后，按 F12 在首页源码里搜 `BoardId`。

   * 博通版：`BoardId=TY968560CTNW`（或含 TY968 / 968 字样）
   * 海思版：`BoardId=Hi5682`（或含 Hi / Hisilicon 字样）
2. **看设备类型字符串**：首页源码搜 `obj1Items`，博通版含 `SCTY` 或 `TY968`。
3. **看序列号格式**：博通版序列号形如 `7CDAC3-XXXXXXXXXX`，含 `-` 分隔。

**确认是博通版再继续。** 海思版请另找海思 SU 算法。

\---

## 一、适用机型

|项目|值|
|-|-|
|设备型号|天邑 TEWA-1100G（XG-PON 天翼网关）|
|板卡|TY968560CTNW（博通方案）|
|软件版本|V1.0.1|
|定制地区|浙江电信（ZheJiang）|
|超级账号|telecomadmin|
|默认超密|nE7jA%5m（**注意：电信下发时已改成随机密码，本教程就是找回它**）|

> 同系列 TEWA-707E / 708E / 768G / 1000E / 1000G 等\*\*博通版\*\*，原理相同，接口可能略有差异。

\---

## 二、原理

天邑博通版光猫的超级密码存储于运行时配置库（CMS 配置管理系统），普通 Web 用户读不到。
但有两条关键通道可以绕开：

1. **8080 端口是烽火 SCTY 维护后台**，登录普通用户后，设备管理页会泄露一个
`set3\_sessionKey`（用于恢复出厂设置的会话密钥）。
2. 用这个 `set3\_sessionKey` 调 `telandftpcfg.cmd` 接口，可以**临时开启 Telnet**（可逆）。
3. Telnet 登录后 `su` 提权，SU 密码由 **MAC 地址通过固定算法**生成（逆向自
`/lib/libcms\_cli.so`，共 3 种算法）。
4. 进入 BusyBox 后 `exit` 退回厂商 CLI（提示符 `>`），执行 `telecomadmin get`
即可直接打印超级管理员密码。

\---

## 三、完整步骤

### 准备

* 光猫背面普通账号：`useradmin` + 密码（贴纸上的）
* 光猫 MAC（贴纸上，形如 `AABBCCDDEEFF`）
* 电脑与光猫同网段

### 步骤 1：登录 8080 维护后台

浏览器打开：

```
http://192.168.1.1:8080
```

用 `useradmin` + 背面密码登录（密码走 base64，浏览器自动处理，你直接输明文即可）。

### 步骤 2：抓 set3\_sessionKey（格式有坑，务必看）

登录后进入 **管理 → 设备管理**，按 F12 查看该页面源码，搜索 `set3\_sessionKey`。

**真实源码格式是带 `' + '` 拼接的**，别被吓到：

```javascript
function restoreClick() {
    var loc = 'restoreinfo.cgi?';
    loc += 'set3\_sessionKey=' + '5860618011875578735';   // ← 中间这串 15\~19 位数字才是
    ...
}
```

**要点：**

* 认准 `set3\_sessionKey` 后面引号里的那串**纯数字**（15\~19 位），不是 `' + '` 这种拼接符号
* 有的固件可能直接写成 `set3\_sessionKey=1234567890123456789`（不带拼接），一样认数字
* 这个 key **每次刷新都会变**，用最新一次抓到的
* 如果 F12 看不到，改用「网络(Network)」抓 `MD\_Device\_user.html` 的响应体，一样能搜到

### 步骤 3：开启 Telnet

把下面的 `XXX` 替换成你抓到的 `set3\_sessionKey`，浏览器打开：

```
http://192.168.1.1:8080/telandftpcfg.cmd?action=add\&telusername=admin\&telpwd=admin\&telport=23\&telenable=1\&ftpusername=useradmin\&ftppwd=ftpadmin\&ftpport=21\&ftpenable=1\&set3\_sessionKey=XXX
```

返回 Telnet 配置页（含 `AlltelnetInfo` 字样）即成功。

**⚠️ 关键：开完别急着连，等 2\~3 秒让 23 端口真正起来。**

### 步骤 4：Telnet 登录

```
telnet 192.168.1.1
用户名: admin
密码:   admin
```

登录成功提示符为 `$`。

> Windows 没有自带 telnet 命令的话：控制面板 → 程序和功能 → 启用或关闭 Windows 功能 → 勾选 Telnet 客户端。
> 或用 `putty`、`xshell` 连接，类型选 Telnet。

### 步骤 5：su 提权（SU 密码由 MAC 生成）

```
$ su
Password: <输入下面算出的 SU 密码>
#          ← 出现 # 说明已进入 BusyBox
```

SU 密码算法见下文「SU 密码算法」，用光猫 MAC 算出 3 个候选。

**⚠️ 试错流程（重要）：**

* 第 1 个候选输错 → 会显示 `Error!` 并弹回 `$` 提示符
* **必须重新输一次 `su`**，再输第 2 个候选
* 依次类推，3 个里必有一个命中，命中后提示符变 `#`

### 步骤 6：读取超级密码

```
# exit
> telecomadmin get
passwd=XXXXXXXXXXXX     ← 这里就是你光猫的超级管理员密码
>
```

> 注意：`telecomadmin get` 要在 `>` 提示符（厂商 CLI）下执行，\*\*不是在 `#`（BusyBox）里\*\*。
> 这就是为什么要先 `exit` 退出来。

### 步骤 7：关闭 Telnet（可逆，恢复原状）

用 `telenable=0` 再调一次同一接口：

```
http://192.168.1.1:8080/telandftpcfg.cmd?action=add\&telusername=admin\&telpwd=admin\&telport=23\&telenable=0\&ftpusername=useradmin\&ftppwd=ftpadmin\&ftpport=21\&ftpenable=1\&set3\_sessionKey=XXX
```

23 端口恢复关闭。

\---

## 四、SU 密码算法（逆向自 libcms\_cli.so，仅博通版）

天邑博通版 SU 密码由 MAC 地址经 3 套查表算法生成，输出 3 组候选，任一组命中即可。

```python
def generate\_su\_passwords(mac):
    """
    输入光猫 MAC（任意格式：AABBCCDDEEFF / AA:BB:CC:DD:EE:FF / AA-BB-...）
    输出 3 组 SU 密码候选
    """
    ct1 = 'QbNUTaMecPWVSKdCgXIJRrsfYXwyqpvnDHWzQuPmAGtAxRTphBcwBnNkjbFmvVMqaFkEutSrDCxsCKjBzEyDEUJTZfHZghMHYFdeASGNaUgFtdbYRkshJHkFNXMcKdfw'
    ct2 = 'NXMcKdfwRkshJHkFaUgFtdbYYFdeASGNZfHZghMHzEyDEUJTDCxsCKjBaFkEutSrjbFmvVMqhBcwBnNkAGtAxRTpDHWzQuPmYXwyqpvngXIJRrsfcPWVSKdCQbNUTaMe'
    ct3 = 'eMaTUNbQCdKSVWPcfsrRJIXgnvpqywXYmPuQzWHDpTRxAtGAkNnBwcBhqMVvmFbjrStuEkFaBjKCsxCDTJUEDyEzHMhgZHfZNGSAedFYYbdtFgUaFkHJhskRwfdKcMXN'

    hex\_clean = ''.join(c for c in mac.upper() if c in '0123456789ABCDEF')
    if len(hex\_clean) < 12:
        return \['MAC地址格式错误']

    v19 = \[ord(c) for c in hex\_clean\[-8:]]\[::-1]
    v10 = 5
    for j in range(len(v19)):
        c = v19\[j]
        if 49 <= c <= 57:          # '1'..'9'
            v10 = (c - 48) | j
            break

    a1, a2, a3 = \[], \[], \[]
    for k in range(len(v19)):
        v15 = (v19\[k] \& v19\[7 - k]) if k < 4 else (v19\[k] | v19\[k - 4])
        v16 = v15 + v10
        if v16 > 127:
            v16 = k
            v10 = k
        a1.append(ct1\[v16])
        a2.append(ct2\[v16])
        a3.append(ct3\[v16])
        v10 += max(k, 1)
    return \[''.join(a1), ''.join(a2), ''.join(a3)]
```

\---

## 五、一键脚本

见同目录 `get\_super\_password.py`，填好 MAC 和光猫背面密码，一条命令跑完：

```
python get\_super\_password.py --mac 你的光猫MAC --password 光猫背面密码
```

脚本会自动：登录 → 抓 key → 开 Telnet → 提权 → 读超密 → 关 Telnet。

\---

## 六、常见问题（FAQ）

|问题|原因|解决|
|-|-|-|
|su 密码 3 个全错|你是海思版，不是博通版|先做「〇、判断机型」那步|
|set3\_sessionKey 抓不到|正则/格式差异|认准 `set3\_sessionKey` 后面引号里的纯数字|
|开完 Telnet 连不上|端口没起来|等 2\~3 秒再连，或重复调一次接口|
|`telecomadmin get` 报 not found|你在 `#` 里执行了|先 `exit` 到 `>` 再执行|
|登录 8080 失败|密码错/被锁定|输错 3 次锁 1 分钟，等一分钟再试|

\---

## 七、参考

* 恩山论坛《电信天邑光猫TEWA系列获取超级密码以及宽带密码教程》
* 恩山论坛《2021年7月后出厂电信天邑TEWA-750/708/768/800/1000等超级密码破解方法及工具》
* 恩山论坛《天邑光猫su密码算法》（chinesesuper，逆向 libcms\_cli.so）

