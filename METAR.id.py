import flet
from flet import *
import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
import math
import webbrowser
import re
import unicodedata
import threading
import time
import os
import sys
import apptype
import squroute

load_url = "https://www.imoc.co.jp/SmartPhone/d/metar.php"
metars = {}
specialKey = ["VERSION","VATSIM","VATJPN","SANSUKE","TEMP","SQUAWK.ID","SOURCE","METAR.ID"]
version = "v0.5.4-beta"
filepath = os.path.dirname(os.path.abspath(sys.argv[0]))
textFiles = ["RWYData.txt","AIRCRAFT.txt","AIRLINES.txt"]
text_width = [34,40,48,40,45]

RWYData = {}
aircrafts = {}
airlines = {}
fixnames = {}

jumbo_mode = False
color_mode = 0
args = sys.argv
for arg in args:
    if arg == "-jumbo":
        jumbo_mode = True
        text_width = [34,32,40,24,45]
    if arg == "-dark":
        color_mode = 1
    if arg == "-light":
        color_mode = 2

def check_version():
    try:
        corrent_version = requests.get("https://raw.githubusercontent.com/sansuke1005/METAR.id/main/current_version.txt",timeout=3.5).text
    except RequestException:
        return 3
    if corrent_version == "404: Not Found":
        return 2
    if version == corrent_version:
        return 0
    return 1
    
def load_text_file():
    for s in textFiles:
        if not os.path.isfile(os.path.join(filepath, s)):
            return s

    with open(os.path.join(filepath, textFiles[0])) as f:
        flines = f.readlines()
        del flines[0]
        for data in flines:
            dataList = data.split(",")
            RWYData[dataList[0]]=[dataList[1],dataList[2],dataList[3],dataList[4],dataList[5],dataList[6].strip()]
    with open(os.path.join(filepath, textFiles[1])) as f:
        flines = f.readlines()
        del flines[0]
        for data in flines:
            dataList = data.split(",")
            if not dataList[0] in aircrafts.keys():
                aircrafts[dataList[0]]=[dataList[1],dataList[2],dataList[3].strip()]
    with open(os.path.join(filepath, textFiles[2])) as f:
        flines = f.readlines()
        del flines[0]
        for data in flines:
            dataList = data.split(",")
            if not dataList[0] in airlines.keys():
                airlines[dataList[0]]=[dataList[1],dataList[2],dataList[3],dataList[4].strip()]
    if os.path.isfile(os.path.join(filepath, "FIXNAMES.txt")):
        with open(os.path.join(filepath, "FIXNAMES.txt")) as f:
            flines = f.readlines()
            del flines[0]
            for data in flines:
                dataList = data.split(",")
                if not dataList[0] in fixnames.keys():
                    fixnames[dataList[0]]=dataList[2]
    return ""


def getMetar(port):
    if len(port)==1:
        port = "RJ" + port + port
    elif len(port)==2:
        port = "RJ" + port
    params = {'Area': '0', 'Port': port}
    html = requests.get(load_url, params=params)
    soup = BeautifulSoup(html.content, "html.parser")
    lines = soup.find("ul").text
    lines_list = re.sub("\n +", " ", lines).split("\n")
    for s in lines_list:
        if len(s) > 15:
            if "NIL" not in s:
                if s[:5] == "METAR":
                    return s[6:]
                return s
    return "Error"

def codeConvert(port):
    if len(port)==1:
        return "RJ" + port + port
    elif len(port)==2:
        return "RJ" + port
    elif len(port)==3:
        return "R" + port
    return port

