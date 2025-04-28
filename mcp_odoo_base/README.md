# MCP Odoo Base API 接口文档

## 模块说明
MCP Odoo Base 是一个基础模块，提供了一系列RESTful API接口，用于与Odoo系统进行交互。通过这些接口，外部系统可以方便地访问和操作Odoo中的业务数据。

## 基本信息

- 基础URL: `http://your-odoo-server:8069`
- 认证方式: API密钥 (在请求头中使用 `X-API-Key`)
- 响应格式: JSON
- 编码方式: UTF-8

## 通用说明

### 请求头格式
```http
Content-Type: application/json
X-API-Key: your-api-key
```

### 标准响应格式
```json
{
    "status": "success|error",
    "data": {}, // 成功时返回的数据
    "message": "错误信息" // 失败时的错误描述
}
```

## 接口列表

### 1. 获取可访问的业务对象列表

- **接口**: `/api/v1/models`
- **方法**: GET
- **描述**: 获取当前API密钥允许访问的所有业务对象列表

**响应示例**:
```json
{
    "status": "success",
    "data": [
        {
            "model": "res.partner",
            "description": "联系人"
        },
        {
            "model": "res.users",
            "description": "用户"
        }
    ]
}
```

### 2. 获取模型元数据

- **接口**: `/api/v1/metadata/<model>`
- **方法**: GET
- **描述**: 获取指定模型的详细元数据信息，包括字段定义等

**示例**: `/api/v1/metadata/res.partner`

**响应示例**:
```json
{
    "status": "success",
    "data": {
        "model": {
            "name": "res.partner",
            "description": "联系人",
            "table": "res_partner",
            "inherit": ["mail.thread", "mail.activity.mixin"]
        },
        "fields": {
            "name": {
                "type": "char",
                "string": "名称",
                "required": true,
                "readonly": false
            }
        }
    }
}
```

### 3. 搜索记录

- **接口**: `/api/v1/<model>/search_read`
- **方法**: POST
- **描述**: 搜索并读取指定模型的记录

**请求体示例**:
```json
{
    "params": {
        "domain": [["is_company", "=", true]],
        "fields": ["name", "email", "phone"],
        "limit": 10
    }
}
```

**响应示例**:
```json
{
    "status": "success",
    "data": [
        {
            "id": 1,
            "name": "小海智能",
            "email": "contact@xiaohai.com",
            "phone": "12345678901"
        }
    ]
}
```

### 4. 创建记录

- **接口**: `/api/v1/object/create`
- **方法**: POST
- **描述**: 创建新的业务对象记录

**请求体示例**:
```json
{
    "model": "res.partner",
    "values": {
        "name": "小海智能",
        "email": "contact@xiaohai.com",
        "phone": "12345678901"
    }
}
```

**响应示例**:
```json
{
    "status": "success",
    "data": {
        "id": 1,
        "name": "小海智能",
        "url": "http://your-odoo-server:8069/web/action?model=res.partner&id=1&process_type=edit"
    }
}
```

### 5. 更新记录

- **接口**: `/api/v1/object/update`
- **方法**: POST
- **描述**: 更新现有业务对象记录

**请求体示例**:
```json
{
    "model": "res.partner",
    "id": 1,
    "values": {
        "name": "小海智能科技",
        "phone": "12345678902"
    }
}
```

**响应示例**:
```json
{
    "status": "success",
    "data": {
        "id": 1,
        "name": "小海智能科技",
        "url": "http://your-odoo-server:8069/web/action?model=res.partner&id=1&process_type=edit"
    }
}
```

### 6. 获取对象链接

- **接口**: `/api/v1/object/link`
- **方法**: POST
- **描述**: 获取业务对象的Web访问链接

**请求体示例**:
```json
{
    "model": "res.partner",
    "id": 1,
    "process_type": "edit",
    "context": {
        "default_name": "小海智能",
        "default_email": "contact@xiaohai.com"
    }
}
```

**响应示例**:
```json
{
    "status": "success",
    "data": {
        "url": "http://your-odoo-server:8069/web/action?model=res.partner&id=1&process_type=edit&context={...}"
    }
}
```

### 7. 知识库搜索

- **接口**: `/api/v1/knowledge/search`
- **方法**: POST
- **描述**: 在知识库中搜索文档

**请求体示例**:
```json
{
    "keywords": ["解决方案", "智能制造"]
}
```

**响应示例**:
```json
{
    "status": "success",
    "data": [
        {
            "id": 1,
            "name": "智能制造解决方案",
            "content": "文档内容..."
        }
    ]
}
```

## 错误处理

所有接口在发生错误时都会返回统一格式的错误响应：

```json
{
    "status": "error",
    "message": "具体的错误信息"
}
```

常见错误类型：
1. `Invalid API key`: API密钥无效
2. `Access to model {model} is not allowed`: 无权访问指定模型
3. `Record {id} not found in {model}`: 记录不存在
4. `Invalid JSON data`: JSON数据格式错误

## 注意事项

1. 所有请求都需要在header中携带有效的API密钥
2. 返回的URL可以直接在浏览器中打开，会自动跳转到Odoo的Web界面
3. 创建和更新操作会返回记录的访问URL
4. 搜索接口默认最大返回80条记录
5. 知识库搜索支持多个关键词的组合查询

## 安全建议

1. 妥善保管API密钥，不要泄露给未授权的人员
2. 建议使用HTTPS协议进行API调用
3. 定期更换API密钥
4. 在生产环境中设置适当的访问控制策略

## 开发环境配置

### 依赖要求
- Python 3.10+
- Odoo 18.0
- 其他依赖请参考 `__manifest__.py` 文件

### 安装步骤
1. 将模块复制到Odoo的addons目录下
2. 更新模块列表
3. 安装模块
4. 在系统参数中配置API密钥

### 测试
模块包含完整的测试用例，可以通过以下命令运行测试：
```bash
python xiaohai_addons/mcp_odoo_base/tests/test_mcp_api.py
```

## 贡献指南
1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 版本历史
- v1.0.0 (2024-03-18)
  - 初始版本发布
  - 实现基础API接口
  - 添加完整的测试用例
  - 添加详细的接口文档

## 许可证
本项目采用 MIT 许可证 - 详见 LICENSE 文件

## 联系方式
- 项目维护者：小海智能
- 邮箱：contact@xiaohai.com
- 项目链接：[GitHub Repository](https://github.com/xiaohai/mcp_odoo_base)

## 致谢
感谢所有为这个项目做出贡献的开发者！ 