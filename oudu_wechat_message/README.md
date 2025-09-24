1、其他模块可以这样调用微信消息服务：
# 在其他模块中使用微信消息服务
class SomeOtherModel(models.Model):
    _name = 'some.other.model'
    
    def some_business_method(self):
        # 获取微信消息服务
        wechat_service = self.env['wechat.notification.service']
        
        # 方式1：使用完整参数创建并发送消息
        message_vals = {
            'report_title': '新商机通知',
            'report_type': '商机报告',
            'report_target': '全体用户',
            'report_content': '发现新的商机机会，请及时查看处理...',
            'redirect_url': '/web#id=123&model=crm.lead&view_type=form',
            'message_title': '商机提醒'
        }
        
        success, message_id = wechat_service.create_and_send_message(message_vals)
        
        # 方式2：使用快捷方法
        wechat_service.send_quick_notification(
            title='系统提醒',
            content='您的订单已处理完成',
            message_type='system_notification',
            redirect_url='/web'
        )


关键特性
1. 独立的公共服务模块
    不与其他业务模块强耦合
    
    提供清晰的公共调用接口
    
    支持多种调用方式满足不同需求

2. 完整的消息生命周期管理
   
    消息创建、发送、追踪、统计全流程

       详细的发送状态和错误处理
        
       支持消息重试机制

3. 安全的用户认证流程
    集成微信SSO自动登录
    
    严格的权限控制
    
    安全的跳转链接处理

4. 企业级代码质量
    完整的类型注解和文档字符串

    全面的异常处理机制

    符合Odoo 18开发标准

5. 运营支持功能
   详细的消息发送统计

    用户行为追踪分析

    可视化报表和监控