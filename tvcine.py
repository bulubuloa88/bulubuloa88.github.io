import requests, time, random
from bs4 import BeautifulSoup
import hashlib
import re, json, os
import urllib.parse
import urlquick, htmlement
from resources import fshare, cache_utils
from addon import alert, notify, TextBoxes, getadv, ADDON, ADDON_ID, ADDON_PROFILE, LOG, PROFILE
import xbmcgui, xbmc, xbmcvfs
from datetime import timedelta

addon_url = "plugin://{}/".format(ADDON_ID)
CACHE_PATH = xbmcvfs.translatePath("special://temp")

def getlink(url,img):
    def getlink_tvcn(url,img):
        response = urlquick.get(url, max_age=60*60)
        soup = BeautifulSoup(response.content, "html.parser")
        items = []
        links = soup.find_all('a', href=lambda href: href and 'fshare.vn' in href)
        total_links = len(links)
        #dialog = xbmcgui.DialogProgress()
        #dialog.create('Đang lấy dữ liệu', 'Vui lòng đợi...')
        
        for i, link in enumerate(links):
            link = link.get('href')
            name,file_type,size_file = fshare.get_fshare_file_info(link)
            
            item={}
            if "folder" in link:
                playable = False
                
            else:
                playable = True
            
            item["label"] = name
            item["is_playable"] = playable
            item["path"] = 'plugin://plugin.video.vietmediaF?action=browse&url=%s' % link
            item["thumbnail"] = img
            item["icon"] = img
            item["label2"] = ""
            item["info"] = {'plot': '','size':size_file}
            items += [item]
            progress = int((i + 1) / total_links * 100)
            #dialog.update(progress, 'Đang lấy dữ liệu')
        #dialog.close()
        data = {"content_type": "movies", "items": ""}
        data.update({"items": items})
        return data
    #dialog = xbmcgui.DialogProgress()
    #dialog.create('Đang lấy dữ liệu', 'Vui lòng đợi...')
    # Kiểm tracache
    cache_filename = hashlib.md5(url.encode()).hexdigest() + '_cache.json'
    cache_path = os.path.join(CACHE_PATH, cache_filename)
    if cache_utils.check_cache(cache_path):
        with open(cache_path, 'r') as cache_file:
            cache_content = json.load(cache_file)
            #notify("cached")
        return cache_content
    else:
        data = getlink_tvcn(url,img)
        with open(cache_path, "w") as f:
            json.dump(data, f)
            #notify("fresh data")
        return data

       
