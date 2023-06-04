import requests
import time
import threading
import yaml
import os

def test_latency(node):
    url = "https://www.youtube.com/generate_204"
    start_time = time.time()
    try:
        response = requests.get(url, proxies=node["proxy"], timeout=10)
        if response.status_code == 204:
            end_time = time.time()
            latency = end_time - start_time
            node["delay"] = round(latency * 1000, 2)  # Convert to milliseconds and round to 2 decimal places
        else:
            node["delay"] = -1  # Indicate failed connection
    except:
        node["delay"] = -1  # Indicate failed connection

# 读取sub_merge_yaml.yaml文件
sub_merge_path = "./sub/sub_merge_yaml.yaml"
with open(sub_merge_path, "r") as file:
    data = yaml.safe_load(file)

proxies = data.get("proxies", [])

# 多线程测试延迟
threads = []
for proxy in proxies:
    thread = threading.Thread(target=test_latency, args=(proxy,))
    threads.append(thread)
    thread.start()

# 等待所有线程完成
for thread in threads:
    thread.join()

# 移除连接失败的节点
proxies = [proxy for proxy in proxies if proxy["delay"] != -1]

# 读取config.yml文件
config_file = "./config/config.yml"
with open(config_file, "r") as file:
    config = yaml.safe_load(file)

# 更新clash配置中的节点列表
config["proxies"] = proxies

# 写入clash.yaml文件
os.makedirs("./sub", exist_ok=True)
clash_config_file = "./sub/clash.yaml"
with open(clash_config_file, "w") as file:
    yaml.dump(config, file, sort_keys=False)

# 打印成功消息
print("Clash configuration file generated: sub/clash.yaml")
