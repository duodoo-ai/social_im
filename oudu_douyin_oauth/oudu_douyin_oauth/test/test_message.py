import requests
import json
import time
from typing import Dict, List, Optional


class WeChatUserInfoManager:
    def __init__(self, access_token: str):
        """
        初始化微信用户信息管理器

        :param access_token: 微信接口调用凭证
        """
        self.access_token = access_token
        self.user_info_url = "https://api.weixin.qq.com/cgi-bin/user/info"

    def get_user_info(self, openid: str, lang: str = "zh_CN") -> Dict:
        """
        获取用户基本信息
        官方文档: https://developers.weixin.qq.com/doc/offiaccount/User_Management/Getting_a_User_List.html

        :param openid: 用户的OpenID
        :param lang: 返回国家地区语言版本，zh_CN 简体，zh_TW 繁体，en 英语
        :return: 用户信息字典或错误信息
        """
        # 构造请求参数
        params = {
            'access_token': self.access_token,
            'openid': openid,
            'lang': lang
        }

        try:
            # 发送GET请求
            response = requests.get(
                self.user_info_url,
                params=params,
                timeout=10
            )
            response.raise_for_status()  # 检查HTTP错误

            result = response.json()

            # 检查微信API返回的错误码
            if 'errcode' in result and result['errcode'] != 0:
                error_msg = f"微信接口错误: [{result['errcode']}] {result.get('errmsg', '未知错误')}"
                return {"error": error_msg, "errcode": result['errcode']}

            return result

        except requests.exceptions.RequestException as e:
            return {"error": f"网络请求失败: {str(e)}", "errcode": -1}
        except json.JSONDecodeError as e:
            return {"error": f"JSON解析失败: {str(e)}", "errcode": -1}

    def get_users_info_batch(self, openids: List[str], lang: str = "zh_CN") -> List[Dict]:
        """
        批量获取用户基本信息
        注意：此接口有频率限制，请谨慎调用

        :param openids: 用户OpenID列表
        :param lang: 返回国家地区语言版本
        :return: 用户信息列表
        """
        # 微信批量获取用户信息接口
        url = f"https://api.weixin.qq.com/cgi-bin/user/info/batchget?access_token={self.access_token}"

        # 构造请求数据
        user_list = [{"openid": openid, "lang": lang} for openid in openids]
        data = {"user_list": user_list}

        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()

            result = response.json()

            if 'errcode' in result and result['errcode'] != 0:
                error_msg = f"微信接口错误: [{result['errcode']}] {result.get('errmsg', '未知错误')}"
                return [{"error": error_msg, "errcode": result['errcode']}]

            return result.get('user_info_list', [])

        except requests.exceptions.RequestException as e:
            return [{"error": f"网络请求失败: {str(e)}", "errcode": -1}]
        except json.JSONDecodeError as e:
            return [{"error": f"JSON解析失败: {str(e)}", "errcode": -1}]

    def interpret_user_info_result(self, user_data: Dict) -> str:
        """
        解释用户信息结果

        :param user_data: 用户信息字典
        :return: 格式化后的结果字符串
        """
        if "error" in user_data:
            return f"❌ 错误: {user_data['error']}"

        # 检查用户是否关注公众号
        subscribe = user_data.get('subscribe', 0)
        if subscribe == 0:
            return f"❌ 用户未关注公众号，只能获取基本OpenID: {user_data.get('openid')}"

        # 格式化用户信息
        result = []
        result.append("✅ 用户详细信息:")
        result.append(f"  OpenID: {user_data.get('openid')}")
        result.append(f"  昵称: {user_data.get('nickname', '未知')}")
        result.append(f"  性别: {self.get_gender_text(user_data.get('sex', 0))}")
        result.append(f"  国家: {user_data.get('country', '未知')}")
        result.append(f"  省份: {user_data.get('province', '未知')}")
        result.append(f"  城市: {user_data.get('city', '未知')}")
        result.append(f"  语言: {user_data.get('language', '未知')}")

        # 处理关注时间（时间戳转换为可读格式）
        subscribe_time = user_data.get('subscribe_time')
        if subscribe_time:
            time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(subscribe_time))
            result.append(f"  关注时间: {time_str}")

        result.append(f"  备注: {user_data.get('remark', '无')}")
        result.append(f"  分组ID: {user_data.get('groupid', '无')}")

        # 处理标签列表
        tagid_list = user_data.get('tagid_list', [])
        if tagid_list:
            result.append(f"  标签列表: {', '.join(map(str, tagid_list))}")
        else:
            result.append("  标签列表: 无")

        result.append(f"  关注来源: {self.get_subscribe_scene_text(user_data.get('subscribe_scene', '未知'))}")

        # UnionID（如果存在）
        if 'unionid' in user_data:
            result.append(f"  UnionID: {user_data.get('unionid')}")

        return "\n".join(result)

    def get_gender_text(self, gender_code: int) -> str:
        """将性别代码转换为文本"""
        gender_map = {0: "未知", 1: "男", 2: "女"}
        return gender_map.get(gender_code, "未知")

    def get_subscribe_scene_text(self, scene_code: str) -> str:
        """将关注来源代码转换为文本"""
        scene_map = {
            "ADD_SCENE_SEARCH": "公众号搜索",
            "ADD_SCENE_ACCOUNT_MIGRATION": "公众号迁移",
            "ADD_SCENE_PROFILE_CARD": "名片分享",
            "ADD_SCENE_QR_CODE": "扫描二维码",
            "ADD_SCENE_PROFILE_LINK": "图文页内名称点击",
            "ADD_SCENE_PROFILE_ITEM": "图文页右上角菜单",
            "ADD_SCENE_PAID": "支付后关注",
            "ADD_SCENE_WECHAT_ADVERTISEMENT": "微信广告",
            "ADD_SCENE_REPRINT": "他人转载",
            "ADD_SCENE_LIVESTREAM": "视频号直播",
            "ADD_SCENE_CHANNELS": "视频号",
            "ADD_SCENE_WXA": "小程序关注",
            "ADD_SCENE_OTHERS": "其他"
        }
        return scene_map.get(scene_code, scene_code)