def metar_summary(s):
    if s == "Error":
        return "Error"
    metar_split = s.split(" ")
    if metar_split[2] == "AUTO" or metar_split[2] == "COR":
        del metar_split[2]
    if "NIL" in metar_split[2]:
        metar_short = [metar_split[0],metar_split[1][2:],"N/A","N/A","0"]
        return " ".join(metar_short)
    QNH = "ERROR"
    availFL = ""
    for i in range(len(metar_split)):
        QNH_temp = metar_split[len(metar_split)-i-1]
        if QNH_temp[0] == "A":
            if len(QNH_temp) == 5 or len(QNH_temp) == 6:
                if QNH_temp[1:5].isdecimal():
                        QNH = QNH_temp[:5]
                        if int(QNH[1:]) < 2942:
                            availFL = "2"
                            break
                        if int(QNH[1:]) < 2992:
                            availFL = "1"
                            break
                        break
    metar_short = [metar_split[0],metar_split[1][2:],metar_split[2][:3]+"@"+metar_split[2][3:5],QNH,availFL]
    return " ".join(metar_short)

def getAiportName(port):
    airportName = RWYData[port][4] + " ("+RWYData[port][5]+")"
    return airportName

def get_tt_IAP():
    return apptype.get_rjtt_app()

def getRecommendRWY(port, metar_short):
    priy_rwy = RWYData[port][0]
    oppo_rwy = RWYData[port][1]
    wind = metar_short[2]
    if "N/A" in wind:
        return ["RWY" + priy_rwy.zfill(2),0]
    if wind[:3] == "VRB":
        return ["RWY" + priy_rwy.zfill(2),0]
    wind_d = int(wind[:3])
    wind_v = int(wind[4:])
    wind_limit = int(RWYData[port][2])
    wind_diff = int(priy_rwy)*10 - wind_d
    wind_t = -math.cos(math.radians(wind_diff))*wind_v
    recommendRWY = ""
    if wind_t < wind_limit:
        if wind_t > 0:
            return ["RWY" + priy_rwy.zfill(2),1]
        else:
            return ["RWY" + priy_rwy.zfill(2),0]
    return ["RWY" + oppo_rwy.zfill(2),0]

def chekIMC(metar):
    if metar == "Error":
        return False
    metar_split = metar.split(" ")
    if metar_split[2] == "AUTO" or metar_split[2] == "COR":
        del metar_split[2]

    if "NIL" in metar_split[2]:
        return False
    
    if "TEMPO" in metar_split:
        metar_split = metar_split[:metar_split.index("TEMPO")]
    
    if "BECMG" in metar_split:
        metar_split = metar_split[:metar_split.index("BECMG")]


    for s in metar_split:
        if s.isdecimal():
            if int(s) < 5000:
                return True

    for s in metar_split:
        if "BKN" in s or "OVC" in s :
            if s[3:].isdecimal():
                if int(s[3:]) < 10:
                    return True
    return False

def getAircraft(s):
    if s not in aircrafts.keys():
        return None
    aircarft = aircrafts[s]
    out = [s]
    menus = ["Company","Type","WT Cat"]
    for i in range(3):
        out.append(menus[i]+": "+aircarft[i])
    return "\n".join(out)

def getAirline(s):
    if s not in airlines.keys():
        return None
    airline = airlines[s]
    out = [s]
    menus = ["Company","Callsign","Country"]
    for i in range(3):
        out.append(menus[i]+": "+airline[i])
    return "\n".join(out)

def special(s):
    if s == specialKey[0]:
        return "Version = "+version
    if s == specialKey[1]:
        webbrowser.open("https://vatsim.net/", new=0, autoraise=True)
    if s == specialKey[2]:
        webbrowser.open("https://vatjpn.org/", new=0, autoraise=True)
    if s == specialKey[3]:
        webbrowser.open("https://x.com/sansuke1005", new=0, autoraise=True)
    if s == specialKey[4]:
        webbrowser.open("https://vatjpn.org/document/public/crc/78/171", new=0, autoraise=True)
    if s == specialKey[5]:
        webbrowser.open("https://squawk.id/", new=0, autoraise=True)
    if s == specialKey[6]:
        webbrowser.open(load_url, new=0, autoraise=True)
    if s == specialKey[7]:
        webbrowser.open("https://github.com/sansuke1005/METAR.id", new=0, autoraise=True)
    return ""    

def get_fix_name(s):
    if s not in fixnames.keys():
        return None
    fixname = "Name: " + fixnames[s]
    return s + "\n" + fixname

