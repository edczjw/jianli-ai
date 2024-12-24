import requests

def test_upload():
    # 测试服务器是否运行
    response = requests.get('http://127.0.0.1:5000/')
    print("服务器状态:", response.json())
    
    # 测试文件上传
    files = {
        'file': ('test_resume.jpg', open('test_resume.jpg', 'rb'), 'image/jpeg')
    }
    
    response = requests.post('http://127.0.0.1:5000/api/analyze', files=files)
    print("分析结果:", response.json())

if __name__ == '__main__':
    test_upload() 