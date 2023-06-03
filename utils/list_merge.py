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
Eterniy = './Eternity'
readme = './README.md'

sub_list_json = './sub/sub_list.json'
sub_merge_path = './sub/'
sub_list_path = './sub/list/'
yaml_p = '{}/sub_merge_yaml.yaml'.format(sub_merge_path)
available_proxies_path = './sub/available_proxies.txt'


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
            return self.sc.main(content, 'content', 'YAML',
                                {'dup_rm_enabled': True, 'format_name_enabled': True})

        with concurrent.futures.ThreadPoolExecutor() as executor:
            content_yaml = list(executor.map(merge, [content_raw]))[0]
        content_write(yaml_p, content_yaml)
        print(f'Done!')

    def test_proxy_latency(proxy):
        try:
            if proxy["type"] == "vmess":
                test_url = f"http://{proxy['server']}:{proxy['port']}/test?param=value"
                response = requests.get(test_url)
                latency = response.elapsed.total_seconds()
                proxy["latency"] = latency
            elif proxy["type"] == "ss":
                # Implement SS latency test logic
                pass
            elif proxy["type"] == "vless":
                # Implement VLESS latency test logic
                pass
        except requests.exceptions.RequestException as e:
            print(f"Error testing proxy: {str(e)}")

    def test_and_save_proxy(proxy):
        test_proxy_latency(proxy)
        return proxy

    def test_and_save_proxies(proxies):
        available_proxies = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            future_to_proxy = {executor.submit(test_and_save_proxy, proxy): proxy for proxy in proxies}
            for future in concurrent.futures.as_completed(future_to_proxy):
                result = future.result()
                available_proxies.append(result)
        return available_proxies

    def save_proxies_to_file(proxies, filename):
        with open(filename, "w") as file:
            yaml.dump(proxies, file)

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


if __name__ == '__main__':
    with open(yaml_p, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
        proxies = data.get("proxies", [])

    available_proxies = test_and_save_proxies(proxies)
    save_proxies_to_file(available_proxies, "available_proxies.yaml")
    
    UpdateUrl().update_main()
    sm = SubMerge()
    sub_list_remote = sm.read_list(sub_list_json, split=True)
    sm.sub_merge(sub_list_remote)
    sm.readme_update(readme, sub_list_remote)
    sm.test_all_proxies()