def get_route(s):
    routes = squroute.get_route(s.split(" ")[0],s.split(" ")[1])
    route = routes[0]
    if route == "ERROR":
        return ["Not Found","",""]
    
    if route[2] == "" and route[1] == "":
        route_info = "{}".format(route[0])
    if route[2] == "" and route[1] != "":
        route_info = "{}\n({})".format(route[0],route[1])
    if route[2] != "" and route[1] == "":
        route_info = "{}\n({})".format(route[0],route[2])
    if route[2] != "" and route[1] != "":
        route_info = "{}\n({}, {})".format(route[0],route[2],route[1])
    
    if routes[2]-1 == 0:
        return [route_info,routes[1],""]
    if routes[2]-1 == 1:
        return [route_info,routes[1],"more {} route".format(str(routes[2]-1))]
    return [route_info,routes[1],"more {} routes".format(str(routes[2]-1))]

def autoSelector(s):
    if len(s.split(" "))==2:
        get_routes = get_route(s)
        return [get_routes[0],get_routes[1],get_routes[2]]
    if s == "/" or s == "CLR" or s == "CLEAR":
        return ["","CLEAR",""]
    if s in specialKey:
        return [special(s),None,""]
    if s.isdecimal() and (len(s)==6 or len(s)==7):
        webbrowser.open("https://stats.vatsim.net/stats/"+s, new=0, autoraise=True)
        return ["",None,""]
    if s == "HND":
        return [apptype.get_rjtt_app_all(),"RJTT INFO",""]
    if len(s)==1:
        port = "RJ"+s+s
        if port in RWYData.keys():
            return [getMetar(port),"METAR",""]
    if len(s)==2:
        port = "RJ"+s
        if port in RWYData.keys():
            return [getMetar(port),"METAR",""]
    if len(s)==3 and s[0] == "O":
        port = "R"+s
        if port in RWYData.keys():
            return [getMetar(port),"METAR",""]
    if s[:2] == "RJ" or s[:2] == "RO":
        if s in RWYData.keys():
            return [getMetar(s),"METAR",""]
    if get_fix_name(s) != None:
        return [get_fix_name(s),"Fix",""]
    if getAircraft(s) != None:
        return [getAircraft(s),"Aircraft",""]
    if getAirline(s) != None:
        return [getAirline(s),"Airline",""]
    return ["Error",None,""]

class NewThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        threading.Thread.__init__(self, group, target, name, args, kwargs)

    def run(self):
        if self._target != None:
            self._return = self._target(*self._args, **self._kwargs)

    def join(self, *args):
        threading.Thread.join(self, *args)
        return self._return

