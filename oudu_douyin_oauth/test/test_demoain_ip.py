import requests
import json
import time
from typing import List, Dict, Optional


class WeChatIPManager:
    def __init__(self, access_token: str):
        """
        初始化微信IP管理器

        :param access_token: 微信接口调用凭证
        """
        self.access_token = access_token
        self.api_url = "https://api.weixin.qq.com/cgi-bin/get_api_domain_ip"

    def get_wechat_api_ips(self) -> Dict:
        """
        获取微信API服务器IP地址列表
        官方文档: https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Get_the_WeChat_server_IP_address.html

        :return: 包含IP列表或错误信息的字典
        """
        # 构造请求参数
        params = {
            'access_token': self.access_token
        }

        try:
            # 发送GET请求
            response = requests.get(
                self.api_url,
                params=params,
                timeout=10  # 设置10秒超时
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

    def format_ip_list(self, ip_data: Dict) -> str:
        """
        格式化IP列表输出

        :param ip_data: 接口返回的IP数据
        :return: 格式化后的字符串
        """
        if "error" in ip_data:
            return f"❌ 错误: {ip_data['error']}"

        ip_list = ip_data.get('ip_list', [])
        if not ip_list:
            return "⚠️ 未获取到IP地址列表"

        result = []
        result.append("✅ 微信API服务器IP地址列表:")
        result.append(f"   共获取到 {len(ip_list)} 个IP地址:")

        for i, ip in enumerate(ip_list, 1):
            result.append(f"   {i:2d}. {ip}")

        result.append("\n💡 注意事项:")
        result.append("   • 微信服务器IP可能会变动，建议每天获取一次")
        result.append("   • 不要长期使用旧的IP列表，避免单点故障")
        result.append("   • 使用固定IP时请注意运营商适配")

        return "\n".join(result)

    def save_ips_to_file(self, ip_data: Dict, filename: str = "wechat_ips.json"):
        """
        将IP列表保存到文件

        :param ip_data: 接口返回的IP数据
        :param filename: 文件名
        """
        if "error" not in ip_data and 'ip_list' in ip_data:
            with open(filename, 'w') as f:
                json.dump({
                    "update_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "ip_list": ip_data['ip_list']
                }, f, indent=2)
            print(f"✅ IP列表已保存到文件: {filename}")


# 使用示例
if __name__ == "__main__":
    # 你的access_token（需要先获取有效的access_token）
    ACCESS_TOKEN = "95_rRUMnw_xgZPCM1s5y3aQ07cHmDwbnDRYjpQAti8ejzNxrw2y3y-uE9ScYWCRJxqcGUODqg2_JKJhReqkBhj7TCZCOME00R4rBkOORPPTh9TAoa1icgU0zI77kx4HVMeAFAKYP"  # 替换为你的access_token

    # 创建IP管理器实例
    ip_manager = WeChatIPManager(ACCESS_TOKEN)

    print("=== 获取微信API服务器IP地址 ===")
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)

    # 获取IP列表
    print("正在获取微信API服务器IP地址...")
    ip_data = ip_manager.get_wechat_api_ips()

    # 显示结果
    print("\n获取结果:")
    print("-" * 50)
    print(ip_manager.format_ip_list(ip_data))

    # 保存到文件（可选）
    if "error" not in ip_data:
        ip_manager.save_ips_to_file(ip_data)

    print("-" * 50)
    print(f"完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")