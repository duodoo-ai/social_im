# -*- coding: utf-8 -*-
"""
@Time    : 2024/11/26 10:26
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@mobile  : 18951631470
"""
import logging
import pymssql
from .eshr_conn import *
from odoo import fields, models, api
_logger = logging.getLogger(__name__)


class EShrEmployee(models.Model):
    _inherit = 'hr.employee'

    fid = fields.Char(string='e-shr FID')   # 职工唯一ID
    fnum = fields.Char(string='e-shr Employee Code')  # 职工编码

    def cron_employee_from_shr(self):
        """
        Complete SHR synchronization of employee information synchronization
        完成SHR同步职工信息同步
        """
        _obj = self.env['hr.employee']
        a_obj = self.env['hr.department']
        rel_obj = self.env['res.partner']
        user_obj = self.env['res.users']
        job_obj = self.env['hr.job']
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
            select t.*, thpp.FImageData from (
                SELECT
                    distinct ps.fid as FPersonID,
                    ps.fnumber employee_code,	--职工编码
                    ps.fname_l2 real_name,	--真实姓名
                    ps.FIDCardNO IDNO,	--身份证号
                    ad.fid department_ID,	--部门ID
                    ad.fnumber department_code,	--部门编码
                    ad.fname_l2 department_name,	--部门名称
                    ps.fcell phone_no,	--手机号
                    ps.FEMail email,	--邮件
                    ps.FBirthday birthday,	--出生日期
                    pm.FBeginDate joined_date,	--入司日期
                    case 
                    	when ps.FGender=1 then 'male'
                    	when ps.FGender=2 then 'female'
                    	else 'other'
                    end gender,	--性别
                    'single' as marital,	--婚姻状况
                    cpos.fname_l2 position,	--职位
                    case 
                    	when pt.fname_l2 in ('正式员工', '试用员工', '实习') then '1' else '0'
                    end 状态,	--状态
                    ad.fparentid 上级部门编码,	  --上级部门编码
                    ps.FFullNamePingYin 拼音,	--拼音
                    cpos.fid position_id,	--职位ID
                    pps.fid parent_fid,	-- 上级职工编码
					pps.fname_l2 parent_name   -- 上级职工姓名
                FROM
                    t_BD_person ps	
                LEFT JOIN T_HR_BDEmployeeType pt on pt.fid = ps.femployeetypeid
                LEFT JOIN t_Org_Positionmember pm ON pm.fpersonid = ps.fid AND pm.fisprimary = 1
                LEFT JOIN t_org_position cpos ON cpos.fid = pm.fpositionid
                LEFT JOIN t_Org_Positionhierarchy ph ON ph.fchildid = cpos.fid
                left join t_org_admin ad on ad.fid = cpos.fadminorgunitid
                LEFT JOIN t_Org_Position ppos ON ppos.fid = ph.fparentid
                LEFT JOIN t_org_positionmember ppm ON ppm.fpositionid = ppos.fid
                LEFT JOIN t_bd_person pps ON pps.fid = ppm.fpersonid
                LEFT JOIN t_ORG_admin PAD ON PAD.fid = ad.fparentid
                WHERE ps.FID IS NOT NULL 
                ) t
                LEFT JOIN T_HR_PersonPhoto thpp ON thpp.FPersonID = t.FPersonID 
                ORDER BY department_code DESC , employee_code
        """
        shr_cursor.execute(sql)
        shr_records = shr_cursor.fetchall()
        if len(shr_records) > 0:
            i = 0
            for r in shr_records:    # 遍历写入数据
                login = r[7] or r[1] or r[16]
                if login in ('0', '#REF!'):
                    login = r[7] or r[1] or r[16]
                sql = """select id from res_users where login = '%s' and active = false """
                sql = sql % login
                try:
                    self._cr.execute(sql)
                    text = self._cr.fetchall()
                except Exception as e:
                    _logger.error(f'User Search Error: {e}')
                    self._cr.rollback()
                    text = False
                bUserCreated = False
                user_record = self.env['res.users']
                if text:
                    bUserCreated = True
                    if bUserCreated:
                        record_u = user_obj.search(['&', ('login', '=', login), ('active', '=', False)])
                        if record_u:
                            record_u.write({'active': True})  # 用户
                        # 职工激活
                        _obj.search(['&', ('user_id', '=', record_u.id), ('active', '=', False)]).write({'active': True})
                        # 联系人激活
                        rel_obj.search(['&', ('user_id', '=', record_u.id), ('active', '=', False)]).write({'active': True})
                dept_ids = a_obj.sudo().search([('name', '=', r[6])])
                if not bUserCreated:
                    rel_records = rel_obj.search([('employee', '=', True), '|', ('name', '=', r[2]), ('ref', '=', r[1])])  # 联系人表
                    pv = {
                        'name': r[2],
                        'ref': r[1],
                        'employee': True,
                        'email': r[8],
                        'mobile': r[7],
                        'phone': False,
                        'lang': 'zh_CN',
                        'type': 'contact',
                        'is_company': False,
                        'active': True,
                        'company_id': dept_ids and dept_ids[0].company_id.id or 1,
                        'tz': 'Asia/Shanghai',
                        'function': r[13],
                    }
                    if not rel_records:
                        rel_record = rel_obj.create(pv)
                    else:
                        rel_records.write(pv)
                        rel_record = rel_records[0]  # 定义用户登录信息
                    user_records = user_obj.search([('login', '=', login)])
                    if not user_records:
                        uv = {
                            'name': r[2],
                            'active': True,
                            'login': login,
                            'email': r[8],
                            'password': '098iop2025',
                            'partner_id': rel_record.id,
                            'company_id': dept_ids and dept_ids[0].company_id.id or 1,
                            'company_ids': [(6, 0, [dept_ids and dept_ids[0].company_id.id or 1])],
                            'notification_type': 'email',
                            'odoobot_state': 'not_initialized',
                            'tz': 'Asia/Shanghai',
                            # 'groups_id': 1,
                        }
                        user_record = user_obj.create(uv)
                    else:
                        user_record = user_records[0]
                # -----------------------------
                job_id = job_obj.search([('fid', '=', r[17])])      # 定义工作岗位
                pv = {
                    'name': r[13] or '职员',
                    'fid': r[17],
                }
                if job_id:
                    job_id.write(pv)
                else:
                    job_obj.create(pv)
                # -----------------------------
                _record = _obj.search(['|', ('name', '=', r[7]), ('fid', '=', r[0])])
                lead_ids = _obj.search([('fid', '=', r[18])])    # 定义职工信息
                pv = {
                    'name': r[2],
                    'fid': r[0],
                    'fnum': r[1],
                    'department_id': dept_ids and dept_ids[0].id or False,
                    'company_id': dept_ids and dept_ids[0].company_id.id or 1,
                    'user_id': user_record.id or False,
                    'work_email': r[8],
                    'mobile_phone': r[7],
                    'work_phone': r[7],
                    'identification_id': r[3],
                    'birthday': r[9],
                    'work_location_id': False,
                    'address_id': 1,
                    'job_id': job_id.id or False,
                    'job_title': r[13] or False,
                    'parent_id': lead_ids and lead_ids[0].id or False,
                    'gender': r[11] or False,
                    'marital': r[12] ,
                    'country_id': 48,
                    'country_of_birth': 48,
                    'active': True,
                }
                # hr_employee 对象处理
                if _record:
                    try:
                        _record.write(pv)
                    except Exception as e:
                        _logger.error('Update hr.employee Abnormal.Employee Name:"' + r[1] + '".' + str(e))
                else:
                    try:
                        _obj.create(pv)
                    except Exception as e:
                        _logger.error('Create hr.employee Abnormal.Employee Name:"' + r[1] + '".' + str(e) + '. ERROR AT 336')
                if r[8]:
                    rel_obj.with_context(active_test=True, tracking_disable=True). \
                        search([('employee', '=', True), '|', ('name', '=', r[1]), ('ref', '=', r[2])]).write(
                        {'active': False})
                    user_obj.with_context(active_test=True, tracking_disable=True). \
                        search(['|', ('name', '=', r[1]), ('login', '=', login)]).write({'active': False})
                i += 1
                if i % 100 == 0:
                    self.env.cr.commit()
            self.env.cr.commit()