class Task(UserControl):
    def __init__(self, task_name, task_delete, task_clicked, sortedMetar):
        super().__init__()
        self.task_name = codeConvert(task_name)
        self.task_delete = task_delete
        self.task_clicked = task_clicked
        self.sortedMetar = sortedMetar

    def build(self):
        if self.task_name in metars.keys():
            return Column()
        self.thread_getIAP = NewThread(target=get_tt_IAP)
        if self.task_name == "RJTT":
            self.thread_getIAP.start()
        if len(self.sortedMetar) == 0:
            self.metar = getMetar(self.task_name)
        else:
            self.metar = self.sortedMetar
        self.metar_short = metar_summary(self.metar).split(" ")
        if self.metar_short[0] == "Error":
            return Column()
        metars[self.task_name]=self.metar

        if self.task_name == "RJTT":
            self.recommendRWY = [self.thread_getIAP.join(),2]
        else:
            self.recommendRWY = getRecommendRWY(self.metar_short[0],self.metar_short)
        self.textStyleQNH = TextStyle(
                                        decoration_thickness = 2,
                                        decoration_color=colors.GREY_600,
                                        size=13, 
                                    )
        self.textRWY = Text(
                            spans=[
                                TextSpan(
                                    self.recommendRWY[0],
                                    ),
                                ],
                            text_align = TextAlign.CENTER,
                            size=13,
                            no_wrap=True,
                            overflow=TextOverflow.VISIBLE,
                        )
        if self.metar_short[4] == "1":
            self.textStyleQNH.decoration=TextDecoration.UNDERLINE
        if self.metar_short[4] == "2":
            self.textStyleQNH.decoration=TextDecoration.UNDERLINE
            self.textStyleQNH.decoration_color=colors.RED
        if self.recommendRWY[1] == 1:
            self.textRWY.color = colors.RED
        if self.recommendRWY[1] == 2:
            self.textRWY.color = colors.PRIMARY

        if jumbo_mode:
            self.metar_code = self.metar_short[0]
            self.metar_time = self.metar_short[1][:4]
            self.metar_wind = self.metar_short[2].replace("@","")
            self.metar_QNH = self.metar_short[3][len(self.metar_short[3])-3:]
        else:
            self.metar_code = self.metar_short[0]
            self.metar_time = self.metar_short[1]
            self.metar_wind = self.metar_short[2]
            self.metar_QNH = self.metar_short[3]

        self.display_view = Container(
            Row(
                alignment="spaceBetween",
                vertical_alignment="center",
                height=26,
                controls=[
                    Container(
                        Text(
                            spans=[
                                TextSpan(
                                    self.metar_code,
                                    ),
                                ],
                            text_align = TextAlign.CENTER,
                            size=13,
                            no_wrap=True,
                            overflow=TextOverflow.VISIBLE,
                        ),
                        width=text_width[0],
                    ),
                    Container(
                        Text(
                            spans=[
                                TextSpan(
                                        self.metar_time,
                                    ),
                                ],
                            text_align = TextAlign.CENTER,
                            size=13,
                            no_wrap=True,
                            overflow=TextOverflow.VISIBLE,
                        ),
                        width=text_width[1],
                    ),
                    Container(
                        Text(
                            spans=[
                                TextSpan(
                                        self.metar_wind, 
                                    ),
                                ],
                            text_align = TextAlign.CENTER,
                            size=13,
                            no_wrap=True,
                            overflow=TextOverflow.VISIBLE,
                        ),
                        width=text_width[2],
                    ),
                    Container(
                        Text(
                            spans=[
                                TextSpan(
                                    self.metar_QNH, 
                                    self.textStyleQNH, 
                                    ),
                                ],
                                text_align = TextAlign.CENTER,
                                no_wrap=True,
                                overflow=TextOverflow.VISIBLE,
                            ),
                        width=text_width[3],
                    ),
                    Container(
                        self.textRWY,
                        width=text_width[4],
                    ),

                    IconButton(
                        icons.DELETE_OUTLINE,
                        on_click=self.delete_clicked,
                        icon_size=18,
                        width=20,
                        
                        style=ButtonStyle(
                            color={
                                MaterialState.HOVERED: colors.RED,
                                MaterialState.DEFAULT: colors.ON_BACKGROUND,
                            },
                            overlay_color=colors.with_opacity(0, colors.PRIMARY),
                            padding=1,
                        ),
                    ),
                ],
            ),
            ink=True,
            on_click=self.container_clicked,
            padding= padding.only(left=5,right=7),
        )
        if chekIMC(self.metar):
            self.display_view.bgcolor = colors.with_opacity(0.1, colors.RED)
        return Column(controls=[self.display_view],spacing=0,)
    
    def container_clicked(self, e):
        self.task_clicked(self,getAiportName(self.task_name)+"\n"+metars[self.task_name],"METAR","")

    def delete_clicked(self, e):
        metars.pop(self.task_name)
        self.task_delete(self)


