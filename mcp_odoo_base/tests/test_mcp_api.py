import requests
import json
import unittest
import re

class TestMCPAPI(unittest.TestCase):
    """MCP API测试类"""

    def setUp(self):
        """测试前的准备工作"""
        self.base_url = "http://127.0.0.1:8069"
        self.api_key = "2f79657a-8582-47b1-a3e6-29553841984b"  # 替换为实际的API密钥
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }

    def _print_response(self, response, message=""):
        """打印响应信息"""
        print(f"\n=== {message} ===")
        print(f"状态码: {response.status_code}")
        print(f"响应头: {response.headers}")
        print(f"响应内容: {response.text}")
        if response.status_code == 200:
            try:
                print(f"JSON数据: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {str(e)}")

    def test_01_get_allowed_models(self):
        """测试获取允许访问的业务对象列表"""
        print("\n测试获取允许访问的业务对象列表")
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/models",
                headers=self.headers,
                verify=False
            )
            self._print_response(response, "允许访问的业务对象列表")
            
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data['status'], 'success')
                self.assertIsInstance(data['data'], list)
                # 验证返回的模型列表中包含res.users和res.partner
                model_names = [m['model'] for m in data['data']]
                self.assertIn('res.users', model_names)
                self.assertIn('res.partner', model_names)
        except requests.RequestException as e:
            self.fail(f"请求异常: {str(e)}")

    def test_02_get_model_metadata(self):
        """测试获取模型元数据"""
        print("\n测试获取模型元数据")
        try:
            # 测试允许访问的模型
            response = requests.get(
                f"{self.base_url}/api/v1/metadata/res.users",
                headers=self.headers,
                verify=False
            )
            self._print_response(response, "res.users模型元数据")
            
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data['status'], 'success')
                self.assertIn('model', data['data'])
                self.assertIn('fields', data['data'])
                
                # 验证模型信息
                model_info = data['data']['model']
                self.assertEqual(model_info['name'], 'res.users')
                self.assertEqual(model_info['description'], 'User')
                self.assertIn('table', model_info)
                self.assertIn('inherit', model_info)
                
                # 验证字段信息
                fields = data['data']['fields']
                self.assertIsInstance(fields, dict)
                # 验证一些必要的字段
                self.assertIn('login', fields)
                self.assertIn('name', fields)
                self.assertIn('partner_id', fields)
                
                # 验证字段属性
                login_field = fields['login']
                self.assertEqual(login_field['type'], 'char')
                self.assertEqual(login_field['string'], 'Login')
                self.assertTrue(login_field['required'])

            # 测试不允许访问的模型
            response = requests.get(
                f"{self.base_url}/api/v1/metadata/ir.model",
                headers=self.headers,
                verify=False
            )
            self._print_response(response, "ir.model模型元数据(应该被拒绝)")
            
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data['status'], 'error')
                self.assertIn('not allowed', data['message'])
        except requests.RequestException as e:
            self.fail(f"请求异常: {str(e)}")

    def test_03_search_read(self):
        """测试查询记录"""
        print("\n测试查询记录")
        try:
            # 测试允许访问的模型
            payload = {
                "params": {
                    "domain": [["active", "=", True]],
                    "fields": ["name", "login", "mcp_enabled"]
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/res.users/search_read",
                headers=self.headers,
                json=payload,
                verify=False
            )
            self._print_response(response, "查询res.users记录")
            
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data['status'], 'success')
                self.assertIsInstance(data['data'], list)

            # 测试不允许访问的模型
            response = requests.post(
                f"{self.base_url}/api/v1/ir.model/search_read",
                headers=self.headers,
                json=payload,
                verify=False
            )
            self._print_response(response, "查询ir.model记录(应该被拒绝)")
            
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data['status'], 'error')
                self.assertIn('not allowed', data['message'])
        except requests.RequestException as e:
            self.fail(f"请求异常: {str(e)}")

    def test_04_invalid_api_key(self):
        """测试无效的API密钥"""
        print("\n测试无效的API密钥")
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": "invalid-api-key"
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/models",
                headers=headers,
                verify=False
            )
            self._print_response(response, "使用无效API密钥")
            
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data['status'], 'error')
                self.assertEqual(data['message'], 'Invalid API key')
        except requests.RequestException as e:
            self.fail(f"请求异常: {str(e)}")

    def test_05_knowledge_search(self):
        """测试知识库检索"""
        print("\n测试知识库检索")
        
        try:
            # 测试正常搜索
            payload = {
                "keywords": ["解决方案", "智能智造"]
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/knowledge/search",
                headers=self.headers,
                json=payload,
                verify=False
            )
            self._print_response(response, "正常搜索知识库")
            
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data['status'], 'success')
                self.assertIsInstance(data['data'], list)
                # 验证返回的文档结构
                if data['data']:
                    doc = data['data'][0]
                    self.assertIn('id', doc)
                    self.assertIn('name', doc)
                    self.assertIn('content', doc)

            # 测试空关键词
            payload = {
                "keywords": []
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/knowledge/search",
                headers=self.headers,
                json=payload,
                verify=False
            )
            self._print_response(response, "空关键词搜索")
            
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data['status'], 'error')
                self.assertEqual(data['message'], '请提供搜索关键词')

            # 测试无效的JSON数据
            response = requests.post(
                f"{self.base_url}/api/v1/knowledge/search",
                headers=self.headers,
                data="invalid json",
                verify=False
            )
            self._print_response(response, "无效JSON数据")
            
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data['status'], 'error')
                self.assertEqual(data['message'], '无效的JSON数据')

            # 测试中文关键词搜索
            payload = {
                "keywords": ["测试文档", "知识库"]
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/knowledge/search",
                headers=self.headers,
                json=payload,
                verify=False
            )
            self._print_response(response, "中文关键词搜索")
            
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data['status'], 'success')
                self.assertIsInstance(data['data'], list)

        except requests.RequestException as e:
            self.fail(f"请求异常: {str(e)}")

    def test_06_get_object_link(self):
        """测试获取对象链接"""
        print("\n测试获取对象链接")

        # 测试获取合法对象链接
        print("\n=== 获取合法对象链接 ===")
        payload = {
            "model": "res.partner",
            "id": 1,
            "process_type": "edit",
            "context": {}
        }
        response = requests.post(
            f"{self.base_url}/api/v1/object/link",
            headers=self.headers,
            json=payload,
            verify=False
        )
        print(f"状态码: {response.status_code}")
        print(f"响应头: {response.headers}")
        print(f"响应内容: {response.text}")
        
        try:
            json_data = response.json()
            print(f"JSON数据: {json.dumps(json_data, indent=2, ensure_ascii=False)}")
            
            self.assertEqual(response.status_code, 200, "状态码应为200")
            self.assertEqual(json_data["status"], "success", "响应状态应为success")
            self.assertIn("url", json_data["data"], "响应应包含url字段")
            self.assertTrue(json_data["data"]["url"].startswith(self.base_url), "返回的URL应以base_url开头")
            
            # 验证URL可访问性
            url = json_data["data"]["url"]
            print(f"\n=== 验证URL可访问性 ===")
            print(f"访问URL: {url}")
            verify_response = requests.get(url, verify=False)
            print(f"验证状态码: {verify_response.status_code}")
            self.assertIn(verify_response.status_code, [200, 303], "URL应该可以正常访问")
            
        except json.JSONDecodeError as e:
            self.fail(f"响应不是有效的JSON格式: {str(e)}")
            
        # 测试获取新客户链接（带预填数据）
        print("\n=== 获取新客户链接（带预填数据）===")
        payload = {
            "model": "res.partner",
            "process_type": "new",
            "context": {
                "default_name": "小海智能",
                "default_email": "xiaohai@xiaohai.com",
                "default_phone": "12345678901",
                "default_mobile": "12345678901"
            }
        }
        response = requests.post(
            f"{self.base_url}/api/v1/object/link",
            headers=self.headers,
            json=payload,
            verify=False
        )
        try:
            json_data = response.json()
            self.assertEqual(response.status_code, 200, "状态码应为200")
            self.assertEqual(json_data["status"], "success", "响应状态应为success")
            self.assertIn("url", json_data["data"], "响应应包含url字段")
            
            # 验证带预填数据的URL可访问性
            url = json_data["data"]["url"]
            print(f"\n=== 验证预填数据URL可访问性 ===")
            print(f"访问URL: {url}")
            verify_response = requests.get(url, verify=False)
            print(f"验证状态码: {verify_response.status_code}")
            self.assertIn(verify_response.status_code, [200, 303], "URL应该可以正常访问")
            
        except json.JSONDecodeError as e:
            self.fail(f"响应不是有效的JSON格式: {str(e)}")
            
        # 测试获取不存在记录的链接
        print("\n=== 获取不存在记录的链接 ===")
        payload = {
            "model": "res.partner",
            "id": 999999,
            "process_type": "edit",
            "context": {}
        }
        response = requests.post(
            f"{self.base_url}/api/v1/object/link",
            headers=self.headers,
            json=payload,
            verify=False
        )
        try:
            json_data = response.json()
            self.assertEqual(response.status_code, 200, "状态码应为200")
            self.assertEqual(json_data["status"], "error", "响应状态应为error")
            self.assertIn("message", json_data, "响应应包含错误消息")
            
        except json.JSONDecodeError as e:
            self.fail(f"响应不是有效的JSON格式: {str(e)}")
            
        # 测试获取受限模型的链接
        print("\n=== 获取受限模型的链接 ===")
        payload = {
            "model": "ir.model",
            "id": 1,
            "process_type": "edit",
            "context": {}
        }
        response = requests.post(
            f"{self.base_url}/api/v1/object/link",
            headers=self.headers,
            json=payload,
            verify=False
        )
        try:
            json_data = response.json()
            self.assertEqual(response.status_code, 200, "状态码应为200")
            self.assertEqual(json_data["status"], "error", "响应状态应为error")
            self.assertIn("message", json_data, "响应应包含错误消息")
            
        except json.JSONDecodeError as e:
            self.fail(f"响应不是有效的JSON格式: {str(e)}")


    def test_07_update_record(self):
        """测试更新记录"""
        print("\n测试更新记录")

        # 测试更新合法记录
        print("\n=== 更新合法记录 ===") 
        payload = {
            "model": "res.partner",
            "id": 1,
            "values": {
                "name": "张三",
                "phone": "13800138000", 
            }
        }
        response = requests.post(
            f"{self.base_url}/api/v1/object/update",
            headers=self.headers,
            json=payload,   
            verify=False
        )
        self._print_response(response, "更新合法记录")      
        
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(data['status'], 'success')
            self.assertIn('data', data)
            self.assertIn('id', data['data'])
            self.assertIn('name', data['data'])
            self.assertIn('url', data['data'])
            
            # 验证返回的URL是否可访问
            print(f"\n=== 验证更新记录URL可访问性 ===")
            url = data['data']['url']
            print(f"访问URL: {url}")
            verify_response = requests.get(url, verify=False)
            print(f"验证状态码: {verify_response.status_code}")
            self.assertIn(verify_response.status_code, [200, 303], "URL应该可以正常访问")
                
        # 测试更新不存在记录                
        print("\n=== 更新不存在记录 ===")
        payload = {
            "model": "res.partner",
            "id": 999999,
            "values": {
                "name": "张三",
                "phone": "13800138000", 
            }   
        }
        response = requests.post(
            f"{self.base_url}/api/v1/object/update",
            headers=self.headers,
            json=payload,
            verify=False
        )
        self._print_response(response, "更新不存在记录")

        # 测试更新受限模型记录
        print("\n=== 更新受限模型记录 ===")
        payload = {
            "model": "ir.model",
            "id": 1,
            "values": { 
                "name": "张三",
                "phone": "13800138000", 
            }
        }
        response = requests.post(
            f"{self.base_url}/api/v1/object/update",
            headers=self.headers,
            json=payload,
            verify=False
        )
        self._print_response(response, "更新受限模型记录")

        # 测试更新非法JSON数据          
        print("\n=== 更新非法JSON数据 ===")
        payload = {
            "model": "res.partner",
            "id": 1,
            "values": "invalid json"
        }
        response = requests.post(
            f"{self.base_url}/api/v1/object/update",
            headers=self.headers,
            json=payload,
            verify=False
        )
        self._print_response(response, "更新非法JSON数据")  
        
        # 测试更新非法字段
        print("\n=== 更新非法字段 ===")
        payload = {
            "model": "res.partner",
            "id": 1,
            "values": {
                "invalid_field": "invalid value"
            }
        }
        response = requests.post(
            f"{self.base_url}/api/v1/object/update",
            headers=self.headers,
            json=payload,
            verify=False
        )
        self._print_response(response, "更新非法字段")

        # 测试更新非法API密钥
        print("\n=== 更新非法API密钥 ===")
        payload = {
            "model": "res.partner",
            "id": 1,
            "values": {
                "name": "张三",
                "phone": "13800138000", 
            }
        }
        response = requests.post(
            f"{self.base_url}/api/v1/object/update",
            headers=self.headers,
            json=payload,
            verify=False
        )
        self._print_response(response, "更新非法API密钥")

    def test_08_create_record(self):
        """测试创建记录"""
        print("\n测试创建记录")

        # 测试创建合法记录
        print("\n=== 创建合法记录 ===")
        payload = {
            "model": "res.partner",
            "values": {
                "name": "张三",
                "phone": "13800138000", 
            }
        }
        response = requests.post(
            f"{self.base_url}/api/v1/object/create",
            headers=self.headers,
            json=payload,
            verify=False
        )
        self._print_response(response, "创建合法记录")  
        
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(data['status'], 'success')
            self.assertIn('data', data)
            self.assertIn('id', data['data'])
            self.assertIn('name', data['data'])
            self.assertIn('url', data['data'])
            
            # 验证返回的URL是否可访问
            print(f"\n=== 验证返回URL可访问性 ===")
            url = data['data']['url']
            print(f"访问URL: {url}")
            verify_response = requests.get(url, verify=False)
            print(f"验证状态码: {verify_response.status_code}")
            self.assertIn(verify_response.status_code, [200, 303], "URL应该可以正常访问")
        
        # 测试创建不存在模型记录    
        print("\n=== 创建不存在模型记录 ===")
        payload = {
            "model": "invalid_model",
            "values": {
                "name": "张三",
                "phone": "13800138000", 
            }
        }
        response = requests.post(
            f"{self.base_url}/api/v1/object/create",
            headers=self.headers,
            json=payload,
            verify=False
        )
        self._print_response(response, "创建不存在模型记录")

def run_tests():
    """运行测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMCPAPI)
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == "__main__":
    run_tests() 