from urllib.parse import urlencode, parse_qsl, unquote, quote_plus, urlparse
from functools import partial
from xbmcplugin import addDirectoryItem, endOfDirectory, setResolvedUrl, setContent
from xbmcaddon import Addon
from pickle import load, dump
from xbmcvfs import translatePath
from datetime import datetime, timedelta
import re, sys, requests, xbmcgui, json, os
addon_url = sys.argv[0]
HANDLE = int(sys.argv[1])
addon_name = Addon().getAddonInfo('name')
addon_id = Addon().getAddonInfo('id')
ICON = Addon().getAddonInfo('icon')
PATH = Addon().getAddonInfo('path')
RESOURCES = PATH + '/media/'
searchimg = RESOURCES +'search.png'
nextimg = RESOURCES + 'next.png'
idsource = Addon().getSetting('idsource')
addon_data_dir = os.path.join(translatePath('special://userdata/addon_data'), addon_id)
UA = 'Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro Build/AP4A.261212) AppleWebKit/605.1.15 (KHTML, like Gecko) Chrome/133.0.0.0 Mobile Safari/605.1.15 EdgA/133.0.0.0'

def addDir(title, img, plot, mode, is_folder=True, **kwargs):
    kwargs = {key: json.dumps(value) if isinstance(value, list) else value for key, value in kwargs.items()}
    dir_url = f'{addon_url}?{urlencode({"mode": mode, **kwargs})}'
    list_item = xbmcgui.ListItem(label=title)
    list_item.setArt({'icon': img, 'thumb': img, 'poster': img, 'fanart': img})
    info_tag = list_item.getVideoInfoTag()
    info_tag.setTitle(title)
    info_tag.setPlot(plot)
    setContent(HANDLE, 'videos')
    if not is_folder:
        list_item.setProperty('IsPlayable', 'true')
    addDirectoryItem(HANDLE, dir_url, list_item, is_folder)
    
def getlink(url, ref):
    r = requests.get(url, timeout=20, headers={'user-agent': UA,'referer': ref.encode('utf-8')})
    r.encoding = 'utf-8'
    return r

def url_to_text(url):
    last_part = url.split('/')[-1]
    return re.sub(r'\W+', ' ', last_part).strip().upper()

def check_string(m, target):
    if not m:
        return False
    m = re.sub(r"\s+", "", m).lower()
    target = re.sub(r"\s+", "", target).lower()
    return m in target

def fu(url):
    return requests.get(url, headers={'user-agent': UA, 'referer': url.encode('utf-8')}, allow_redirects=True).url

def referer(url):
    parsed_url = urlparse(url.strip())
    return f'{parsed_url.scheme}://{parsed_url.netloc}/'

def get_file_path(filename):
    return os.path.join(addon_data_dir, filename)

def read_file(filename):
    path = get_file_path(filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'rb') as f:
            return load(f)
    except:
        return None
    
def write_file(filename, data):
    if not os.path.exists(addon_data_dir):
        os.makedirs(addon_data_dir)
    path = get_file_path(filename)
    try:
        with open(path, 'wb') as f:
            dump(data, f)
    except:
        pass
    return path

def search_history_save(search_key):
    if not search_key:
        return
    history = read_file('historys.pkl') or []
    if search_key in history:
        history.remove(search_key)
    elif len(history) >= 20:
        history.pop()
    history.insert(0, search_key)
    write_file('historys.pkl', history)
    
def search_history_get():
    return read_file('historys.pkl') or []

def process_items(items):
    for k in items:
        name = k['name']
        description = k.get('description', name)
        image = k['image']['url'] if k.get('image') else ICON
        if k.get('remote_data'):
            addDir(name, image, description, 'remote_data', url=k['remote_data']['url'], name=name, anh=image)
        elif k.get('sources'):
            for a in k['sources']:
                for b in a['contents']:
                    for c in b['streams']:
                        for d in c['stream_links']:
                            namef = name if d["name"] == name else f'{name} | [COLOR yellow]{d["name"]}[/COLOR]'
                            addDir(namef, image, description, 'play', link = d['url'], sub = [e['url'] for e in d.get('subtitles', [])], is_folder=False)

        elif k.get('channels'):
            for a in k['channels']:
                tentran = a['name']
                idtran = a.get('share', {}).get('url')                
                anhtran = a['image']['url']
                if a.get('sources'):
                    org_metadata = a.get('org_metadata', {}).get('title', '')
                    m = re.search(r"(\d{2}:\d{2})", org_metadata)
                    thoigian = m.group(1) if m else ''
                    blv = a.get('label') and a['label'].get('text', '') or ''
                    for b in a['sources']:
                        for c in b['contents']:
                            stream = sum(len(d.get('stream_links', [])) for d in c.get('streams') or [])
                            tenf1 = f'{thoigian} {tentran}' if thoigian else tentran
                            tenf = f'{tenf1} | [COLOR yellow]{blv}[/COLOR]'
                            if stream > 1:
                                addDir(tenf, anhtran, tenf, 'detail_xemplay', url = idtran, name = tentran, anh = anhtran)
                            else:                               
                                for d in c['streams']:                          
                                    for e in d['stream_links']:
                                        if e['type'] != 'webview':   
                                            tenf =f'{tenf1} | [COLOR yellow]{blv}[/COLOR]' if tenf1 == e["name"] else f'{tenf1} [COLOR yellow]{blv}[/COLOR] | [COLOR red]{e["name"]}[/COLOR]'
                                            if e.get('request_headers'):
                                                addDir(tenf, anhtran, tenf, 'play', link = e['url'], ref = e['request_headers'][0]['value'], is_folder=False)
                                            else:
                                                addDir(tenf, anhtran, tenf, 'play', link = e['url'], is_folder=False)

