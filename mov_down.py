import re,os,argparse,json,requests
from tqdm import tqdm
from urllib import parse
from urllib.request import urlretrieve
from funcs import DATA_PATH,LOG_PATH,JSON_PATH,SPACE,get_max_pid,get_cur_pid,scan_mode

MOV_PATH = os.path.join(DATA_PATH,'mov')
os.makedirs(MOV_PATH,exist_ok=True)
MOV_PID_LIST = os.listdir(MOV_PATH)
ERROR_MOV_PATH = os.path.join(LOG_PATH,'error_mov.json')

MOV_EXTS = ('mov','mp4')

STATUS_MESSAGE = ['No mov','Success','Error']

def write_error(pid:int,url:str,e:Exception,data_json:dict,):
    if data_json.get(pid):
        data_json[pid].append({url:e.__str__()})
    else:
        data_json[pid]=[{url:e.__str__()}]

def get_type(urls:list)->dict:
    results = {}
    for url in urls:
        par =parse.urlparse(url[0])  #修改re匹配pattern对应此处
        for ext in MOV_EXTS:
            if par.query.endswith(ext) or par.path.endswith(ext):
                results[url[0]]=ext
                break
    return results

def find_mov(pid:int)->dict:
    post_path = os.path.join(JSON_PATH,'%06d.json'%pid)
    with open(post_path,'r',encoding='utf-8') as f:
        p = json.load(f)
    regular = re.compile(r'((https|ftp|file):\/\/[-A-Za-z0-9+&@#\/%?=~_|!:,.;]+[-A-Za-z0-9+&@#\/%=~_|])')
    urls = re.findall(regular,p['data']['text'])
    if p['data']['comments']:
        for comment_dict in p['data']['comments']:
            urls.extend(re.findall(regular,comment_dict['text']))
    results = get_type(urls)
    return results

def format_mov_name(url:str,ext:str)->str:
    if url.endswith('.'+ext):
        url_whole_name = os.path.split(url)[-1]
        url_name = url_whole_name[-40:] if len(url_whole_name)>=40 else url_whole_name
    else:
        url2 = re.sub('\W','~',url)
        url_name = url2[-40:] if len(url2)>=40 else url2
        url_name += '.' +ext
    return url_name

def get_mov(pid:int,urls:dict,data_json:dict):
    status_num = 0
    if urls:
        os.makedirs(os.path.join(MOV_PATH,'%0d'%pid), exist_ok=True)
        for url,ext in urls.items():
            url_name = format_mov_name(url,ext)
            mov_path = os.path.join(MOV_PATH,'%0d'%pid,url_name)
            if os.path.exists(mov_path):
                print('%d\tmovie skipped'%pid)
                continue
            try:
                urlretrieve(url,mov_path)
                print('%d\tA movie dowloaded.'%pid)
                status_num = 1
            except Exception as e:
                write_error(pid,url,e,data_json)
                print('%d\tA movie failed.'%pid)
                status_num = 2
    return status_num
def main():
    parser = argparse.ArgumentParser('T-hole.red Crawler')
    parser.add_argument('--start', type=int, help='Inclusion')
    parser.add_argument('--end', type=int, help='Exclusion')
    parser.add_argument('--scan', type=int, help='Scan Mode')
    args = parser.parse_args()
    s = requests.Session()
    max_pid = get_max_pid()
    if args.scan:
        start_id,end_id = scan_mode(max_pid,args.scan)
    else:
        if args.start:
            start_id = min(args.start,max_pid)
        else:
            cur_json = []
            if MOV_PID_LIST:
                for pid in MOV_PID_LIST:
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
        with open (ERROR_MOV_PATH,'r') as f:
            data_json = json.load(f)    #载入错误日志
    except:
        data_json = {}
    f = open (ERROR_MOV_PATH,'w+')     #打开错误日志写入状态
    try:
        for pid in tqdm(range(start_id,end_id), desc='Movies'):
            try:
                mov_dict = find_mov(pid)
                status_num = get_mov(pid,mov_dict,data_json)
                tqdm.write(f'pid:{pid},Status:{STATUS_MESSAGE[status_num]}')
            except:
                tqdm.write('%d no exist'%pid)
                continue
        json.dump(data_json,f)
    except:
        json.dump(data_json,f)      #意外恢复
    f.close()
if __name__ == '__main__':
    main()