def listMovie(url):
    def getlist(url):
        success = False
        for _ in range(3):
            try:
                response = urlquick.get(url, max_age=60*60, timeout=15)
                success = True
                break
            except ConnectionError:
                xbmcgui.Dialog().notification('Lỗi', 'Không kết nối được đến web', xbmcgui.NOTIFICATION_ERROR)
            except Timeout:
                xbmcgui.Dialog().notification('Lỗi', 'Yêu cầu đã vượt quá thời gian chờ', xbmcgui.NOTIFICATION_ERROR)
            except RequestException:
                xbmcgui.Dialog().notification('Lỗi', 'Có lỗi xảy ra trong quá trình yêu cầu', xbmcgui.NOTIFICATION_ERROR)
    
        if not success:
            alert("Không lấy được nội dung từ trang web")
            return None
        #response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        divs = soup.find_all("div", {"id": lambda x: x and x.startswith("post-")})
        items = []
        t =len(divs)
        i = 0
        for div in divs:
            name = div.find('h2', class_='movie-title').text.strip()
            vietsub = div.find("span", class_=lambda value: value and value.startswith("item-quality"))
            if vietsub:
                vietsub = vietsub.text.strip()
            else:
                vietsub = "No sub"
            rating = div.find("span", class_="movierating movierating-green")
            if rating:
                rating = rating.text.strip()
                rating = "Rating: [COLOR yellow]%s[/COLOR]" % rating
            else:
                rating = ""
            
            img = div.find("img", class_="lazy")
            if img:
                img = img.get("data-src")
            else:
                img = ""
            description = div.find("p", class_="movie-description")
            if description:
                description = description.text.strip()
                description = rating+"\n"+description
            else:
                description = ""
            year = div.find("span", class_="movie-date")
            if year:
                year = year.text.strip()
            else:
                year = ""
            link = div.find("a")["href"]
            genre_div = div.find("span", class_="genre")
            if genre_div:
                genre = genre_div.text.strip()
            else:
                genre = "N/A"
            progress = int(i) * 100 / t
            #dialog.update(int(progress), "Đang lên danh sách...")
            item = {}
            item["label"] = f"{name} [COLOR yellow]{vietsub}[/COLOR]"
            item["is_playable"] = False
            item["path"] = addon_url + "browse&url="+link
            item["thumbnail"] = img
            item["icon"] = img
            item["label2"] = "VMF"
            item["info"] = {'plot': description, 'genre': genre}
            items += [item]
            i +=1
            
        #Nextpage
        if "page" in url:
            next_page =  re.search(r"/(\d+)/$", url).group(1)
            next_page = int(next_page)+1
            base_url = re.search(r"(.*\/)page",url).group(1)
        else:
            next_page = "2"
            base_url = url
        next_page_url = base_url+"page/%s/" % next_page
        
        response = requests.head(next_page_url)
        status_code = response.status_code
        if status_code == 200:
        
            next_page_url = addon_url + "browse&url=vmf"+next_page_url
            nextpage = {"label": '[COLOR yellow]Trang %s[/COLOR] ' % next_page, "is_playable": False,
                        "path": next_page_url, "thumbnail": 'https://i.imgur.com/yCGoDHr.png', "icon": "https://i.imgur.com/yCGoDHr.png", "label2": "", "info": {'plot': 'Trang tiếp TVCN'}}
            items.append(nextpage)
        xbmc.executebuiltin('DialogProgress.close()')
        
        data = {"content_type": "movies", "items": ""}
        data.update({"items": items})
        if 'page/' not in url:
            item_adv = getadv()
            items_length = len(data["items"])
            random_position = random.randint(1, min(5, items_length + 1))
            data["items"].insert(random_position, item_adv)
        #dialog.close()
        return data
    
    #dialog = xbmcgui.DialogProgress()
    #dialog.create('Đang lấy dữ liệu', 'Vui lòng đợi...')
    # Kiểm tracache
    cache_filename = hashlib.md5(url.encode()).hexdigest() + '_cache.json'
    cache_path = os.path.join(CACHE_PATH, cache_filename)
    if cache_utils.check_cache(cache_path):
        # Đọc nội dung từ file cache
        with open(cache_path, 'r') as cache_file:
            cache_content = json.load(cache_file)
            #notify("cached")
        return cache_content
    else:
        data = getlist(url)
        with open(cache_path, "w") as f:
            json.dump(data, f)
            #notify("fresh data")
        return data
   