def timkiem(params_url):
    addDir('Tìm kiếm', searchimg, 'Tìm kiếm', 'search', url=params_url)
    b = search_history_get()
    if b:
        for m in b:
            addDir(m, searchimg, m, 'timcineflow', url=params_url, key = m)
    endOfDirectory(HANDLE)
    
def timcineflow(query, params_url):
    search_query = quote_plus(query)
    u = f'{params_url}{search_query}'
    r = getlink(u, u).json()
    if r.get('groups'):
        for a in r['groups']:
            host = a['name']
            for b in a['channels']:
                name = b['name']
                description = b.get('description', name)
                image = b['image']['url']
                ten = f'[COLOR yellow]{host}[/COLOR] {name}'
                if b.get('remote_data'):
                    addDir(ten, image, description, 'remote_data', url = b['remote_data']['url'], name = name, anh = image)
                if b.get('sources'):
                    for c in b['sources']:
                        for d in c['contents']:
                            for e in d['streams']:
                                for f in e['stream_links']:
                                    ten = f"[COLOR yellow]{host}[/COLOR] {name} [COLOR yellow]{f['name']}[/COLOR]"
                                    addDir(ten, image, ten, 'play', link = f['url'], sub = [g['url'] for g in f.get('subtitles', [])], is_folder=False)
    elif r.get('channels'):
        for c in r['channels']:
            if c.get('sources'):
                for d in c['sources']:
                    for e in d['contents']:
                        for f in e['streams']:
                            img = f['image']['url']
                            for g in f['stream_links']:
                                if g['type'] != 'webview':
                                    linkplay = g['url']
                                    tenkenh = g['name']
                                    addDir(tenkenh, img, tenkenh, 'play', link = linkplay, is_folder=False)
    endOfDirectory(HANDLE)

def main():    
    addDir('TRẬN CẦU TÂM ĐIỂM',os.path.join(PATH, 'icon.vebo.png'),'Trực tiếp các Trận cầu tâm điểm','index_vebo')
    addDir('HIGHLIGHT - BÓNG ĐÁ',os.path.join(PATH, 'icon.vebo.png'),'Highlight các Trận cầu tâm điểm','index_highlight', page = '1')
    
    u = 'https://raw.githubusercontent.com/bulubuloa88/bulubuloa88.github.io/refs/heads/main/Xem.json'
    ref = 'https://github.com/bulubuloa88/bulubuloa88.github.io/blob/main/Xem.json'
    r = getlink(u, ref).json()    
    for k in r['link']:
        h = k['name'] 
        plot = k['plot']
        img = k['image']
        url = k['api']
        if not check_string(idsource, url) and not check_string(idsource, h):
            addDir(h, img, plot, 'index_xemplay', url = url)
    endOfDirectory(HANDLE)

def index_vebo():
    url = 'https://api.vebo.xyz/api/match/featured/mt'
    resp = getlink(url, url).json()['data']
    thumb_url = 'https://img-90p.4shares.live/'
    trash = ['canceled','interrupted', 'finished']
    for k in resp:
        if k['match_status'] not in trash:
            time = datetime.fromtimestamp(int(k['timestamp'])/1000).strftime('%H:%M')
            blv = ' - '.join((h['name'] for h in k['commentators'] or []))  
            if k.get('scores') and k['match_status'] == 'live':      
                home = k['scores']['home']
                away = k['scores']['away']
                scores = f'[COLOR orange]({home}-{away})[/COLOR]'
            else:
                scores = ''
            tenv = f'{time} {scores} {k["name"]} | [COLOR yellow]{blv}[/COLOR]' if blv else f'{time} {scores} {k["name"]}' 
            if k.get('thumbnail_url'):
                if k['thumbnail_url'].get('live') and k['thumbnail_url'].get('pending'):
                    thumb_sub = k['thumbnail_url']['live'] if k['match_status'] == 'live' else k['thumbnail_url']['pending']
                    thumbnail_url =f'{thumb_url}{thumb_sub}'
                else:
                     thumbnail_url = k['tournament']['logo']               
            else:
                thumbnail_url = k['tournament']['logo']
            addDir(tenv, thumbnail_url,tenv, 'list_vebo', idk = k['id'], slug = k['slug'], is_folder = False)
    endOfDirectory(HANDLE)

