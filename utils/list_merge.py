import json
import os
import re
import yaml
import requests
from urllib import request
import concurrent.futures

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
        with concurrent.futures.ThreadPoolExecutor() as executor:
            content_yaml = list(executor.map(self.merge, [content_raw]))[0]
        content_write(yaml_p, content_yaml)
        print(f'Done!')

    def merge(self, content):
        return self.sc.main(content, 'content', 'YAML', {'dup_rm_enabled': True, 'format_name_enabled': True})

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


def test_node_latency(node_info):
    # 节点延迟测试的逻辑
    return result


if __name__ == '__main__':
    sm = SubMerge()
    sub_list_remote = sm.read_list(sub_list_json, split=True)
    sm.sub_merge(sub_list_remote)
    sm.readme_update(readme, sub_list_remote)

    # 读取 sub_merge_yaml.yaml 文件，采用 clash 核心，测试节点的延迟
    with open(yaml_p, 'r', encoding='utf-8') as f:
        yaml_content = f.read()
        clash_config = yaml.safe_load(yaml_content)

    print('\n-----节点延迟测试开始-----')
    tested_nodes = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = []
        for proxy in clash_config['proxies']:
            node_info = {
                'url': proxy['server'],
                'id': proxy['name'],
                'remarks': proxy['name']
            }

            if node_info['url'] not in tested_nodes:
                future = executor.submit(test_node_latency, node_info)
                futures.append(future)
                tested_nodes.append(node_info['url'])

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            print(result)
            # 将测试通过的节点保存到文件中
            if result['status'] == 'pass':
                with open('available_nodes.txt', 'a', encoding='utf-8') as f:
                    f.write(f"{result['url']}\n")

    print('-----节点延迟测试完成-----')
