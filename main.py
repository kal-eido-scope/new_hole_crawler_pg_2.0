import requests,json,os,time,argparse,copy,time
API_ROOT = 'https://t-hole.red/_api/v1/'
SPACE = 5
TOKEN = '39fzRQwSVvkB3x1P'
HEADERS = {'User-Token': TOKEN}
PROXY = {'http':'123.56.231.232'}

DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')
JSON_PATH = os.path.join(DATA_PATH, 'json')
UPDATE_PATH = os.path.join(DATA_PATH, 'update')

def update_list(reflag:bool)->list:
    "确认爬取页码，返回全部页码或最新SPACE页"
    if reflag==1:
        return range(1,SPACE+1)
    else:
        return range(1,10000)

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

def add_comment(pid:int,json_origin:dict,post_path:str)->dict:
    json_temp = copy.deepcopy(json_origin)
    comments_req = get_comment(pid)
    if comments_req:
        comments = comments_req['data']
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
                if comment not in cur_comments:
                    cur_comments.append(comment)
        else:
            json_temp['data']['comments'] = cur_comments
    return json_temp

def split_pages(file_list:str):
    "从页中分离出pid"
    for fp in os.listdir(file_list):
        json_temp = {"code":0,"data":{}}
        try:
            with open(fp,'r')as f:
                json_page = json.load(f)
            for json_to_add in json_page["data"]:
                json_temp['data']=json_to_add
                pid = json_to_add["pid"]
                id_path = os.path.join(JSON_PATH,'%06d.json'%pid)
                json_2 = add_comment(int(pid),json_temp,id_path)
                with open(id_path,'wb+') as f:
                    f.write(json.dumps(json_2,ensure_ascii=False).encode('utf-8'))
                print('%d successed'%pid)
        except:
            continue

def main():
    parser = argparse.ArgumentParser('New T-Hole Crawler by pages')
    parser.add_argument('--update', type=int)    #默认更新模式
    args = parser.parse_args()
    os.makedirs(DATA_PATH,exist_ok=True)
    os.makedirs(JSON_PATH,exist_ok=True)
    os.makedirs(UPDATE_PATH,exist_ok=True)
    renew_list = update_list(args.update)#
    cur_dir = os.path.join(UPDATE_PATH,"%s-%s-%s-%s-%s-%s"%time.localtime(time.time())[:6])
    crawl(renew_list,cur_dir)
    #for fn in os.listdir(cur_dir):
        #split_pages(os.path.join(cur_dir,fn))
if __name__ == "__main__":
    main()