def index_vebo_iptv():
    url = 'https://vebo.thethaoiptv.com/'
    resp = getlink(url, url).json()['groups'][0]
    if resp.get('channels'):
        for k in resp['channels']:
            name = k['name']      
            blv = k.get('labels') and k['labels'][0].get('text', '') or '' 
            tenf = f'{name} | [COLOR yellow]{blv}[/COLOR]' 
            image = k['image']['url'] if k.get('image') else ICON
            if k.get('id'):
                 addDir(tenf, image,tenf, 'list_vebo', idk = k['id'], is_folder = False)            
    endOfDirectory(HANDLE)

def list_vebo(idk):
    urlvb = fu('https://vebo.tv')
    resp = getlink(f'{urlvb}truc-tiep', urlvb).text
    ref = referer(re.search(r"base_embed_url.*?'(.*?)'", resp)[1])
    data = getlink(f'http://api.vebo.xyz/api/match/{idk}/meta', urlvb).json()
    if data.get('data'):
        kq = data['data']
        if kq.get('play_urls'):   
            link = kq['play_urls'][0]['url']  
            for k in kq['play_urls']:
                if k['name'] == 'FullHD':
                    link = k['url']       
            ref = f'{ref}/'
            play_vebo(link, ref)         
            
def play_vebo(link, ref=None):
    hdr = f'verifypeer=false&User-Agent={unquote(UA)}'
    linkplay = re.sub(r'\s+', '%20', link.strip(), flags=re.UNICODE)
    if ref:
        hdr += f'&Referer={ref}/'
    play_item = xbmcgui.ListItem(offscreen=True)
    if 'm3u8' in linkplay:
        play_item.setProperty('inputstream', 'inputstream.adaptive')
        play_item.setProperty('inputstream.adaptive.stream_headers', hdr)
        play_item.setProperty('inputstream.adaptive.manifest_headers', hdr)
    else:
        linkplay = f'{linkplay}|{hdr}'
    play_item.setPath(linkplay)
    setResolvedUrl(HANDLE, True, listitem=play_item)
   
def index_highlight(page):
    url = f'https://api.vebo.xyz/api/news/vebotv/list/highlight/{page}'
    detail_url = 'https://api.vebo.xyz/api/news/vebotv/detail/'
    data_match = getlink(url,url).json()  
    data = data_match['data']    
    highlight = data['highlight']
    if data.get('highlight'):
        logo =  highlight['feature_image']
        name = highlight['name']
        match_id = highlight['id']            
        api = f'{detail_url}{match_id}'
        addDir(name, logo,name, 'play_highlight', link = api, ref = api, is_folder=False)
    list = data['list']
    for item in list:
        if item['category']['slug'] == 'soi-keo':
            pass
        else:
            logo = item['feature_image']
            name = item['name']
            match_id = item['id']            
            api = f'{detail_url}{match_id}'
            addDir(name, logo,name, 'play_highlight', link = api, is_folder=False)       
    pagenext = int(page)+1
    if pagenext < 180:        
        page_name =f'[COLOR yellow]Trang {pagenext}[/COLOR]'    
        addDir(page_name, nextimg,'Trang tiếp theo', 'index_highlight', page = f'{pagenext}')
    endOfDirectory(HANDLE)
    
def play_highlights(api):   
    data_match = getlink(api,api).json()
    match = data_match['data']['video_url']
    play_vebo(match)
               
def index_xemplay(params_url):
    r = getlink(params_url, params_url).json()
    if r.get('search'):
        addDir('Tìm kiếm', searchimg, 'Tìm kiếm', 'timkiem', url = f"{r['search']['url']}?{r['search']['search_key']}=")
    for k in r['groups']:
        if k.get('remote_data'):
            tenkenh = k.get('channels_title', k['name'])
            addDir(tenkenh, ICON, tenkenh, 'list_xemplay', url = k['remote_data']['url'], p = 1)
    if r.get('channels_title'):
            tenindex = r['channels_title']
            addDir(tenindex, ICON, tenindex, 'list_xemplay', url = r['url'], p = 1)
    
    if r.get('sorts'):
            for k in r['sorts']:
                if k['type'] == 'radio':
                    tenkenh = f"[COLOR yellow]{k['text']}[/COLOR]"
                    addDir(tenkenh, ICON, tenkenh, 'list_xemplay', url = k['url'], p = 1)
                if k['type'] == 'dropdown':
                    name = k['text']
                    for m in k['value']:
                        tenkenh = f"[COLOR yellow]{name}[/COLOR] {m['text']}"
                        addDir(tenkenh, ICON, tenkenh, 'list_xemplay', url = m['url'], p = 1)
    
    endOfDirectory(HANDLE)    
    