def receive(url):
    if "menu" in url:
        names = ["Tìm kiếm","Phim Lẻ","Phim Bộ","Xu hướng","Thể loại","Quốc gia","Chất lượng"]
        links = ["plugin://plugin.video.vietmediaF?action=browse&url=https://thuviencine.com/timkiem/",
                "plugin://plugin.video.vietmediaF?action=browse&url=https://thuviencine.com/movies/",
                "plugin://plugin.video.vietmediaF?action=browse&url=https://thuviencine.com/tv-series/",
                "plugin://plugin.video.vietmediaF?action=browse&url=https://thuviencine.com/top/",
                "plugin://plugin.video.vietmediaF?action=browse&url=https://thuviencine.com/theloai",
                "plugin://plugin.video.vietmediaF?action=browse&url=https://thuviencine.com/quocgia","plugin://plugin.video.vietmediaF?action=browse&url=https://thuviencine.com/chatluong"]
        items = []
        
        for name, link in zip(names,links):
            item = {}
            item["label"] = name
            item["is_playable"] = False
            item["path"] = link
            item["thumbnail"] = "https://i.imgur.com/GXyTFfi.png"
            item["icon"] = "https://i.imgur.com/GXyTFfi.png"
            item["label2"] = ""
            item["info"] = {'plot': ''}
            item["art"] = {'fanart': "https://i.imgur.com/LkeOoN3.jpg"}
            items += [item]
        data = {"content_type": "episodes", "items": ""}
        data.update({"items": items})
        return data
    elif "tv-series" in url or "/top/" in url or "/movies/" in url or "vmf" in url:
        if "vmf" in url:
            url = url.replace("vmf","")
        match = re.search(r"url=(.*)",url)
        if match:
            url = match.group(1)
        data = listMovie(url)
        return data
    elif "theloai" in url:
        links = ['vmfhttps://thuviencine.com/adventure/', 'vmfhttps://thuviencine.com/chuong-trinh-truyen-hinh/', 'vmfhttps://thuviencine.com/kids/', 'vmfhttps://thuviencine.com/phim-bi-an/', 'vmfhttps://thuviencine.com/phim-chien-tranh/', 'vmfhttps://thuviencine.com/phim-chinh-kich/', 'vmfhttps://thuviencine.com/phim-gay-can/', 'vmfhttps://thuviencine.com/phim-gia-dinh/', 'vmfhttps://thuviencine.com/phim-gia-tuong/', 'vmfhttps://thuviencine.com/phim-hai/', 'vmfhttps://thuviencine.com/phim-hanh-dong/', 'vmfhttps://thuviencine.com/phim-hinh-su/', 'vmfhttps://thuviencine.com/phim-hoat-hinh/', 'vmfhttps://thuviencine.com/phim-khoa-hoc-vien-tuong/', 'vmfhttps://thuviencine.com/phim-kinh-di/', 'vmfhttps://thuviencine.com/phim-lang-man/', 'vmfhttps://thuviencine.com/phim-lich-su/', 'vmfhttps://thuviencine.com/phim-mien-tay/', 'vmfhttps://thuviencine.com/phim-nhac/', 'vmfhttps://thuviencine.com/phim-phieu-luu/', 'vmfhttps://thuviencine.com/phim-tai-lieu/', 'vmfhttps://thuviencine.com/reality/', 'vmfhttps://thuviencine.com/science-fiction/', 'vmfhttps://thuviencine.com/soap/', 'vmfhttps://thuviencine.com/war-politics/']
        names = ['Adventure', 'Chương Trình Truyền Hình', 'Kids', 'Phim Bí Ẩn', 'Phim Chiến Tranh', 'Phim Chính Kịch', 'Phim Gây Cấn', 'Phim Gia Đình', 'Phim Giả Tượng', 'Phim Hài', 'Phim Hành Động', 'Phim Hình Sự', 'Phim Hoạt Hình', 'Phim Khoa Học Viễn Tưởng', 'Phim Kinh Dị', 'Phim Lãng Mạn', 'Phim Lịch Sử', 'Phim Miền Tây', 'Phim Nhạc', 'Phim Phiêu Lưu', 'Phim Tài Liệu', 'Reality', 'Science Fiction', 'Soap', 'War & Politics']
        items = []
        for name, link in zip(names,links):
            item = {}
            item["label"] = name
            item["is_playable"] = False
            item["path"] = addon_url + "browse&url="+link
            item["thumbnail"] = ""
            item["icon"] = ""
            item["label2"] = ""
            item["info"] = {'plot': ''}
            items += [item]
        data = {"content_type": "episodes", "items": ""}
        data.update({"items": items})
        return data
    elif "quocgia" in url:
        country_urls = {
            'Việt Nam': 'vmfhttps://thuviencine.com/country/vietnam/',
            'Anh': 'vmfhttps://thuviencine.com/country/united-kingdom/',
            'Argentina': 'vmfhttps://thuviencine.com/country/argentina/',
            'Australia': 'vmfhttps://thuviencine.com/country/australia/',
            'Austria': 'vmfhttps://thuviencine.com/country/austria/',
            'Belgium': 'vmfhttps://thuviencine.com/country/belgium/',
            'Bosnia and Herzegovina': 'vmfhttps://thuviencine.com/country/bosnia-and-herzegovina/',
            'Brazil': 'vmfhttps://thuviencine.com/country/brazil/',
            'Cambodia': 'vmfhttps://thuviencine.com/country/cambodia/',
            'Canada': 'vmfhttps://thuviencine.com/country/canada/',
            'Chile': 'vmfhttps://thuviencine.com/country/chile/',
            'China': 'vmfhttps://thuviencine.com/country/china/',
            'Colombia': 'vmfhttps://thuviencine.com/country/colombia/',
            'Czech Republic': 'vmfhttps://thuviencine.com/country/czech-republic/',
            'Denmark': 'vmfhttps://thuviencine.com/country/denmark/',
            'Dominican Republic': 'vmfhttps://thuviencine.com/country/dominican-republic/',
            'Estonia': 'vmfhttps://thuviencine.com/country/estonia/',
            'Finland': 'vmfhttps://thuviencine.com/country/finland/',
            'France': 'vmfhttps://thuviencine.com/country/france/',
            'Germany': 'vmfhttps://thuviencine.com/country/germany/',
            'Greece': 'vmfhttps://thuviencine.com/country/greece/',
            'Hong Kong': 'vmfhttps://thuviencine.com/country/hong-kong/',
            'Hungary': 'vmfhttps://thuviencine.com/country/hungary/',
            'Iceland': 'vmfhttps://thuviencine.com/country/iceland/',
            'India': 'vmfhttps://thuviencine.com/country/india/',
            'Indonesia': 'vmfhttps://thuviencine.com/country/indonesia/',
            'Ireland': 'vmfhttps://thuviencine.com/country/ireland/',
            'Israel': 'vmfhttps://thuviencine.com/country/israel/',
            'Italy': 'vmfhttps://thuviencine.com/country/italy/',
            'Japan': 'vmfhttps://thuviencine.com/country/japan/',
            'Korea': 'vmfhttps://thuviencine.com/country/korea/',
            'Latvia': 'vmfhttps://thuviencine.com/country/latvia/',
            'Lithuania': 'vmfhttps://thuviencine.com/country/lithuania/',
            'Luxembourg': 'vmfhttps://thuviencine.com/country/luxembourg/',
            'Malaysia': 'vmfhttps://thuviencine.com/country/malaysia/',
            'Mexico': 'vmfhttps://thuviencine.com/country/mexico/',
            'Mỹ': 'vmfhttps://thuviencine.com/country/my/',
            'N/A': 'vmfhttps://thuviencine.com/country/n-a/',
            'Netherlands': 'vmfhttps://thuviencine.com/country/netherlands/',
            'New Zealand': 'vmfhttps://thuviencine.com/country/new-zealand/',
            'Nigeria': 'vmfhttps://thuviencine.com/country/nigeria/',
            'Norway': 'vmfhttps://thuviencine.com/country/norway/',
            'Peru': 'vmfhttps://thuviencine.com/country/peru/',
            'Philippines': 'vmfhttps://thuviencine.com/country/philippines/',
            'Phim bộ Mỹ': 'vmfhttps://thuviencine.com/country/phim-bo-my/',
            'Poland': 'vmfhttps://thuviencine.com/country/poland/',
            'Portugal': 'vmfhttps://thuviencine.com/country/portugal/',
            'Romania': 'vmfhttps://thuviencine.com/country/romania/',
            'Russia': 'vmfhttps://thuviencine.com/country/russia/',
            'Singapore': 'vmfhttps://thuviencine.com/country/singapore/',
            'Slovakia': 'vmfhttps://thuviencine.com/country/slovakia/',
            'South Africa': 'vmfhttps://thuviencine.com/country/south-africa/',
            'South Korea': 'vmfhttps://thuviencine.com/country/south-korea/',
            'Spain': 'vmfhttps://thuviencine.com/country/spain/',
            'Sweden': 'vmfhttps://thuviencine.com/country/sweden/',
            'Switzerland': 'vmfhttps://thuviencine.com/country/switzerland/',
            'Taiwan': 'vmfhttps://thuviencine.com/country/taiwan/',
            'Thailand': 'vmfhttps://thuviencine.com/country/thailand/',
            'Tunisia': 'vmfhttps://thuviencine.com/country/tunisia/',
            'Turkey': 'vmfhttps://thuviencine.com/country/turkey/',
            'UK': 'vmfhttps://thuviencine.com/country/uk/',
            'Ukraine': 'vmfhttps://thuviencine.com/country/ukraine/',
            'Uruguay': 'vmfhttps://thuviencine.com/country/uruguay/',
            'Venezuela': 'vmfhttps://thuviencine.com/country/venezuela/'
        }

        items = []
        for country, link in country_urls.items():
            item = {
                "label": country,
                "is_playable": False,
                "path": addon_url + "browse&url=" + link,
                "thumbnail": "",
                "icon": "",
                "label2": "",
                "info": {'plot': ''}
            }
            items.append(item)

        data = {"content_type": "episodes", "items": items}
        return data

    elif "chatluong" in url:
        links=['vmfhttps://thuviencine.com/quality/vietsub/', 'vmfhttps://thuviencine.com/quality/tm-pd/', 'vmfhttps://thuviencine.com/quality/tm-lt-pd/', 'vmfhttps://thuviencine.com/quality/tm/', 'vmfhttps://thuviencine.com/quality/raw/', 'vmfhttps://thuviencine.com/quality/phim-viet/', 'vmfhttps://thuviencine.com/quality/new/', 'vmfhttps://thuviencine.com/quality/lt-pd/', 'vmfhttps://thuviencine.com/quality/lt/', 'vmfhttps://thuviencine.com/quality/hd/', 'vmfhttps://thuviencine.com/quality/engsub/', 'vmfhttps://thuviencine.com/quality/cam-vietsub/', 'vmfhttps://thuviencine.com/quality/cam/', 'vmfhttps://thuviencine.com/quality/bluray-vietsub/', 'vmfhttps://thuviencine.com/quality/bluray-tm-pd/', 'vmfhttps://thuviencine.com/quality/bluray/', 'vmfhttps://thuviencine.com/quality/4k-vietsub/', 'vmfhttps://thuviencine.com/quality/4k-tm/', 'vmfhttps://thuviencine.com/quality/4k-lt/', 'vmfhttps://thuviencine.com/quality/4k/']
        names= ['Vietsub', 'TM - PĐ', 'TM - LT - PĐ', 'TM', 'Raw', 'Phim Việt', 'NEW', 'LT - PĐ', 'LT', 'HD', 'Engsub', 'CAM Vietsub', 'CAM', 'Bluray Vietsub', 'Bluray TM - PĐ', 'Bluray', '4K Vietsub', '4K TM', '4K LT', '4K']
        items = []
        for name, link in zip(names,links):
            item = {}
            item["label"] = name
            item["is_playable"] = False
            item["path"] = addon_url + "browse&url="+link
            item["thumbnail"] = ""
            item["icon"] = ""
            item["label2"] = ""
            item["info"] = {'plot': ''}
            items += [item]
        data = {"content_type": "episodes", "items": ""}
        data.update({"items": items})
        return data
        
        
    elif "/timkiem/" in url:
        history_file = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.vietmediaF/search_history.json')

        def load_history():
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []

        def save_history(query):
        
            history_dir = os.path.dirname(history_file)
            if not os.path.exists(history_dir):
                os.makedirs(history_dir)

        
            history = load_history()
            if query not in history:
                history.append(query)
                with open(history_file, 'w', encoding='utf-8') as f:
                    json.dump(history, f, ensure_ascii=False)

        
        def clear_history():
            if os.path.exists(history_file):
                os.remove(history_file)
                alert("Lịch sử tìm kiếm đã được xóa.")

        
        history = load_history()

        
        dialog = xbmcgui.Dialog()
        if history:
            options = ["[COLOR yellow]Nhập từ khóa mới[/COLOR]", "[COLOR yellow]Xóa lịch sử[/COLOR]"] + history
            choice = dialog.select("Chọn hoặc nhập từ khóa tìm kiếm:", options)

            if choice == -1:  # Người dùng bấm Cancel
                notify("Bạn đã hủy tìm kiếm")
                xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=False)
                return None

            if choice == 0:  # Nhập từ khóa mới
                keyboard = xbmc.Keyboard("", "Nhập tên phim tiếng Anh")
                keyboard.doModal()
                if keyboard.isConfirmed() and keyboard.getText():
                    query = keyboard.getText()
                    query = urllib.parse.unquote(query)
                    save_history(query)
                    url = "https://thuviencine.com/?s=%s" % query
                    data = listMovie(url)
                    return data
                else:
                    notify("Hủy tìm kiếm")
                    xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=False)
                    return None
            elif choice == 1:  # Xóa lịch sử
                confirm = dialog.yesno("Xác nhận", "Bạn có chắc chắn muốn xóa toàn bộ lịch sử tìm kiếm không?")
                if confirm:
                    clear_history()
                return None
            elif choice > 1:  # Chọn từ lịch sử
                query = history[choice - 2]
                url = "https://thuviencine.com/?s=%s" % query
                data = listMovie(url)
                return data
        else:
            # Nếu chưa có lịch sử, nhập mới
            keyboard = xbmc.Keyboard("", "Nhập tên phim tiếng Anh")
            keyboard.doModal()
            if keyboard.isConfirmed() and keyboard.getText():
                query = keyboard.getText()
                query = urllib.parse.unquote(query)
                save_history(query)
                url = "https://thuviencine.com/?s=%s" % query
                data = listMovie(url)
                return data
            else:
                notify("Hủy tìm kiếm")
                xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=False)  
                return

    else:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        movie_image = soup.find("div", class_="movie-image")
        if movie_image:
            image = movie_image.find("img")["src"]
        else:image=""
            
        download_button = soup.find("li", id="download-button")
        if download_button:
            link = download_button.find("a")["href"]
            data = getlink(link,image)
        else:
            alert("Không tìm thấy link. Thử lại sau")
            exit()
        return data