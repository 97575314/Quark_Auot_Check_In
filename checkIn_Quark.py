import os
import re
import sys
import requests


def send(title, message):
    print(f"{title}: {message}")


def get_env():
    """读取 COOKIE_QUARK，支持按换行或 && 分隔多个账号。"""
    raw = os.getenv("COOKIE_QUARK", "").strip()
    if not raw:
        print("❌未添加COOKIE_QUARK变量")
        send("夸克自动签到", "❌未添加COOKIE_QUARK变量")
        sys.exit(0)

    # 兼容：多账号用 \n 或 && 分隔；单账号也兼容直接传入
    parts = []
    for item in re.split(r"(?:\n|&&)", raw):
        item = item.strip()
        if item:
            parts.append(item)

    if not parts:
        print("❌COOKIE_QUARK为空或格式不正确")
        send("夸克自动签到", "❌COOKIE_QUARK为空或格式不正确")
        sys.exit(0)

    return parts


class Quark:
    '''
    Quark类封装了签到、领取签到奖励的方法
    '''

    def __init__(self, user_data):
        self.param = user_data

    def convert_bytes(self, b):
        '''
        将字节转换为 MB GB TB
        '''
        units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = 0
        while b >= 1024 and i < len(units) - 1:
            b /= 1024
            i += 1
        return f"{b:.2f} {units[i]}"

    def get_growth_info(self):
        '''
        获取用户当前的签到信息
        '''
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info"
        querystring = {
            "pr": "ucpro",
            "fr": "android",
            "kps": self.param.get('kps'),
            "sign": self.param.get('sign'),
            "vcode": self.param.get('vcode')
        }
        try:
            response = requests.get(url=url, params=querystring, timeout=20)
            print(f"[DEBUG] get_growth_info status={response.status_code} url={url}")
            payload = response.json()
            print(f"[DEBUG] get_growth_info payload={payload}")
            if payload.get("data"):
                return payload["data"]
            return False
        except Exception as e:
            print(f"[ERROR] get_growth_info exception: {e}")
            return False

    def get_growth_sign(self):
        '''
        执行签到请求
        '''
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/sign"
        querystring = {
            "pr": "ucpro",
            "fr": "android",
            "kps": self.param.get('kps'),
            "sign": self.param.get('sign'),
            "vcode": self.param.get('vcode')
        }
        data = {"sign_cyclic": True}
        try:
            response = requests.post(url=url, json=data, params=querystring, timeout=20)
            print(f"[DEBUG] get_growth_sign status={response.status_code}")
            payload = response.json()
            print(f"[DEBUG] get_growth_sign payload={payload}")
            if payload.get("data"):
                return True, payload["data"].get("sign_daily_reward")
            return False, payload.get("message", "签到请求返回异常")
        except Exception as e:
            print(f"[ERROR] get_growth_sign exception: {e}")
            return False, str(e)

    def queryBalance(self):
        '''
        查询抽奖余额
        '''
        url = "https://coral2.quark.cn/currency/v1/queryBalance"
        querystring = {
            "moduleCode": "1f3563d38896438db994f118d4ff53cb",
            "kps": self.param.get('kps'),
        }
        try:
            response = requests.get(url=url, params=querystring, timeout=20)
            payload = response.json()
            if payload.get("data"):
                return payload["data"].get("balance")
            return payload.get("msg", "查询余额失败")
        except Exception as e:
            return str(e)

    def do_sign(self):
        '''
        执行签到任务
        '''
        log = ""
        growth_info = self.get_growth_info()
        if growth_info:
            user_name = self.param.get('user', '未知用户')
            log += (
                f" {'88VIP' if growth_info.get('88VIP') else '普通用户'} {user_name}\n"
                f"💾 网盘总容量：{self.convert_bytes(growth_info.get('total_capacity', 0))}，"
                f"签到累计容量："
            )
            if "sign_reward" in growth_info.get('cap_composition', {}):
                log += f"{self.convert_bytes(growth_info['cap_composition']['sign_reward'])}\n"
            else:
                log += "0 MB\n"

            cap_sign = growth_info.get('cap_sign', {})
            if cap_sign.get("sign_daily"):
                log += (
                    f"✅ 签到日志: 今日已签到+{self.convert_bytes(cap_sign.get('sign_daily_reward', 0))}，"
                    f"连签进度({cap_sign.get('sign_progress', 0)}/{cap_sign.get('sign_target', 0)})\n"
                )
            else:
                sign, sign_return = self.get_growth_sign()
                if sign:
                    log += (
                        f"✅ 执行签到: 今日签到+{self.convert_bytes(sign_return or 0)}，"
                        f"连签进度({cap_sign.get('sign_progress', 0) + 1}/{cap_sign.get('sign_target', 0)})\n"
                    )
                else:
                    log += f"❌ 签到异常: {sign_return}\n"
        else:
            raise Exception("❌ 签到异常: 获取成长信息失败")

        return log


def parse_cookie_block(raw_block):
    """解析单个账号 Cookie 块。支持多种常见分隔格式。"""
    clean = raw_block.strip().replace(" ", "")
    if not clean:
        return {}

    user_data = {}
    for item in clean.split(';'):
        if not item or '=' not in item:
            continue
        key, value = item.split('=', 1)
        if key:
            user_data[key] = value
    return user_data


def main():
    msg = ""
    cookie_quark = get_env()
    print(f"✅ 检测到共 {len(cookie_quark)} 个夸克账号\n")

    for i, cookie_block in enumerate(cookie_quark, start=1):
        user_data = parse_cookie_block(cookie_block)
        if not user_data:
            msg += f"🙍🏻‍♂️ 第{i}个账号\n❌ Cookie 格式异常，未解析到有效参数\n\n"
            print(f"[WARN] 第{i}个账号 Cookie 格式异常，未解析到有效参数")
            continue

        print(f"\n==== 第{i}个账号开始处理 ====")
        msg += f"🙍🏻‍♂️ 第{i}个账号\n"
        try:
            log = Quark(user_data).do_sign()
            msg += log + "\n"
        except Exception as err:
            msg += f"❌ 失败: {err}\n\n"
            print(f"[ERROR] 第{i}个账号签到失败: {err}")

    try:
        send('夸克自动签到', msg)
    except Exception as err:
        print(f"{err}\n❌ 错误，请查看运行日志！")

    return msg[:-1] if msg else ""


if __name__ == "__main__":
    print("----------夸克网盘开始签到----------")
    main()
    print("----------夸克网盘签到完毕----------")