def list_xemplay(params_url):    
    r = getlink(params_url, params_url).json()      
    if r.get('channels'):
        process_items(r['channels'])
    elif r.get('groups'):
        process_items(r['groups'])        
    endOfDirectory(HANDLE)  
    
def detail_xemplay(idtran, tentran, anhtran):
    data = getlink(idtran, idtran).json()['channel']['sources']
    for b in data:
        for c in b['contents']:
            for d in c['streams']:
                blv = d['name']
                for e in d['stream_links']:
                    if e['type'] != 'webview':
                        tenf = f'{tentran} | [COLOR yellow]{blv}[/COLOR] | [COLOR red]{e["name"]}[/COLOR]'
                        if e.get('request_headers'):
                            addDir(tenf, anhtran, tenf, 'play', link = e['url'], ref = e['request_headers'][0]['value'], is_folder=False)
                        else:
                            addDir(tenf, anhtran, tenf, 'play', link = e['url'], is_folder=False)
    endOfDirectory(HANDLE)
    
def remote_data(u, img, phim):
    r = getlink(u, u).json()
    if r.get('sources'):
            for a in r['sources']:
                host = a['name']
                for b in a['contents']:
                    mua = b['name']
                    for c in b['streams']:
                        server = c['name']
                        for d in c['stream_links']:
                            if d['type'] != 'webview':
                                tenf = f"{phim} [COLOR yellow]{mua} Tập {server}[/COLOR] [COLOR red]{host}[/COLOR] {d['name']}"
                                addDir(tenf, img, tenf, 'play', link = d['url'], sub = [e['url'] for e in d.get('subtitles', [])], is_folder=False)
    if r.get('channels'):
            for k in r['channels']:
                name = k['name']
                image = k['image']['url']
                for a in k['sources']:
                    for b in a['contents']:
                        for c in b['streams']:
                            for d in c['stream_links']:
                                if d['type'] != 'webview':
                                    tenf = f"{name} [COLOR yellow]{d['name']}[/COLOR]"
                                    addDir(tenf, image, tenf, 'play', link = d['url'], sub = [e['url'] for e in d.get('subtitles', [])], is_folder=False)
    endOfDirectory(HANDLE)
        
def search(params_url):
        query = xbmcgui.Dialog().input(u'Nhập nội dung cần tìm ...', type=xbmcgui.INPUT_ALPHANUM)
        if query:
            search_history_save(query)
            timcineflow(query, params_url)
        else:
            timkiem(params_url)   
            
def play(sub, link, ref):
        play_item = xbmcgui.ListItem(offscreen=True)
        if sub:
            play_item.setSubtitles(json.loads(sub))
        hdr = f'verifypeer=false&User-Agent={unquote(UA)}'
        linkplay = re.sub(r'\s+', '%20', link.strip(), flags=re.UNICODE)
        if ref:
            hdr += f'&Referer={referer(ref)}'
        play_item.setProperty('inputstream', 'inputstream.adaptive')
        play_item.setProperty('inputstream.adaptive.stream_headers', hdr)
        play_item.setProperty('inputstream.adaptive.manifest_headers', hdr)
        play_item.setPath(linkplay)
        setResolvedUrl(HANDLE, True, listitem=play_item)  
                             
def router(paramstring):
    params = dict(parse_qsl(paramstring))
    action_map = {
        'index_vebo': index_vebo_iptv,
        'list_vebo': partial(list_vebo, params.get('idk')),
        'play_vebo': partial(play_vebo, params.get('link'), params.get('ref')),
        'index_highlight': partial(index_highlight, params.get('page')),
        'play_highlight': partial(play_highlights, params.get('link')),
        'index_xemplay': partial(index_xemplay,params.get('url')),
        'index_xemplay': partial(index_xemplay,params.get('url')),
        'list_xemplay': partial(list_xemplay, params.get('url')),
        'detail_xemplay': partial(detail_xemplay, params.get('url'), params.get('name'), params.get('anh')),
        'remote_data': partial(remote_data, params.get('u'), params.get('img'), params.get('phim')),
        'search': partial(search, params.get('url')),
        'timkiem': partial(timkiem, params.get('url')),
        'timcineflow': partial(timcineflow, params.get('key'), params.get('url')),
        'play': partial(play, params.get('sub'), params.get('link'), params.get('ref')),        
    }
    action_map.get(params.get('mode'), main)()
    
try:
    router(sys.argv[2][1:])
except:
    pass