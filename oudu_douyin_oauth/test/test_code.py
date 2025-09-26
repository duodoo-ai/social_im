import requests

# 替换为你实际获取到的 access_token
access_token = "96_qfIbdre9aSscJ5QOV66GIPZgv3_xRt0ZXPOeowdQIlOsJuZpsMaoQFi5GzXPdl3DZjwyUnn_Umv1gtL88kSC0Jj2L3TPd6NxYEUOWUDcDxJPF_qA0AA8c7hhUpsDWXfAGAWPQ"

url = f"https://api.weixin.qq.com/cgi-bin/user/get?access_token={access_token}"

try:
    response = requests.get(url)
    data = response.json()

    if "errcode" in data and data["errcode"] != 0:
        print(f"❌ 获取用户列表失败: [{data['errcode']}] {data['errmsg']}")
    else:
        total = data.get("total", 0)  # 关注该公众账号的总用户数
        count = data.get("count", 0)  # 拉取的OPENID个数，最大值为10000
        openid_list = data.get("data", {}).get("openid", [])  # 列表内是用户的OpenID
        next_openid = data.get("next_openid", "")  # 获取下一个用户的OPENID，用于分批拉取

        print(f"✅ 成功获取用户列表!")
        print(f"   总关注用户数: {total}")
        print(f"   本次拉取数量: {count}")
        print(f"   下一个起始OpenID: {next_openid}")
        print(f"   前几个OpenID示例: {openid_list[:5]}")  # 打印前5个，避免刷屏

except Exception as e:
    print(f"❌ 请求过程中发生异常: {str(e)}")