import requests,json,os,time,argparse,copy,time
from funcs import get_max_pid
API_ROOT = 'https://t-hole.red/_api/v1/'
SPACE = 5
TOKEN = '39fzRQwSVvkB3x1P'
HEADERS = {'User-Token': TOKEN}
PROXY = {'http':'123.56.231.232'}

DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_PATH,exist_ok=True)    
JSON_PATH = os.path.join(DATA_PATH, 'json')
os.makedirs(JSON_PATH,exist_ok=True)
UPDATE_PATH = os.path.join(DATA_PATH, 'update')
os.makedirs(UPDATE_PATH,exist_ok=True)
LOG_PATH = os.path.join(DATA_PATH,'log')
os.makedirs(LOG_PATH,exist_ok=True)

def update_list(reflag:int)->list:
    "确认爬取页码，返回全部页码或最新SPACE页"
    if reflag==1:
        return range(1,SPACE+1)
    elif reflag == 10:
        return range(1,10000)
    elif reflag == 2:
        mp = get_max_pid()
        temp = int((mp/25)*(2/5))
        l = mp - (temp *25)
        dat = {'max_last':mp,'crawl_last':l}
        print(f'max_pid:{mp},crawl:{l}')
        with open(os.path.join(LOG_PATH,'log.json'),'wb+')as f:
            f.write(json.dumps(dat,ensure_ascii=False).encode('utf-8'))
        return range(1,temp)
    elif reflag == 3:
        with open(os.path.join(LOG_PATH,'log.json'),'r')as f:
            dat = json.load(f)
        mp = get_max_pid()
        crawl_last = dat['crawl_last']
        temp = int((mp-crawl_last)/25)+1
        return range(temp,100000)
    elif reflag == 4:
        return range(1,100000)

def crawl(page_list:list,to_dir:str)->None:
    "爬取相应列表内的页码至to_str文件夹下"
    for i in page_list:
        try:
            url = API_ROOT + f'/getlist?p={i}&order_mode=0'
            r = requests.get(url,headers=HEADERS)
            if r.json()['data']:
                fn = os.path.join(to_dir,'page%04d.json'%i)
                os.makedirs(os.path.dirname(fn),exist_ok=True)
                with open (fn,'wb+') as f:
                    f.write(json.dumps(r.json(),ensure_ascii=False).encode('utf-8'))
            else:
                break
            print('%4d:finished'%i)
        except:
            print('%4d:error'%i)
            return

def get_comment(pid:int)->list:
    """获取评论"""
    GET_COMMENT_URL = API_ROOT + '/getcomment?pid=' + str(pid)
    r = requests.get(GET_COMMENT_URL,headers=HEADERS)
    #time.sleep(0.5)
    w = r.json()
    if w['code'] == -1:
        print('comment code is -1')
        return {}
    else:
        return w
        
def comment_process(comment:dict,cur_comments:list)->list:
    flag = True
    for cur_comment in cur_comments:
        if comment['timestamp'] == cur_comment['timestamp']:
            if comment['text'] == cur_comment['text']:
                if comment['name_id'] == cur_comment['name_id']:
                    if comment.get('pid'):
                        flag = False#if comment.get('pid'):  #判断新旧版本标准，存在则采用新版本
                        break
    if not flag:#旧的有新的没有，加，旧的有新的有跳过；旧的没有新的有跳过
        new_version = {
                "author_title": comment['author_title'],
                "blocked": comment['blocked'],
                "blocked_count": 0,
                "can_del": comment['can_del'],
                "cid": -1,
                "create_time": comment['timestamp'],
                "is_blocked": False,
                "is_tmp": False,
                "name_id": comment['name_id'],
                "text": comment['text'],
                "timestamp": comment['timestamp']
            }
        cur_comments.append(new_version)
        print('one old comment has been modified and added')
    return cur_comments

def add_comment(pid:int,json_origin:dict,post_path:str)->dict:
    json_temp = copy.deepcopy(json_origin)
    comments_req = get_comment(pid)
    if comments_req:
        comments = comments_req['data']
    else:
        comments = []
    if not os.path.exists(post_path):
        if json_temp['data']['comments'] is None and json_temp['data']['n_comments']>0:
            if comments:#comment请求有回复则输入
                json_temp['data']['comments'] = comments
        elif json_temp['data']['comments'] and len(json_temp['data']['comments'])<json_temp['data']['n_comments']:
            json_temp['data']['comments'] = comments
    else:
        cur_comments = json_temp['data']['comments'] if json_temp['data']['comments'] else comments
        with open(post_path,'r',encoding='utf-8') as f:
            past_version = json.load(f)
        if past_version['data']['comments']:
            for comment in past_version['data']['comments']:
                comment_process(comment,cur_comments)
        json_temp['data']['comments'] = cur_comments
    return json_temp

def split_pages(file_list:str):
    "从页中分离出pid"
    for fp in file_list:
        json_temp = {"code":0,"data":{}}
        try:
            with open(fp,'r',encoding='utf-8')as f:
                json_page = json.load(f)
            for json_to_add in json_page["data"]:
                json_temp['data']=json_to_add
                pid = json_to_add["pid"]
                id_path = os.path.join(JSON_PATH,'%06d.json'%pid)
                json_2 = add_comment(int(pid),json_temp,id_path)
                with open(id_path,'wb+') as f:
                    f.write(json.dumps(json_2,ensure_ascii=False).encode('utf-8'))
                print('%d successed'%pid)
        except Exception as e:
            print(e)
            print(e.__traceback__.tb_frame.f_globals["__file__"])
            print(e.__traceback__.tb_lineno)

def main():
    parser = argparse.ArgumentParser('New T-Hole Crawler by pages')
    parser.add_argument('--update', type=int)    #默认更新模式
    args = parser.parse_args()
    os.makedirs(DATA_PATH,exist_ok=True)
    os.makedirs(JSON_PATH,exist_ok=True)
    os.makedirs(UPDATE_PATH,exist_ok=True)
    renew_list = update_list(args.update)#
    cur_dir = os.path.join(UPDATE_PATH,"%s-%s-%s-%s-%s-%s"%time.localtime(time.time())[:6])
    os.makedirs(cur_dir,exist_ok=True)
    crawl(renew_list,cur_dir)
    file_list = []
    for fn in os.listdir(cur_dir):
        file_list.append(os.path.join(cur_dir,fn))
    split_pages(file_list)
if __name__ == "__main__":
    main()
