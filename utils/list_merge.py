import json
import os
import re
import yaml
import requests
import threading

from list_update import UpdateUrl
from sub_convert import SubConvert
from cv2box.utils import os_call
from urllib import request
import concurrent.futures
import subprocess

# 文件路径定义
Eternity = './Eternity'
readme = './README.md'

sub_list_json = './sub/sub_list.json'
sub_merge_path = './sub/'
sub_list_path = './sub/list/'
yaml_p = '{}/sub_merge_yaml.yaml'.format(sub_merge_path)


def content_write(file, output_type):
    file = open(file, 'w+', encoding='utf-8')
    file.write(output_type)
    file.close()

class TestProxyThread(threading.Thread):
    def __init__(self, proxy_addr, result):
        threading.Thread.__init__(self)
        self.proxy_addr = proxy_addr
        self.result = result

    def run(self):
        latency = self.test_proxy(self.proxy_addr)
        if latency:
            self.result.append(latency)

class SubMerge:
    def __init__(self):
        self.sc = SubConvert()

    def read_list(self, json_file, split=False):
        with open(json_file, 'r', encoding='utf-8') as f:
            raw_list = json.load(f)
        input_list = []
        for index in range(len(raw_list)):
            if raw_list[index]['enabled']:
                if split == False:
                    urls = re.split('\|', raw_list[index]['url'])
                else:
                    urls = raw_list[index]['url']
                raw_list[index]['url'] = urls
                input_list.append(raw_list[index])
        return input_list

    def sub_merge(self, url_list):
        content_list = []
        os_call('rm -f ./sub/list/*')

        for index, url_info in enumerate(url_list):
            url, ids, remarks = url_info['url'], url_info['id'], url_info['remarks']
            content = self.sc.convert_remote(url, output_type='url', host='http://127.0.0.1:25500')
            if content.startswith('Url 解析错误'):
                content = self.sc.main(self.read_list(sub_list_json)[index]['url'], input_type='url', output_type='url')
                if content.startswith('Url 解析错误'):
                    error_msg = 'Url 解析错误'
                    print(f'Writing error of {remarks} to {ids:0>2d}.txt')
                else:
                    content_list.append(content)
                    print(f'Writing content of {remarks} to {ids:0>2d}.txt')
            elif content.startswith('Url 订阅内容无法解析'):
                error_msg = 'Url 订阅内容无法解析'
                print(f'Writing error of {remarks} to {ids:0>2d}.txt')
            elif content is not None:
                content_list.append(content)
                print(f'Writing content of {remarks} to {ids:0>2d}.txt')
            else:
                error_msg = 'Url 订阅内容无法解析'
                print(f'Writing error of {remarks} to {ids:0>2d}.txt')

            with open(f'{sub_list_path}{ids:0>2d}.txt', 'w+', encoding='utf-8') as f:
                f.write(error_msg if 'error_msg' in locals() else content)

        print('Merging nodes...\n')
        content_raw = ''.join(content_list)

        def merge(content):
            return self.sc.main(content, 'content', 'YAML', {'dup_rm_enabled': True, 'format_name_enabled': True})

        with concurrent.futures.ThreadPoolExecutor() as executor:
            content_yaml = list(executor.map(merge, [content_raw]))[0]
        content_write(yaml_p, content_yaml)
        print(f'Done!')

    def geoip_update(self, url):
        print('Downloading Country.mmdb...')
        try:
            url = "https://raw.githubusercontent.com/Loyalsoldier/geoip/release/Country.mmdb"
            request.urlretrieve(url, './utils/Country.mmdb')
            print('Success!\n')
        except Exception:
            print('Failed!\n')

    def readme_update(self, readme_file='./README.md', sub_list=[]):
        print('更新 README.md 中')
        with open(readme_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            f.close()

        for index in range(len(lines)):
            if lines[index] == '## 所有节点\n':
                lines.pop(index + 1)
                with open('./sub/sub_merge_yaml.yaml', 'r', encoding='utf-8') as f:
                    proxies = f.read()
                    proxies = proxies.split('\n- ')
                    top_amount = len(proxies) - 1
                lines.insert(index + 1, f'合并节点总数: `{top_amount}`\n')
                break

        with open(readme_file, 'w', encoding='utf-8') as f:
            data = ''.join(lines)
            print('完成!\n')
            f.write(data)

    def test_proxy(self, proxy):
        proxy_info = proxy.split('\n')
        proxy_server = proxy_info[1].split(':')
        proxy_address = proxy_server[0]
        proxy_port = proxy_server[1]

        try:
            response = subprocess.check_output(
                f"ping -c 3 -W 2 {proxy_address}", stderr=subprocess.STDOUT, shell=True
            )
            response = response.decode('utf-8')
            avg_time = re.findall(r"min/avg/max/mdev = (.+?)\/", response)
            if len(avg_time) > 0:
                avg_time = avg_time[0]
                return avg_time
        except subprocess.CalledProcessError:
            return None

    def test_all_proxies(self):
        with open(yaml_p, 'r', encoding='utf-8') as f:
            proxies = yaml.load(f, Loader=yaml.FullLoader)

        available_proxies = []
        threads = []
        lock = threading.Lock()

        def append_result(latency):
            lock.acquire()
            available_proxies.append(latency)
            lock.release()

        for proxy in proxies['proxies']:
            proxy_name = proxy['name']
            proxy_server = proxy['server']
            proxy_port = proxy['port']
            proxy_type = proxy['type']
            proxy_uuid = proxy['uuid']
            proxy_addr = f"{proxy_name}\n{proxy_server}:{proxy_port}\n{proxy_type}\n{proxy_uuid}"
            thread = TestProxyThread(proxy_addr, available_proxies)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        with open('./sub/available_proxies.txt', 'w', encoding='utf-8') as f:
            for latency in available_proxies:
                f.write(f"{latency['name']}: {latency['latency']} ms\n")


if __name__ == '__main__':
    UpdateUrl().update_main()
    sm = SubMerge()
    sub_list_remote = sm.read_list(sub_list_json, split=True)
    sm.sub_merge(sub_list_remote)
    sm.readme_update(readme, sub_list_remote)
    sm.test_all_proxies()
