#!/usr/bin/env python3

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
from vmess import VmessConfig
from urllib.parse import urlparse

# 文件路径定义
Eterniy = './Eternity'
readme = './README.md'

sub_list_json = './sub/sub_list.json'
sub_merge_path = './sub/'
sub_list_path = './sub/list/'
yaml_p = '{}/sub_merge_yaml.yaml'.format(sub_merge_path)


def content_write(file, output_type):
    file = open(file, 'w+', encoding='utf-8')
    file.write(output_type)
    file.close()


class SubMerge:
    def __init__(self):
        self.sc = SubConvert()

    def read_list(self, json_file, split=False):  # 将 sub_list.json Url 内容读取为列表
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
                content = self.sc.main(self.read_list(sub_list_json)[index]['url'], input_type='url',
                                       output_type='url')
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

    def readme_update(self, readme_file='./README.md', sub_list=[]):  # 更新 README 节点信息
        print('更新 README.md 中')
        with open(readme_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            f.close()

        # 所有节点打印
        for index in range(len(lines)):
            if lines[index] == '## 所有节点\n':  # 目标行内容
                lines.pop(index + 1)  # 删除节点数量
                with open('./sub/sub_merge_yaml.yaml', 'r', encoding='utf-8') as f:
                    proxies = f.read()
                    proxies = proxies.split('\n- ')
                    top_amount = len(proxies) - 1
                lines.insert(index + 1, f'合并节点总数: `{top_amount}`\n')
                break

        # 写入 README 内容
        with open(readme_file, 'w', encoding='utf-8') as f:
            data = ''.join(lines)
            print('完成!\n')
            f.write(data)

    def test_proxy_availability(self, proxy):
        try:
            url = "https://www.google.com/generate_204"
            parsed_url = urlparse(url)
            ws_path = proxy.get('ws-path', '/')
            proxy_url = f"{parsed_url.scheme}://{proxy['server']}:{proxy['port']}{ws_path}"
            
            headers = {
                'Host': parsed_url.netloc,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36',
            }

            if proxy['type'] == 'vmess':
                vmess_config = {
                    'v': '2',
                    'ps': proxy['name'],
                    'add': proxy['server'],
                    'port': str(proxy['port']),
                    'id': proxy['uuid'],
                    'aid': str(proxy['alterId']),
                    'net': proxy.get('network', 'tcp'),
                    'type': proxy.get('cipher', 'auto'),
                    'sni': proxy.get('ws-headers', {}).get('Host', parsed_url.netloc),
                    'path': ws_path,
                    'tls': 'tls' in proxy and proxy['tls'],
                }
                proxy_url = f"{proxy_url}/?{urlencode(vmess_config)}"
                proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
                response = requests.get(url, headers=headers, proxies=proxies, timeout=5)
            else:
                response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 204:
                print(f"Proxy {proxy['name']} is available")
                with open('available_proxies.txt', 'a') as f:
                    f.write(f"{proxy}\n")
        except Exception as e:
            print(f"Proxy {proxy['name']} is not available: {e}")

    def test_node_availability(self):
        print("Testing node availability...")
        with open(yaml_p, 'r') as f:
            yaml_data = yaml.safe_load(f)

        proxies = yaml_data.get('proxies', [])
        threads = []
        max_threads = 100

        for proxy in proxies:
            thread = threading.Thread(target=self.test_proxy_availability, args=(proxy,))
            threads.append(thread)
            thread.start()

            if len(threads) >= max_threads:
                for thread in threads:
                    thread.join()
                threads = []

        for thread in threads:
            thread.join()

        print("Node availability testing completed.")


if __name__ == '__main__':
    UpdateUrl().update_main()
    sm = SubMerge()
    sub_list_remote = sm.read_list(sub_list_json, split=True)
    sm.sub_merge(sub_list_remote)
    sm.readme_update(readme, sub_list_remote)
    sm.test_node_availability()
