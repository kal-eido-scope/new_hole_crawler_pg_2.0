import re
import json
import os
import requests
import argparse
import urllib3
from urllib import parse
from time import sleep
from funcs import get_cur_pid, scan_mode,get_max_pid,DATA_PATH,JSON_PATH,LOG_PATH,SPACE
from tqdm import tqdm
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

IMG_PATH = os.path.join(DATA_PATH,'img')        #img文件夹相对路径
os.makedirs(IMG_PATH,exist_ok=True)
IMG_PID_LIST = os.listdir(IMG_PATH)             #img文件夹下pid的list
ERROR_IMG_PATH = os.path.join(LOG_PATH,'error_img.json')   #img下载错误日志路径
STATUS_MESSAGE = ['No img','Success','Error']

IMG_EXTS = ('bmp','jpg','jpeg','png','tif','gif','pcx','tga','exif','fpx','svg','psd','cdr','pcd','dxf','ufo','eps','ai','raw','WMF','webp','avif','apng')

def write_error(pid:int,status_code:int,url:str,hole_url:str,data_json:dict)->bool:
    """写入错误代码"""
    if data_json.get(pid):
        data_json[pid].append({url:{'hole_url':hole_url,'status_code':status_code}})
    else:
        data_json[pid]=[{url:{'hole_url':hole_url,'status_code':status_code}}]
    
def find_img_url(text:str)->dict:
    "增加对ipfs的处理"
    results = {}
    pattern1 = '\[[^载]*?\]\(([^(\s)]*?'+'|[^(\s)]*?'.join(IMG_EXTS)+')\)'#(?!\s\[加载失败请点击此\](.*?))
    l1 = re.findall(pattern1,text)
    for x in l1:#此处改作正则判断替换
        if x.startswith('http') or x.startswith('https') or x.startswith('ftp'):
            url = x
        else:
            url = 'https:' + x
        par =parse.urlparse(url)
        for ext in IMG_EXTS:
            if par.query.endswith(ext) or par.path.endswith(ext):
                results[url]=('',ext)
                break
    pattern2 = '\[.*?\]\(([^(\s)]*?' + '|[^(\s)]*?'.join(IMG_EXTS) + ')\)\s\[加载失败请点击此\]\(([^(\s)]*?)\)'
    l2 = re.findall(pattern2,text)
    for x,y in l2:
        hole_url,ext = results.get(x)
        if ext:
            results[x]=(y,ext)
    return results

def re_find(pid:int)->dict:
    "返回所有图片地址"
    imgs = {}
    post_path = os.path.join(JSON_PATH,'%06d.json'%pid)
    with open(post_path,'r',encoding='utf-8') as f:
        p = json.load(f)
    dic_text = find_img_url(p['data']['text'])
    imgs = dic_text
    if p['data']['comments']:
        for comment_dict in p['data']['comments']:
            imgs = dict(imgs,**find_img_url(comment_dict['text']))
    return imgs
def get_format_path(img:str,ext:str,pid:int)->str:
    if img.endswith('.'+ext):
        img_whole_name = os.path.split(img)[-1]
        img_name = img_whole_name[-40:] if len(img_whole_name) >= 40 else img_whole_name
    else:
        img2 = re.sub('\W','~',img)
        img_name = img2[-40:] if len(img2) >= 40 else img2
        img_name += '.' + ext
    img_path = os.path.join(IMG_PATH,'%0d'%pid,img_name)
    return img_path
    
def get_img(pid:int,data_json:dict)->int:
    "0 for no img; 1 for success; 2 for errors happening"
    status_num = 0
    imgs = re_find(pid)
    if imgs:
        status_num = 1
        os.makedirs(os.path.join(IMG_PATH,'%0d'%pid), exist_ok=True)
        for img,value in imgs.items():
            hole_url = value[0]
            ext = value[-1]
            img_path = get_format_path(img,ext,pid)
            if os.path.exists(img_path):
                print('%d\timg skipped'%pid)
                continue
            try:
                try:
                    img_get = requests.get(img,verify=False,timeout=240)#urlretrieve(img)
                    status_code = img_get.status_code
                except:
                    img_get = requests.get(hole_url,verify=False,timeout=240)#urlretrieve(img)
                    status_code = img_get.status_code
            except:
                    status_code = 404
            if status_code != 200:
                status_num = 2
                write_error(pid,status_code,img,hole_url,data_json)
                print('%d\tAn img failed.'%pid)
            else:
                with open(img_path,'wb') as f:
                    f.write(img_get.content)
                print('%d\tAn img dowloaded.'%pid)
            sleep(2)
    return status_num

def main():
    parser = argparse.ArgumentParser('T-hole.red Crawler')
    parser.add_argument('--start', type=int, help='Inclusion')
    parser.add_argument('--end', type=int, help='Exclusion')
    parser.add_argument('--scan', type=int, help='Scan Mode')
    args = parser.parse_args()
    max_pid = get_max_pid()
    if args.scan:
        start_id,end_id = scan_mode(max_pid,args.scan)
    else:
        if args.start:
            start_id = min(args.start,max_pid)
        else:
            cur_json = []
            if IMG_PID_LIST:
                for pid in IMG_PID_LIST:
                    cur_json.append(int(pid))
                cur_json.sort()
                start_id = cur_json[-1]
            else:
                start_id = 1
        if args.end:
            end_id = min(max_pid,args.end)
        else:
            end_id = get_cur_pid()
        if end_id < start_id:
            end_id = start_id
    #start_id,end_id=max_pid-SPACE,max_pid
    try:
        with open (ERROR_IMG_PATH,'r') as f:
            data_json = json.load(f)    #载入错误日志
    except:
        data_json = {}
    f = open (ERROR_IMG_PATH,'w+')     #打开错误日志写入状态
    try:
        for pid in tqdm(range(start_id,end_id), desc='Images'):
            try:
                status_num = get_img(pid,data_json)
                tqdm.write(f'pid:{pid},Status:{STATUS_MESSAGE[status_num]}')
            except Exception as e:
                tqdm.write('%d no exist'%pid)
                continue
        json.dump(data_json,f)
    except Exception as e:
        json.dump(data_json,f)      #意外恢复
        print(e)
        print(e.__traceback__.tb_frame.f_globals["__file__"])
        print(e.__traceback__.tb_lineno)
    f.close()

if __name__ == '__main__':
    main()