class TodoApp(UserControl):
    def __init__(self, window_on_top):
        super().__init__()
        self.window_on_top = window_on_top

    def build(self):
        self.new_task = TextField(
            text_size=13,
            expand=True, 
            on_submit=self.add_clicked, 
            on_change=self.check_alnum,
            content_padding= padding.only(left=5),
            border_color = colors.OUTLINE,
            autofocus = True,
        )
        self.tasks = Column(spacing=0, scroll=ScrollMode.AUTO, )
        
        self.info = TextField(
            text_size=13,
            multiline=True,
            read_only=True,
            value="",
            min_lines=4,
            max_lines=4,
            content_padding= 5,
            border_color = colors.OUTLINE_VARIANT,
            focused_border_color = colors.OUTLINE_VARIANT,
            focused_border_width = 1,
            label=None,
            label_style = TextStyle(
                size = 13,
                color = colors.OUTLINE_VARIANT,
            )
        )
        self.info = TextField(
            text_size=13,
            multiline=True,
            read_only=True,
            value="",
            min_lines=4,
            max_lines=4,
            content_padding= 5,
            border_color = colors.OUTLINE_VARIANT,
            focused_border_color = colors.OUTLINE_VARIANT,
            focused_border_width = 1,
            label=None,
            label_style = TextStyle(
                size = 13,
                color = colors.OUTLINE_VARIANT,
            )
        )
        self.info_text = TextSpan(
            text ="",
            style = TextStyle(color=colors.BLUE),
            url="",
            on_enter=self.highlight_link,
            on_exit=self.unhighlight_link,
        )
        self.pb = ProgressBar(color=colors.PRIMARY, bgcolor=colors.BACKGROUND, value=0,bar_height=3)
        self.info_box = Column([
            Stack([
                    self.info,
                    Container(
                        Text(
                            spans=[
                                self.info_text,
                                ],
                            size=13,
                        ),
                        right=3,
                        bottom=3,
                    ),
                ]),
            self.pb,
            ],
            spacing=2,
            
        )

        self.t = CustomThread1(self.reload_clicked)
        self.t.start()



        return Column([
                Row(
                    spacing=5,
                    height=30,
                    controls=[
                        self.new_task,
                        IconButton(
                            width=14,
                            icon_size=15,
                            icon=icons.PUSH_PIN_OUTLINED,
                            selected_icon=icons.PUSH_PIN,
                            on_click=self.toggle_icon_button,
                            selected=False,
                            style=ButtonStyle(color={"selected": colors.ON_BACKGROUND, "": colors.OUTLINE},overlay_color=colors.with_opacity(0, colors.PRIMARY),padding=0),
                        ),
                        IconButton(
                            width=14,
                            icon_size=15,
                            icon=icons.SORT,
                            on_click=self.sort,
                            style=ButtonStyle(color={"selected": colors.ON_BACKGROUND, "": colors.OUTLINE},overlay_color=colors.with_opacity(0, colors.PRIMARY),padding=0),
                        ),
                        ElevatedButton(
                            content=Container(
                                    Icon(name=icons.CACHED),
                            ),
                            on_click=self.reload_clicked,
                            width=30,
                            style=ButtonStyle(
                                color=colors.ON_BACKGROUND,
                                bgcolor={
                                        MaterialState.DEFAULT: colors.PRIMARY_CONTAINER,
                                    },
                                padding=0,
                                shape=RoundedRectangleBorder(radius=5),
                                ),
                        ),
                        
                    ],
                ),
                Container(
                    self.tasks,
                    expand=True,
                ),
                Container(
                    self.info_box,
                ),
            ],
            spacing=5,
        )
        
    

    def add_clicked(self, e):
        self.pb.value = None
        self.update()
        info = autoSelector(self.new_task.value)
        if info[1] == "METAR":
            task = Task(self.new_task.value, self.task_delete, self.task_clicked, [])
            self.task_clicked(None, getAiportName(task.task_name)+"\n"+info[0], info[1],"")
            self.tasks.controls.append(task)
            self.tasks.scroll_to(offset=-1, duration=500)
        elif info[1] == "CLEAR":
            self.tasks.controls = []
            metars.clear()
        else:
            self.task_clicked(None, info[0], info[1],info[2])
        self.new_task.value = ""
        self.pb.value = 0
        self.new_task.focus()
        self.update()


    def check_alnum(self,e):
        if re.compile("[a-zA-Z0-9]+").match(self.new_task.value):
            hankaku=True
            for c in self.new_task.value:
                if not unicodedata.east_asian_width(c) == "Na":
                    hankaku=False
            if hankaku==True:
                self.new_task.value = self.new_task.value.upper()
                self.update()
            


    def task_delete(self, task):
        self.tasks.controls.remove(task)
        self.update()

    def task_clicked(self, task, new_info, info_label, text):
        self.info.value = new_info
        self.info.label = info_label
        self.info_text.text = text
        if info_label is None:
            self.info_text.url = ""
        else:
            self.info_text.url = squroute.get_url()+"?from={}&to={}".format(info_label[0:4],info_label[5:9])
        self.update()

    def reload_clicked(self, e):
        self.pb.value = None
        self.update()
        if self.pb.value == "":
            self.tasks.controls = []
            metars_copy = metars.copy()
            metars.clear()
            for key in metars_copy:
                new_task = Task(key, self.task_delete, self.task_clicked, [])
                self.tasks.controls.append(new_task)
        self.pb.value = 0
        self.update()

    def sort(self, e):
        self.pb.value = None
        self.update()
        if self.pb.value == "":
            self.tasks.controls = []
            metars_sort = sorted(metars.items())    #変更
            metars_sort = dict((x, y) for x, y in metars_sort)
            metars.clear()
            for key in metars_sort:
                new_task = Task(key, self.task_delete, self.task_clicked, metars_sort[key])
                self.tasks.controls.append(new_task)
        self.pb.value = 0
        self.update()

    def toggle_icon_button(self, e):
        e.control.selected = not e.control.selected
        self.window_on_top(e.control.selected)
        e.control.update()

    def highlight_link(self,e):
        e.control.style.decoration = TextDecoration.UNDERLINE
        e.control.update()

    def unhighlight_link(self,e):
        e.control.style.decoration = TextDecoration.NONE
        e.control.update()