# 使用示例
if __name__ == "__main__":
    # 你的access_token（从之前成功的测试中获取）
    ACCESS_TOKEN = "95_rRUMnw_xgZPCM1s5y3aQ07cHmDwbnDRYjpQAti8ejzNxrw2y3y-uE9ScYWCRJxqcGUODqg2_JKJhReqkBhj7TCZCOME00R4rBkOORPPTh9TAoa1icgU0zI77kx4HVMeAFAKYP"

    # 你的用户OpenID列表（从之前成功的测试中获取）
    USER_OPENIDS = [
        "o9k4H2NuurmITFVVLlygBq299ZY8",
        "o9k4H2E5urnH9wxy9iZa2LGacjAs",
    ]

    # 创建用户信息管理器
    user_manager = WeChatUserInfoManager(ACCESS_TOKEN)

    print("=== 微信服务号「获取用户基本信息」接口测试 ===\n")

    # 方法1: 获取单个用户信息
    print("1. 获取单个用户信息:")
    first_user_info = user_manager.get_user_info(USER_OPENIDS[0])
    print(user_manager.interpret_user_info_result(first_user_info))
    print("\n" + "=" * 50 + "\n")

    # 方法2: 批量获取用户信息（前两个用户）
    print("2. 批量获取用户信息:")
    batch_users_info = user_manager.get_users_info_batch(USER_OPENIDS[:2])

    for i, user_info in enumerate(batch_users_info):
        print(f"用户 {i + 1}:")
        print(user_manager.interpret_user_info_result(user_info))
        print("-" * 30)

    print("\n" + "=" * 50 + "\n")

    # 方法3: 逐个获取所有用户信息
    print("3. 逐个获取所有用户信息:")
    for i, openid in enumerate(USER_OPENIDS):
        print(f"用户 {i + 1} (OpenID: {openid}):")
        user_info = user_manager.get_user_info(openid)
        print(user_manager.interpret_user_info_result(user_info))
        print("-" * 30)

        # 添加延迟，避免请求过于频繁
        time.sleep(0.1)