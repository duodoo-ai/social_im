import requests
import time
from typing import Dict, Optional, Tuple


class WechatAccessTokenTester:
    def __init__(self, appid: str, secret: str):
        """
        初始化测试器

        :param appid: 微信公众号的AppID
        :param secret: 微信公众号的AppSecret
        """
        self.appid = appid
        self.secret = secret
        self.access_token_url = "https://api.weixin.qq.com/cgi-bin/token"

    def get_access_token(self, timeout: int = 10) -> Dict:
        """
        获取接口调用凭据 (access_token)

        :param timeout: 请求超时时间（秒）
        :return: 微信API的响应数据字典
        """
        # 构造请求参数
        params = {
            "grant_type": "client_credential",
            "appid": self.appid,
            "secret": self.secret
        }

        try:
            # 发送GET请求
            response = requests.get(
                self.access_token_url,
                params=params,
                timeout=timeout
            )
            response.raise_for_status()  # 检查HTTP状态码是否异常

            # 解析JSON响应
            result = response.json()
            return result

        except requests.exceptions.RequestException as e:
            # 网络请求异常
            return {
                "errcode": -1,
                "errmsg": f"网络请求失败: {str(e)}"
            }
        except ValueError as e:
            # JSON解析异常
            return {
                "errcode": -1,
                "errmsg": f"响应解析失败: {str(e)}"
            }

    def interpret_error_code(self, errcode: int) -> str:
        """
        解释错误码的含义

        :param errcode: 错误码
        :return: 错误描述
        """
        error_mapping = {
            -1: "系统繁忙，此时请开发者稍候再试",
            40001: "AppSecret错误或者access_token无效",
            40002: "不合法的凭证类型",
            40013: "不合法的AppID",
            40125: "不合法的secret",
            40164: "调用接口的IP地址不在白名单中",
            40243: "AppSecret已被冻结，请解冻后再次调用",
            41004: "缺少secret参数",
            50004: "禁止使用token接口",
            50007: "账号已冻结"
        }

        return error_mapping.get(errcode, "未知错误码")

    def run_test(self):
        """
        执行测试流程
        """
        print("=== 微信服务号「获取接口调用凭据」接口测试 ===\n")

        print(f"AppID: {self.appid}")
        print(f"AppSecret: {self.secret}")
        print(f"请求URL: {self.access_token_url}")
        print("参数: grant_type=client_credential")
        print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)

        # 发送请求获取access_token
        print("1. 正在发送请求获取access_token...")
        result = self.get_access_token()

        # 处理响应结果
        print("2. 收到响应，解析结果...")
        print("-" * 50)

        if "errcode" in result and result["errcode"] != 0:
            # 接口返回错误
            error_code = result["errcode"]
            error_msg = result.get("errmsg", "")
            error_interpretation = self.interpret_error_code(error_code)

            print(f"❌ 请求失败!")
            print(f"   错误码: {error_code}")
            print(f"   错误信息: {error_msg}")
            print(f"   解释: {error_interpretation}")

            # 针对特定错误码给出建议
            if error_code == 40164:
                print("   💡 解决方案: 请登录微信公众平台，将服务器IP地址添加到IP白名单中")
            elif error_code == 40243:
                print("   💡 解决方案: 请登录微信公众平台，解冻AppSecret")
            elif error_code in [40001, 40013, 40125]:
                print("   💡 解决方案: 请检查AppID和AppSecret是否正确配置")

        elif "access_token" in result:
            # 请求成功
            access_token = result["access_token"]
            expires_in = result["expires_in"]

            print("✅ 获取access_token成功!")
            print(f"   Access Token: {access_token}")
            print(f"   Access Token: {access_token[:20]}... (共{len(access_token)}字符)")
            print(f"   有效期: {expires_in}秒 (约{expires_in / 3600:.1f}小时)")
            print(f"   到期时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + expires_in))}")

        else:
            # 未知响应格式
            print("⚠️  接收到未知格式的响应:")
            print(f"   {result}")


# 测试执行
if __name__ == "__main__":
    # 初始化测试器 (请替换为你的AppID和AppSecret)
    appid = "wx065d1d2cac29ab41"  # 替换为你的AppID
    secret = "6961da76f8438ec1cba76bac583794f2"  # 替换为你的AppSecret

    tester = WechatAccessTokenTester(appid, secret)

    # 运行测试
    tester.run_test()