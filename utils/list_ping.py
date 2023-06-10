import yaml  
import threading  
import time  
import subprocess  
  
# 读取sub_merge_yaml.yaml文件  
with open('./sub/sub_merge_yaml.yaml', 'r', encoding='utf-8') as f:  
    proxies = yaml.load(f, Loader=yaml.FullLoader)  
  
# 初始化clash并读取配置文件  
subprocess.Popen(['clash', 'open', './config/config.yml'])  
  
# 定义测试节点函数  
def test_proxy(proxy):  
    # 测试节点延迟  
    start_time = time.time()  
    response = subprocess.run(['clash', 'test', proxy], capture_output=True, text=True)  
    end_time = time.time()  
    delay = end_time - start_time  
    print(f"Proxy {proxy} delay: {delay:.2f}s")  
  
# 创建100个线程测试节点延迟  
threads = []  
for proxy in proxies:  
    t = threading.Thread(target=test_proxy, args=(proxy,))  
    threads.append(t)  
    t.start()  
  
# 等待所有线程完成测试  
for t in threads:  
    t.join()  
  
# 输出可用节点并转换为clash工具可用的yaml文件  
available_proxies = [proxy for proxy in proxies if 'error' not in proxy]  
with open('./sub/available_proxies.yaml', 'w', encoding='utf-8') as f:  
    yaml.dump(available_proxies, f)
