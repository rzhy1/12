import yaml
import requests
import concurrent.futures

def test_latency(proxy):
    try:
        if proxy['type'] == 'ssr':
            url = f"http://{proxy['server']}:{proxy['port']}/"
        else:
            url = f"http://{proxy['server']}:{proxy['port']}/ping"

        response = requests.get(url, timeout=5)
        response.raise_for_status()

        latency = response.elapsed.total_seconds() * 1000
        proxy['latency'] = latency
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
        if proxy['type'] == 'vmess':
            clash_proxy = {
                'name': proxy['name'],
                'type': 'vmess',
                'server': proxy['server'],
                'port': proxy['port'],
                'uuid': proxy['uuid'],
                'alterId': proxy['alterId'],
                'cipher': proxy['cipher'],
                'network': proxy['network'],
                'ws-path': proxy['ws-path'],
                'tls': proxy['tls'],
                'ws-headers': proxy['ws-headers'],
                'skip-cert-verify': proxy.get('skip-cert-vertify', False)
            }
        elif proxy['type'] == 'ss':
            clash_proxy = {
                'name': proxy['name'],
                'type': 'ss',
                'server': proxy['server'],
                'port': proxy['port'],
                'cipher': proxy['cipher'],
                'password': proxy['password']
            }
        elif proxy['type'] == 'trojan':
            clash_proxy = {
                'name': proxy['name'],
                'type': 'trojan',
                'server': proxy['server'],
                'port': proxy['port'],
                'password': proxy['password'],
                'skip-cert-verify': proxy.get('skip-cert-verify', False)
            }
        elif proxy['type'] == 'ssr':
            clash_proxy = {
                'name': proxy['name'],
                'type': 'ssr',
                'server': proxy['server'],
                'port': proxy['port'],
                'cipher': proxy['cipher'],
                'password': proxy['password'],
                'obfs': proxy['obfs'],
                'protocol': proxy['protocol'],
                'obfsparam': proxy['obfsparam'],
                'protoparam': proxy['protoparam']
            }
        else:
            continue
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
tested_proxies = test_all_latencies(proxies)

# 转换为 Clash YAML 格式
clash_yaml = convert_to_clash_yaml(tested_proxies)

# 输出 Clash YAML 文件
with open('./sub/clash.yaml', 'w') as file:
    yaml.dump(clash_yaml, file)

print("Clash YAML file has been generated successfully.")
