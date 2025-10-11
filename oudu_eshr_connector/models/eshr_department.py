# -*- coding: utf-8 -*-
"""
@Time    : 2024/12/05 8:20
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@mobile  : 18951631470
"""
import logging
import pymssql
from odoo import fields, models, api
from .eshr_conn import *
_logger = logging.getLogger(__name__)


class EShrDepartment(models.Model):
    _inherit = 'hr.department'

    fid = fields.Char(string='e-shr FID')   # 部门唯一ID
    fnum = fields.Char(string='e-shr Department Code')  # 部门编码
    level = fields.Char(string='e-shr Level')  # 部门层级

    def cron_org_from_shr(self):
        # 金蝶e - shr组织架构同步
        # Kingdee e-shr Organizational Synchronization
        org_obj = self.with_user(2).env['hr.department']
        try:
            ms_conn = pymssql.connect(
                host="%s" % host,
                user="%s" % user,
                password="%s" % password,
                database="%s" % database,
                charset="utf8")
            shr_cursor = ms_conn.cursor()  # 输出从SHR拿回来的记录集
        except Exception as e:
            # 连接金蝶e-shr数据库失败，请检查网络连接是否正常! 更多可能是你的网络已断开连接！
            # 连接目标地址
            # 错误详情
            _logger.error('Failed to connect to Kingdee e-shr database, '
                          'please check if the network connection is normal! '
                          'More likely, your network has been disconnected!'
                          '==> Connect to the target address：{} '
                          '==> Error details：{} '
                          .format(host, e))
            return
        sql = """
            SELECT
                fid,
                fname_l2 AS fname,
                fnumber,
                fparentid,
                flevel - 2 
            FROM
                T_ORG_Admin 
            WHERE
                fissealup = 0 
            ORDER BY
                fnumber
        """
        shr_cursor.execute(sql)
        shr_records = shr_cursor.fetchall()
        if len(shr_records) > 0:
            # 遍历写入数据
            # Traverse and write data
            for line in shr_records:
                # 写入组织数据
                # Write organizational data
                fid = org_obj.search([('fid', '=', line[0])])
                # 获取父部门ID（如果不是根部门）
                parent_id = False
                if line[3]:  # 如果有父部门fid
                    parent_dept = org_obj.search([('fid', '=', line[3])], limit=1)
                    parent_id = parent_dept.id if parent_dept else False
                uv = {
                    'fid': line[0],  # 组织唯一标识码  Unique code organization
                    'name': line[1] or False,
                    'fnum': line[2] or False,
                    'parent_id': parent_id,
                    'level': line[4]
                }
                if line[2] == '1':
                    uv['parent_id'] = False
                if fid:
                    fid.write(uv)
                else:
                    org_obj.create(uv)
            self.env.cr.commit()
