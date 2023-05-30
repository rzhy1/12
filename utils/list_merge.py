#!/usr/bin/env python3

import json
import os
import re
import yaml
import requests

from list_update import UpdateUrl
from sub_convert import SubConvert
from cv2box.utils import os_call
from urllib import request
import concurrent.futures

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
            
            # 跳过 Trojan 节点
            if 'trojan://' in url:
                print(f'Skipping Trojan node: {remarks}')
                continue
                
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

    def ping_test(self):
        print('开始进行Ping测试...\n')
        ping_file = './ping_result.txt'
        ping_nodes = []

        with open(yaml_p, 'r', encoding='utf-8') as f:
            yaml_content = f.read()
            nodes = yaml.safe_load(yaml_content)
        
        for node in nodes:
            if node.get('type') == 'ss' or node.get('type') == 'vmess':
                ping_result = subprocess.run(['ping', '-c', '4', '-W', '1', '-s', '32', node.get('server')], capture_output=True, text=True)
                if ping_result.returncode == 0:
                    ping_nodes.append(node)

        if ping_nodes:
            with open(ping_file, 'w', encoding='utf-8') as f:
                f.write(yaml.dump(ping_nodes))
            print(f'已将Ping通的节点保存至 {ping_file}\n')
        else:
            print('没有Ping通的节点\n')


if __name__ == '__main__':
    UpdateUrl().update_main()
    sm = SubMerge()
    sub_list_remote = sm.read_list(sub_list_json, split=True)
    sm.sub_merge(sub_list_remote)
    sm.readme_update(readme, sub_list_remote)
    sm.ping_test()

