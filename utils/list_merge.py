import yaml
import threading
import requests

# 读取sub_merge_yaml.yaml文件
with open('./sub/sub_merge_yaml.yaml', 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)

proxies = config['proxies']

# 定义延迟测试的目标URL
target_url = 'https://www.YouTube.com/generate_204'

# 创建结果列表
results = []

# 定义测试函数
def test_latency(proxy):
    try:
        proxies = {
            'http': f"http://{proxy['server']}:{proxy['port']}",
            'https': f"http://{proxy['server']}:{proxy['port']}"
        }
        response = requests.get(target_url, proxies=proxies, timeout=10)
        response.raise_for_status()
        results.append({'name': proxy['name'], 'delay': response.elapsed.total_seconds()})
    except Exception as e:
        print(f"Error testing {proxy['name']}: {str(e)}")

# 创建线程列表
threads = []

# 启动多线程测试
for proxy in proxies:
    thread = threading.Thread(target=test_latency, args=(proxy,))
    thread.start()
    threads.append(thread)

# 等待所有线程执行完成
for thread in threads:
    thread.join()

# 按延迟排序结果列表
sorted_results = sorted(results, key=lambda x: x['delay'])

# 构建Clash配置文件
clash_config = {
    'proxies': [{
        'name': result['name'],
        'type': 'http',
        'server': proxies[index]['server'],
        'port': proxies[index]['port'],
        'delay': result['delay'],
        'url': target_url
    } for index, result in enumerate(sorted_results)],
    'proxy-groups': [
        {
            'name': 'proxies',
            'type': 'select',
            'proxies': [result['name'] for result in sorted_results]
        }
    ]
}

# 保存为clash.yaml文件
with open('/sub/clash.yaml', 'w', encoding='utf-8') as file:
    yaml.safe_dump(clash_config, file)
