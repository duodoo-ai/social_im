# -*- coding: utf-8 -*-
"""
@Time    : 2025/08/02 16:33
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@Mobile  ：18951631470
@Website: http://www.duodoo.tech
"""
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError, AccessDenied
from odoo.modules.registry import Registry
import requests, json
import logging
from typing import Optional, Dict, Any
from odoo.exceptions import MissingError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    wechat_user_id = fields.Char(string='微信用户ID', copy=False, index=True)
    wechat_unionid = fields.Char(string='微信UnionID', copy=False, index=True)
    wechat_openid = fields.Char(string='微信OpenID', copy=False, index=True)
    wechat_nickname = fields.Char(string='微信昵称')
    wechat_sex = fields.Selection([
        ('0', '未知'),
        ('1', '男性'),
        ('2', '女性')
    ], string='微信性别')
    wechat_city = fields.Char(string='微信城市')
    wechat_province = fields.Char(string='微信省份')
    wechat_country = fields.Char(string='微信国家')
    wechat_headimgurl = fields.Char(string='微信头像URL')
    wechat_privilege = fields.Text(string='微信特权信息')

    # 添加密码字段的覆盖
    password = fields.Char(default='wechat', groups="base.group_user")  # 设置为不可见

    def _check_credentials(self, password, env):
        # 如果password是一个字典，并且包含type字段为'wechat'，则跳过密码检查
        if isinstance(password, dict) and password.get('type') == 'wechat':
            # 这里可以添加额外的验证，比如检查openid等
            # 因为我们已经在auth_wechat方法中验证过用户，所以这里直接返回True
            return True
        return super(ResUsers, self)._check_credentials(password, env)

    def fix_all_wechat_nicknames(self):
        """修复所有微信用户的昵称乱码问题"""
        users = self.search([('wechat_nickname', '!=', False)])

        for user in users:
            original = user.wechat_nickname
            fixed = self.fix_wechat_nickname(original)

            if fixed != original:
                user.write({'wechat_nickname': fixed, 'name': fixed})
                _logger.info("修复用户 %s 昵称: %s → %s", user.id, original, fixed)

    def fix_all_wechat_nicknames(self):
        """修复所有微信用户的昵称乱码问题"""
        users = self.search([('wechat_nickname', '!=', False)])

        for user in users:
            original = user.wechat_nickname
            fixed = self.fix_wechat_nickname(original)

            if fixed != original:
                user.write({'wechat_nickname': fixed})
                # 同时更新用户名称（可选）
                if not user.name or user.name == original:
                    user.write({'name': fixed})
                _logger.info("修复用户 %s 昵称: %s → %s", user.id, original, fixed)

    @api.model
    def fix_wechat_nickname(self, original_nickname: Optional[str]) -> str:
        """
        修复微信昵称的编码问题，支持更广泛的字符集和更稳健的异常处理。
        针对双重编码乱码问题优化处理流程
        :param original_nickname: 原始昵称字符串
        :return: 修复后的昵称字符串
        """
        if not original_nickname:
            return _("微信用户")

        try:
            # 获取乱码字符配置
            garbled_chars = self._get_garbled_chars()

            # 第一步：处理常见双重编码问题（优先处理）
            if isinstance(original_nickname, str):
                # 检测双重编码特征（Latin-1存储的UTF-8字节）
                if any(char in original_nickname for char in garbled_chars):
                    try:
                        fixed_bytes = original_nickname.encode('latin1')
                        fixed_nickname = fixed_bytes.decode('utf-8')
                        _logger.debug("双重编码修复: %s -> %s", original_nickname, fixed_nickname)
                        return fixed_nickname
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        # 尝试Windows-1252编码
                        try:
                            fixed_bytes = original_nickname.encode('windows-1252')
                            fixed_nickname = fixed_bytes.decode('utf-8')
                            _logger.debug("Windows-1252修复: %s -> %s", original_nickname, fixed_nickname)
                            return fixed_nickname
                        except (UnicodeEncodeError, UnicodeDecodeError):
                            pass

            # 第二步：处理字节数据
            if isinstance(original_nickname, bytes):
                # 尝试多种编码解码
                encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'latin1', 'iso-8859-1', 'windows-1252']
                for encoding in encodings_to_try:
                    try:
                        return original_nickname.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                _logger.warning("无法解码微信昵称字节数据: %s", original_nickname)
                return _("微信用户")

            # 第三步：处理字符串的其他乱码情况
            if isinstance(original_nickname, str):
                # 尝试清理无效字节
                try:
                    # 先尝试UTF-8清理
                    cleaned = original_nickname.encode('utf-8', 'ignore').decode('utf-8')
                    if cleaned != original_nickname:
                        _logger.debug("UTF-8清理: %s -> %s", original_nickname, cleaned)
                        return cleaned

                    # 如果无效，尝试GBK清理
                    cleaned = original_nickname.encode('gbk', 'ignore').decode('gbk', 'ignore')
                    if cleaned != original_nickname:
                        _logger.debug("GBK清理: %s -> %s", original_nickname, cleaned)
                        return cleaned
                except UnicodeError:
                    pass

                # 如果包含无法解码的字符，尝试替换
                try:
                    return original_nickname.encode('utf-8', 'replace').decode('utf-8')
                except UnicodeError:
                    pass

            # 第四步：处理其他类型
            if not isinstance(original_nickname, (str, bytes)):
                try:
                    return str(original_nickname)
                except Exception:
                    pass

            # 所有尝试失败后返回原始值
            return original_nickname

        except Exception as e:
            _logger.error("修复微信昵称时发生异常: %s", str(e), exc_info=True)
            return _("微信用户")

    def _get_garbled_chars(self):
        """获取配置的乱码字符列表"""
        try:
            # 获取微信配置
            config = self.env['wechat.sso.config'].sudo().get_active_config()
            if config and config.garbled_chars:
                # 分割并清理字符
                return [char.strip() for char in config.garbled_chars.split(',') if char.strip()]
        except Exception as e:
            _logger.error("获取乱码配置失败: %s", str(e))

        # 默认乱码字符
        return ['Ã', 'Â', 'â', 'é­å½¬', '€', 'ç', '¢', '£', '¥']

    def auth_wechat(self, provider, code, params):
        # 需要包含以下关键步骤：
        # 1. 通过code获取access_token
        # 2. 获取用户openid
        # 3. 查询或创建关联用户
        # 4. 返回用户对象
        if provider != 'wechat':
            _logger.error("认证提供者非微信: %s", provider)
            return False

        # 获取微信配置
        config = self.env['wechat.sso.config'].sudo().get_active_config()
        if not config:
            _logger.error("没有找到生效的微信配置")
            return False

        try:
            # 1. 通过code获取access_token和openid
            token_url = "https://api.weixin.qq.com/sns/oauth2/access_token"
            token_params = {
                'appid': config.app_id,
                'secret': config.app_secret,
                'code': code,
                'grant_type': 'authorization_code'
            }

            response = requests.get(token_url, params=token_params, timeout=10)
            response.raise_for_status()
            result = response.json()

            if 'errcode' in result and result['errcode'] != 0:
                _logger.error("微信认证失败: %s", result.get('errmsg', '未知错误'))
                return False

            access_token = result['access_token']
            openid = result['openid']
            wechat_user_id = openid  # 使用openid作为微信用户ID

            # 2. 获取用户信息
            user_info_url = "https://api.weixin.qq.com/sns/userinfo"
            user_info_params = {
                'access_token': access_token,
                'openid': openid,
                'lang': 'zh_CN'
            }

            response = requests.get(user_info_url, params=user_info_params, timeout=10)
            response.raise_for_status()
            user_info = response.json()
            _logger.info("获取用户信息: %s", user_info)

            if 'errcode' in user_info and user_info['errcode'] != 0:
                _logger.error("获取微信用户信息失败 (errcode: %s): %s", user_info.get('errcode'),
                              user_info.get('errmsg', '未知错误'))
                return False

            # 3. 准备用户数据
            # 修复昵称编码
            fixed_nickname = self.fix_wechat_nickname(user_info.get('nickname'))
            user_vals = {
                'wechat_unionid': user_info.get('unionid'),
                'wechat_openid': openid,
                'wechat_nickname': fixed_nickname,
                'wechat_sex': str(user_info.get('sex', '0')),  # 确保是字符串
                'wechat_city': user_info.get('city'),
                'wechat_province': user_info.get('province'),
                'wechat_country': user_info.get('country'),
                'wechat_headimgurl': user_info.get('headimgurl'),
                'wechat_privilege': json.dumps(user_info.get('privilege', []), ensure_ascii=False) if user_info.get(
                    'privilege') else None,
            }

            # 4. 查找或创建用户
            domain = [
                '|',  # 使用OR操作
                ('wechat_user_id', '=', wechat_user_id),
                ('wechat_openid', '=', openid)  # 同时检查openid，确保唯一性
            ]
            if user_info.get('unionid'):
                domain = ['|'] + domain + [('wechat_unionid', '=', user_info.get('unionid'))]

            user = self.sudo().search(domain, limit=1, order='id DESC')  # 取最新的一条

            db_name = self.env.cr.dbname

            if user:
                if len(user) > 1:
                    _logger.warning("找到多个匹配的微信用户 (openid: %s, user_id: %s), 将更新第一个找到的用户。", openid,
                                    wechat_user_id)
                    user = user[0]

                # 创建新的数据库连接和超级用户环境
                registry = Registry(db_name)
                with registry.cursor() as new_cr:
                    new_env = api.Environment(new_cr, SUPERUSER_ID, {})
                    user_in_su_env = new_env['res.users'].browse(user.id)

                    # 更新用户信息
                    user_in_su_env.write(user_vals)
                    new_cr.commit()
                _logger.info("更新微信用户信息: %s (用户ID: %s)", wechat_user_id, user.id)

            elif config.auto_create_user:
                if not config.default_user_group:
                    raise ValidationError(_("启用自动创建用户时必须在微信配置中设置默认用户组"))

                # 自动创建新用户
                user_login = f"wechat_{wechat_user_id}"[:64]  # 确保登录名不超长
                user_name = fixed_nickname or f"微信用户_{wechat_user_id[:8]}"

                create_vals = {
                    'login': user_login,
                    'name': user_name,
                    'company_id': config.company_id.id,
                    'company_ids': [(6, 0, [config.company_id.id])],
                    'active': True,
                    **user_vals,  # 合并微信信息
                    'wechat_user_id': wechat_user_id,
                    'groups_id': [(6, 0, [config.default_user_group.id])],  # 使用配置中的用户组
                }
                # 创建新的数据库连接和超级用户环境
                db_name = self.env.cr.dbname
                registry = Registry(db_name)
                with registry.cursor() as new_cr:
                    new_env = api.Environment(new_cr, SUPERUSER_ID, {})
                    user = new_env['res.users'].create(create_vals)
                    new_cr.commit()
                _logger.info("创建新微信用户: %s (用户ID: %s)", wechat_user_id, user.id)
            else:
                _logger.warning("微信用户 %s 不存在且不允许自动创建", wechat_user_id)
                return False

            return user

        except requests.exceptions.Timeout:
            _logger.error("获取微信访问令牌或用户信息请求超时")
            return False
        except requests.exceptions.ConnectionError:
            _logger.error("网络连接错误，无法访问微信API")
            return False
        except requests.exceptions.RequestException as e:
            _logger.error("微信认证网络请求异常: %s", str(e))
            return False
        except json.JSONDecodeError as e:
            _logger.error("解析微信API返回的JSON数据失败: %s", str(e))
            return False
        except Exception as e:
            _logger.exception("微信认证过程中发生未预期的异常: %s", str(e))
            return False
