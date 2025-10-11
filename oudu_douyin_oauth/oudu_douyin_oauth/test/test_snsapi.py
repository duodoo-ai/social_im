import requests
from urllib.parse import quote, urlencode
import json
import time
from typing import Dict, Optional, Tuple


class WeChatOAuth:
    def __init__(self, appid: str, secret: str):
        """
        初始化微信网页授权处理器

        :param appid: 微信公众号的AppID
        :param secret: 微信公众号的AppSecret
        """
        self.appid = appid
        self.secret = secret

    def generate_oauth_url(self, redirect_uri: str, scope: str = "snsapi_userinfo",
                           state: str = None, force_popup: bool = False) -> str:
        """
        生成网页授权链接

        :param redirect_uri: 授权后重定向的回调链接地址
        :param scope: 授权作用域，snsapi_base或snsapi_userinfo
        :param state: 重定向后会带上state参数，可用于防止CSRF攻击
        :param force_popup: 是否强制弹出授权页面
        :return: 构造好的授权URL
        """
        # 对redirect_uri进行URL编码（只编码一次）
        redirect_uri_encoded = quote(redirect_uri, safe='')

        # 构建授权URL - 直接拼接参数，避免双重编码
        base_url = "https://open.weixin.qq.com/connect/oauth2/authorize"
        # 直接拼接参数，避免使用urlencode导致双重编码
        oauth_url = (f"{base_url}?appid={self.appid}"
                     f"&redirect_uri={redirect_uri_encoded}"
                     f"&response_type=code"
                     f"&scope={scope}")

        # 添加可选参数
        if state:
            oauth_url += f"&state={state}"
        if force_popup:
            oauth_url += "&forcePopup=true"

        # 添加微信重定向标识
        oauth_url += "#wechat_redirect"

        return oauth_url

    def get_oauth_token(self, code: str) -> Dict:
        """
        通过code换取网页授权access_token

        :param code: 授权码
        :return: 授权token信息
        """
        url = "https://api.weixin.qq.com/sns/oauth2/access_token"
        params = {
            "appid": self.appid,
            "secret": self.secret,
            "code": code,
            "grant_type": "authorization_code"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()

            if "errcode" in result and result["errcode"] != 0:
                error_msg = f"获取oauth_token失败: [{result['errcode']}] {result.get('errmsg', '未知错误')}"
                raise Exception(error_msg)

            return result

        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"JSON解析失败: {str(e)}")

    # 其他方法保持不变...
    def get_user_info(self, access_token: str, openid: str, lang: str = "zh_CN") -> Dict:
        """
        获取用户基本信息（需要snsapi_userinfo授权）

        :param access_token: 网页授权接口调用凭证
        :param openid: 用户的唯一标识
        :param lang: 返回国家地区语言版本
        :return: 用户信息
        """
        url = "https://api.weixin.qq.com/sns/userinfo"
        params = {
            "access_token": access_token,
            "openid": openid,
            "lang": lang
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()

            if "errcode" in result and result["errcode"] != 0:
                error_msg = f"获取用户信息失败: [{result['errcode']}] {result.get('errmsg', '未知错误')}"
                raise Exception(error_msg)

            return result

        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"JSON解析失败: {str(e)}")

    def refresh_oauth_token(self, refresh_token: str) -> Dict:
        """
        刷新网页授权access_token

        :param refresh_token: 刷新token
        :return: 刷新后的token信息
        """
        url = "https://api.weixin.qq.com/sns/oauth2/refresh_token"
        params = {
            "appid": self.appid,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()

            if "errcode" in result and result["errcode"] != 0:
                error_msg = f"刷新token失败: [{result['errcode']}] {result.get('errmsg', '未知错误')}"
                raise Exception(error_msg)

            return result

        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"JSON解析失败: {str(e)}")

    def check_oauth_token(self, access_token: str, openid: str) -> bool:
        """
        检验网页授权access_token是否有效

        :param access_token: 网页授权接口调用凭证
        :param openid: 用户的唯一标识
        :return: 是否有效
        """
        url = "https://api.weixin.qq.com/sns/auth"
        params = {
            "access_token": access_token,
            "openid": openid
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()

            return result.get("errcode") == 0

        except requests.exceptions.RequestException:
            return False
        except json.JSONDecodeError:
            return False

    def complete_oauth_flow(self, code: str) -> Dict:
        """
        完整的OAuth授权流程

        :param code: 授权码
        :return: 用户信息和token信息
        """
        try:
            # 1. 通过code获取oauth_token
            print("正在通过code获取access_token...")
            token_info = self.get_oauth_token(code)

            access_token = token_info.get("access_token")
            openid = token_info.get("openid")
            scope = token_info.get("scope")

            print(f"✅ 成功获取access_token: {access_token[:20]}...")
            print(f"OpenID: {openid}")
            print(f"授权范围: {scope}")

            result = {"token_info": token_info}

            # 2. 如果是snsapi_userinfo授权，获取用户详细信息
            if scope == "snsapi_userinfo" and access_token and openid:
                print("正在获取用户详细信息...")
                user_info = self.get_user_info(access_token, openid)
                result["user_info"] = user_info

                print("✅ 成功获取用户信息:")
                print(f"   昵称: {user_info.get('nickname', '未知')}")
                print(f"   OpenID: {user_info.get('openid')}")
                if 'unionid' in user_info:
                    print(f"   UnionID: {user_info.get('unionid')}")

            return result

        except Exception as e:
            print(f"❌ OAuth流程失败: {str(e)}")
            return {"error": str(e)}


# 使用示例
if __name__ == "__main__":
    # 配置参数（请替换为你的实际参数）
    APPID = "wx065d1d2cac29ab41"  # 你的服务号AppID
    SECRET = "8fab07c28b90737fbcfd5c931e522f38"  # 你的服务号AppSecret
    REDIRECT_URI = "http://www.ningzhuhui.com/wechat/callback"  # 授权回调地址

    # 创建OAuth处理器
    oauth = WeChatOAuth(APPID, SECRET)

    print("=== 微信snsapi_userinfo网页授权示例 ===\n")

    # 1. 生成授权链接
    print("1. 生成授权链接:")
    auth_url = oauth.generate_oauth_url(
        redirect_uri=REDIRECT_URI,
        scope="snsapi_userinfo",
        state="custom_state_123",
        force_popup=True
    )
    print(f"授权URL: {auth_url}")
    print("请将此链接在微信客户端中打开\n")

    # 2. 模拟处理回调（实际中由回调URL处理）
    print("2. 模拟处理授权回调:")
    print("请在微信中完成授权后，输入回调URL中的code参数:")

    # 这里模拟获取到的code（实际应从回调URL的查询参数中获取）
    simulated_code = input("请输入授权code: ").strip()

    if simulated_code:
        # 3. 完成完整的OAuth流程
        print("\n3. 执行OAuth流程:")
        result = oauth.complete_oauth_flow(simulated_code)

        if "error" in result:
            print(f"授权失败: {result['error']}")
        else:
            print("\n✅ 授权成功完成!")
            print(f"Token信息: {json.dumps(result.get('token_info', {}), indent=2, ensure_ascii=False)}")

            if "user_info" in result:
                print(f"用户信息: {json.dumps(result.get('user_info', {}), indent=2, ensure_ascii=False)}")

    # 4. 演示其他功能
    print("\n4. 其他功能演示:")

    # 如果有token信息，演示刷新和检查功能
    if 'token_info' in locals().get('result', {}) and 'refresh_token' in result.get('token_info', {}):
        refresh_token = result['token_info']['refresh_token']

        print("演示token刷新功能...")
        try:
            refreshed = oauth.refresh_oauth_token(refresh_token)
            print(f"✅ Token刷新成功: {refreshed.get('access_token')[:20]}...")
        except Exception as e:
            print(f"❌ Token刷新失败: {str(e)}")

        # 检查token有效性
        if 'access_token' in result['token_info'] and 'openid' in result['token_info']:
            is_valid = oauth.check_oauth_token(
                result['token_info']['access_token'],
                result['token_info']['openid']
            )
            print(f"Token有效性检查: {'有效' if is_valid else '无效'}")