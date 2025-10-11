import requests
import json
import time
from typing import Dict, List, Optional


class WeChatFollowerManager:
    def __init__(self, access_token: str):
        """
        初始化微信关注用户管理器

        :param access_token: 微信接口调用凭证
        """
        self.access_token = access_token
        self.base_url = "https://api.weixin.qq.com/cgi-bin/user/get"

    def get_followers_list(self, next_openid: str = None) -> Dict:
        """
        获取关注用户列表
        官方文档: https://developers.weixin.qq.com/doc/offiaccount/User_Management/Getting_a_User_List.html

        :param next_openid: 上一个拉取列表的最后一个OPENID，None表示从开始拉取
        :return: 微信API的响应数据
        """
        # 构造请求参数
        params = {
            'access_token': self.access_token
        }

        if next_openid:
            params['next_openid'] = next_openid

        try:
            # 发送GET请求
            response = requests.get(
                self.base_url,
                params=params,
                timeout=10  # 设置超时时间
            )
            response.raise_for_status()  # 检查HTTP错误

            result = response.json()

            # 检查微信API返回的错误码
            if 'errcode' in result and result['errcode'] != 0:
                error_msg = f"微信接口错误: [{result['errcode']}] {result.get('errmsg', '未知错误')}"
                raise Exception(error_msg)

            return result

        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"JSON解析失败: {str(e)}")

    def get_all_followers(self, delay: float = 0.1) -> List[str]:
        """
        获取所有关注用户的OpenID列表（自动处理分页）

        :param delay: 每次请求之间的延迟时间（秒），避免频繁请求
        :return: 所有关注用户的OpenID列表
        """
        all_openids = []
        next_openid = None
        total_count = 0

        print("开始获取关注用户列表...")

        while True:
            try:
                # 添加延迟，避免请求过于频繁
                if delay > 0:
                    time.sleep(delay)

                # 获取一批用户
                result = self.get_followers_list(next_openid)

                # 处理返回结果
                batch_openids = result.get('data', {}).get('openid', [])
                total = result.get('total', 0)
                count = result.get('count', 0)
                next_openid = result.get('next_openid')

                # 如果是第一次请求，显示总用户数
                if not all_openids:
                    total_count = total
                    print(f"总关注用户数: {total_count}")

                # 添加当前批次的OpenID
                all_openids.extend(batch_openids)
                print(f"已获取 {len(all_openids)}/{total_count} 个用户")

                # 检查是否已获取所有用户
                if not next_openid or count == 0 or len(all_openids) >= total_count:
                    break

            except Exception as e:
                print(f"获取用户列表时出错: {str(e)}")
                break

        return all_openids

    def get_users_info(self, openids: List[str], lang: str = "zh_CN") -> List[Dict]:
        """
        批量获取用户详细信息（需要用户已关注公众号）
        注意：此接口有频率限制，请谨慎调用

        :param openids: 用户OpenID列表
        :param lang: 语言设置
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
                raise Exception(error_msg)

            return result.get('user_info_list', [])

        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"JSON解析失败: {str(e)}")


# 使用示例
if __name__ == "__main__":
    # 你的access_token（实际使用时应该从安全的地方获取）
    ACCESS_TOKEN = "95_rRUMnw_xgZPCM1s5y3aQ07cHmDwbnDRYjpQAti8ejzNxrw2y3y-uE9ScYWCRJxqcGUODqg2_JKJhReqkBhj7TCZCOME00R4rBkOORPPTh9TAoa1icgU0zI77kx4HVMeAFAKYP"

    # 创建管理器实例
    manager = WeChatFollowerManager(ACCESS_TOKEN)

    try:
        # 方法1: 获取单页用户列表
        print("=== 获取单页用户列表 ===")
        first_page = manager.get_followers_list()
        print(f"总用户数: {first_page.get('total', 0)}")
        print(f"本次获取数量: {first_page.get('count', 0)}")
        print(f"第一个OpenID示例: {first_page.get('data', {}).get('openid', [])[:3]}")
        print(f"下一个OpenID: {first_page.get('next_openid', '')}")

        # 方法2: 获取所有用户OpenID列表
        print("\n=== 获取所有用户OpenID列表 ===")
        all_openids = manager.get_all_followers()
        print(f"成功获取 {len(all_openids)} 个关注用户")

        # 方法3: 批量获取用户详细信息（可选，演示获取前5个用户）
        if len(all_openids) > 0:
            print("\n=== 批量获取用户详细信息 ===")
            # 只获取前5个用户信息作为演示，避免频繁调用
            sample_openids = all_openids[:5]
            users_info = manager.get_users_info(sample_openids)

            for user in users_info:
                print(
                    f"用户: {user.get('nickname', '未知')}, OpenID: {user.get('openid')}, 关注时间: {user.get('subscribe_time', 0)}")

    except Exception as e:
        print(f"程序执行出错: {str(e)}")