import yaml
import requests
import concurrent.futures

def test_latency(proxy):
    try:
        if proxy['type'] == 'ssr':
            url = f"http://{proxy['server']}:{proxy['port']}/"
        else:
            url = f"http://{proxy['server']}:{proxy['port']}/ping"

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        latency = response.elapsed.total_seconds() * 1000
        proxy['delay'] = latency
        return proxy
    except:
        return None

def test_all_latencies(proxies):
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(test_latency, proxy) for proxy in proxies]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                results.append(result)
    return results

def convert_to_clash_yaml(proxies):
    clash_proxies = []
    for proxy in proxies:
        clash_proxy = {}
        clash_proxy['name'] = proxy['name']

        if proxy['type'] == 'vmess':
            clash_proxy['type'] = 'vmess'
            clash_proxy['server'] = proxy['server']
            clash_proxy['port'] = proxy['port']
            clash_proxy['uuid'] = proxy['uuid']
            clash_proxy['alterId'] = proxy['alterId']
            clash_proxy['cipher'] = proxy['cipher']
            clash_proxy['tls'] = proxy.get('tls', False)
            clash_proxy['network'] = proxy.get('network', 'tcp')
            clash_proxy['ws-path'] = proxy.get('ws-path', '/')
            clash_proxy['ws-headers'] = proxy.get('ws-headers', {})
            clash_proxy['skip-cert-verify'] = proxy.get('skip-cert-verify', False)

        elif proxy['type'] == 'ss':
            clash_proxy['type'] = 'ss'
            clash_proxy['server'] = proxy['server']
            clash_proxy['port'] = proxy['port']
            clash_proxy['cipher'] = proxy['cipher']
            clash_proxy['password'] = proxy['password']

        elif proxy['type'] == 'trojan':
            clash_proxy['type'] = 'trojan'
            clash_proxy['server'] = proxy['server']
            clash_proxy['port'] = proxy['port']
            clash_proxy['password'] = proxy['password']
            clash_proxy['skip-cert-verify'] = proxy.get('skip-cert-verify', False)

        elif proxy['type'] == 'ssr':
            clash_proxy['type'] = 'ssr'
            clash_proxy['server'] = proxy['server']
            clash_proxy['port'] = proxy['port']
            clash_proxy['cipher'] = proxy['cipher']
            clash_proxy['password'] = proxy['password']
            clash_proxy['obfs'] = proxy['obfs']
            clash_proxy['protocol'] = proxy['protocol']
            clash_proxy['obfsparam'] = proxy['obfsparam']
            clash_proxy['protoparam'] = proxy['protoparam']

        clash_proxies.append(clash_proxy)

    clash_yaml = {
        'proxies': clash_proxies
    }

    return clash_yaml

# 读取 sub_merge_yaml.yaml 文件
with open('./sub/sub_merge_yaml.yaml', 'r') as file:
    data = yaml.safe_load(file)

proxies = data.get('proxies', [])
if not proxies:
    print("No proxies found in the YAML file.")
    exit()

# 测试节点延迟
proxies_with_latency = test_all_latencies(proxies)

# 转换为 Clash YAML 格式
clash_yaml = convert_to_clash_yaml(proxies_with_latency)

# 将结果保存为 clash.yaml 文件
with open('clash.yaml', 'w') as file:
    yaml.dump(clash_yaml, file)

print("Clash YAML file has been generated successfully.")