def main(page: Page):
    page.title = "Metar.ID"
    if color_mode == 1:
        page.theme_mode = "DARK"
    if color_mode == 2:
        page.theme_mode = "LIGHT"
    page.window_width = 300
    page.window_height = 395
    page.window_min_width = 300
    page.window_min_height = 216
    page.window_maximizable = False
    #page.window_resizable = False
    page.theme = theme.Theme(color_scheme_seed='blue')
    page.update()

    def window_on_top(b):
        page.window_always_on_top = b
        page.update()

    app = TodoApp(window_on_top)
    app.expand = True
    page.add(app)


    version_status = check_version()
    def dlf_update(e):
        if version_status == 1:
            webbrowser.open("https://github.com/sansuke1005/METAR.id/releases", new=0, autoraise=True)
        page.window_destroy()

    dlg_update = AlertDialog(
        modal=True,

        actions_alignment=MainAxisAlignment.END,
    )
    status_title = ["","アップデートがあります","アプリは現在使用できません","ネットワークエラー"]
    if version_status != 0:
        time.sleep(0.1)
        page.dialog = dlg_update
        dlg_update.title = Text(status_title[version_status])
        if version_status == 1:
            dlg_update.actions = [TextButton("Go to Github", on_click=dlf_update)]
        else:
            dlg_update.actions = [TextButton("OK", on_click=dlf_update)]
        dlg_update.open = True
        page.update()

    def dlf_clicked(e):
        page.window_destroy()

    dlg_modal = AlertDialog(
        modal=True,
        title=Text("ファイルが見つかりません"),
        actions=[
            TextButton("OK", on_click=dlf_clicked),
        ],
        actions_alignment=MainAxisAlignment.END,
    )
    isTextLoaded = load_text_file()

    if not isTextLoaded == "":
        time.sleep(0.1)
        page.dialog = dlg_modal
        dlg_modal.content = Text(isTextLoaded)
        dlg_modal.open = True
        page.update()

class CustomThread1(threading.Thread):
  def __init__(self, reload_clicked):
    super().__init__()
    self.reload_clicked = reload_clicked
  
  def run(self):
    while True:
        time.sleep(300)
        self.reload_clicked(None)

flet.app(target=main)
