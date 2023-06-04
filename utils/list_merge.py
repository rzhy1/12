import json
import os
import re
import yaml
import requests
from urllib import request
import concurrent.futures

from list_update import UpdateUrl
from sub_convert import SubConvert
from cv2box.utils import os_call

# 文件路径定义
Eterniy = './Eternity'
readme = './README.md'

sub_list_json = './sub/sub_list.json'
sub_merge_path = './sub/'
sub_list_path = './sub/list/'
yaml_p = '{}/sub_merge_yaml.yaml'.format(sub_merge_path)
tested_nodes_file = 'tested_nodes.txt'

def content_write(file, output_type):
    with open(file, 'w+', encoding='utf-8') as f:
        f.write(output_type)

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
        tested_nodes = []
        
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
                tested_nodes.append(url_info)  # 记录已测试的节点
                print(f'Writing content of {remarks} to {ids:0>2d}.txt')
            else:
                error_msg = 'Url 订阅内容无法解析'
                print(f'Writing error of {remarks} to {ids:0>2d}.txt')

            with open(f'{sub_list_path}{ids:0>2d}.txt', 'w+', encoding='utf-8') as f:
                f.write(error_msg if 'error_msg' in locals() else content)
        
        # 多线程测试节点延迟
        print('Testing node latency...\n')
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            results = executor.map(self.test_node_latency, tested_nodes)
        
        # 保存测试结果
        with open(tested_nodes_file, 'w+', encoding='utf-8') as f:
            for result in results:
                f.write(result + '\n')
        
        return content_list

    def test_node_latency(self, node_info):
        url, ids, remarks = node_info['url'], node_info['id'], node_info['remarks']
        try:
            response = requests.get(url, timeout=5)
            latency = response.elapsed.total_seconds() * 1000
            result = f'Node: {remarks}, Latency: {latency:.2f}ms'
        except requests.exceptions.RequestException:
            result = f'Node: {remarks}, Latency: Failed'
        print(result)
        return result

    def merge_nodes(self, content_list):
        output_type = 'ssr'
        output_content = ''
        output_content_temp = ''
        
        if output_type == 'ssr':
            for content in content_list:
                output_content_temp += content + '\n'
            
            output_content_temp = output_content_temp.rstrip()
            output_content_temp = output_content_temp.replace('ssr://', '')
            output_content_temp = output_content_temp.replace('ssr%3A%2F%2F', '')
            output_content_temp = output_content_temp.replace('ss://', '')
            
            # 节点去重
            content_list = output_content_temp.split('\n')
            print('\n-----去重开始-----')
            print('起始数量{}'.format(len(content_list)))
            
            for base_num in range(100, len(content_list), 100):
                temp_list = content_list[:base_num]
                current_num = len(set(temp_list))
                print('当前基准{}-----当前数量{}'.format(base_num, current_num))
            
            content_list = list(set(content_list))
            print('重复数量{}'.format(len(output_content_temp.split('\n')) - len(content_list)))
            print('-----去重完成-----\n')
            
            # 节点排序
            content_list = sorted(content_list, key=lambda x: self.get_sort_key(x), reverse=False)
            
            # 拼接节点
            output_content = ''
            for content in content_list:
                content = self.ssr_check(content)
                if content is not None:
                    output_content += content + '\n'
        else:
            output_content = '\n'.join(content_list)
        
        return output_content

    def get_sort_key(self, content):
        sort_key = content.split(':')[0] if ':' in content else content.split('://')[1].split('/')[0]
        return sort_key

    def ssr_check(self, content):
        ssr_url = 'ssr://' + content if not content.startswith('ssr://') else content
        ss_url = 'ss://' + content if not content.startswith('ss://') else content
        
        if not self.sc.check_valid(ssr_url) and not self.sc.check_valid(ss_url):
            return None
        
        if not ssr_url.startswith('ssr://'):
            ssr_url = self.sc.ssr_link(ss_url)
        
        return ssr_url

    def save_yaml(self, content_yaml):
        with open(yaml_p, 'w+', encoding='utf-8') as f:
            f.write(content_yaml)

        return yaml_p

    def update_sub_list(self, content_yaml):
        sub_url = 'https://raw.githubusercontent.com/fw876/helloworld/master/README.md'
        request.urlretrieve(sub_url, readme)
        uu = UpdateUrl(readme, content_yaml)
        uu.update()
        uu.test_url()
        uu.save()

def main():
    sm = SubMerge()
    input_list = sm.read_list(sub_list_json, split=True)
    content_list = sm.sub_merge(input_list)
    output_content = sm.merge_nodes(content_list)
    content_yaml = sm.sc.main(output_content, output_type='url', format_name_enabled=False)
    yaml_p = sm.save_yaml(content_yaml)
    sm.update_sub_list(content_yaml)
    content_write(Eterniy, content_yaml)
    print('Done!')

if __name__ == '__main__':
    main()
