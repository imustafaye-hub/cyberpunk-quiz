import json
import flet as ft
from datetime import datetime, timedelta
import random
import threading
import wikipedia # Yeni kütüphanemiz
from plyer import notification

# --- AYARLAR ---
DATA_FILE = "questions.json"
STATS_FILE = "user_stats.json"

# --- CYBERPUNK RENKLER ---
BG_COLOR = "#0f0f1f"
CARD_COLOR = "#1a1a2e"
PRIMARY_COLOR = "#00f3ff"
SECONDARY_COLOR = "#bf00ff"
TEXT_COLOR = "#ffffff"
CORRECT_COLOR = "#00ff9d"
WRONG_COLOR = "#ff0055"
CHAT_USER_COLOR = "#2d2d44"
CHAT_AI_COLOR = "#1e1e2f"

def main(page: ft.Page):
    page.title = "BrainQuiz Mobile"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG_COLOR
    page.padding = 0
    
    # Wikipedia Dil Ayarı
    wikipedia.set_lang("tr")
    
    # --- VERİ YÖNETİMİ ---
    def load_data(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return [] if filename == DATA_FILE else {"streak": 0}

    def save_data(filename, data):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    questions = load_data(DATA_FILE)
    stats = load_data(STATS_FILE)
    if not isinstance(stats, dict): stats = {"streak": 0}
    
    current_question_idx = -1

    # --- 1. ÖZELLİK: BİLDİRİM SİSTEMİ ---
    def send_local_notification(title, message):
        try:
            notification.notify(
                title=title,
                message=message,
                app_name='BrainQuiz',
                timeout=5
            )
        except Exception as e:
            print(f"Bildirim hatası: {e}")

    def check_pending_reviews():
        now = datetime.now()
        count = 0
        for q in questions:
            date_str = q.get("next_review", "")
            if not date_str:
                count += 1
            else:
                try:
                    if datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S") <= now:
                        count += 1
                except:
                    count += 1
        
        if count > 0:
            send_local_notification("Tekrar Zamanı!", f"{count} adet soru seni bekliyor.")
            page.snack_bar = ft.SnackBar(ft.Text(f"📢 {count} soru tekrar bekliyor!"), bgcolor=SECONDARY_COLOR)
            page.snack_bar.open = True
            page.update()

    # --- UI PARÇALARI (Quiz) ---
    streak_text = ft.Text(f"🔥 Seri: {stats.get('streak', 0)}", size=20, weight="bold", color="orange")
    question_text = ft.Text("Yükleniyor...", size=20, weight="bold", color="white", text_align="center")
    topic_text = ft.Text("Konu: ...", size=12, italic=True, color="grey")
    answer_text = ft.Text("", size=16, color=CORRECT_COLOR, text_align="center", visible=False)
    img_container = ft.Image(src="", width=300, height=180, fit=ft.ImageFit.CONTAIN, visible=False)

    btn_show = ft.ElevatedButton("Cevabı Göster", width=200, style=ft.ButtonStyle(bgcolor=PRIMARY_COLOR, color="black"))
    btn_correct = ft.ElevatedButton("✅ Hatırladım", width=130, visible=False, style=ft.ButtonStyle(bgcolor=CORRECT_COLOR, color="black"))
    btn_wrong = ft.ElevatedButton("❌ Unuttum", width=130, visible=False, style=ft.ButtonStyle(bgcolor=WRONG_COLOR, color="white"))

    # --- 2. ÖZELLİK: WIKIPEDIA ASİSTANI ---
    chat_history = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    chat_input = ft.TextField(hint_text="Ne hakkında bilgi istersin?", expand=True, border_color=PRIMARY_COLOR)
    
    def perform_wiki_search(query):
        response = ""
        try:
            print(f"Wikipedia'da aranıyor: {query}")
            # sentences=3 -> Sadece ilk 3 cümleyi getirir (özet için ideal)
            summary = wikipedia.summary(query, sentences=3)
            response = f"📚 **Wikipedia Bilgisi:**\n\n{summary}"
            
        except wikipedia.exceptions.DisambiguationError as e:
            # Aranan kelimenin birden fazla anlamı varsa (örn: 'Mercury' -> gezegen mi element mi?)
            secenekler = ", ".join(e.options[:3])
            response = f"⚠️ Çok fazla sonuç var. Şunlardan birini mi kastettiniz?\n({secenekler})"
            
        except wikipedia.exceptions.PageError:
            response = "❌ Wikipedia'da bu konuyla ilgili bir sayfa bulunamadı."
            
        except Exception as e:
            response = f"Bir hata oluştu: {str(e)}"

        # UI Güncelleme
        chat_history.controls.append(
            ft.Container(
                content=ft.Text(response, color=PRIMARY_COLOR, selectable=True),
                bgcolor=CHAT_AI_COLOR,
                padding=10,
                border_radius=10,
                margin=ft.margin.only(right=50, bottom=10)
            )
        )
        page.update()

    def send_message(e):
        if not chat_input.value: return
        user_msg = chat_input.value
        
        chat_history.controls.append(
            ft.Container(
                content=ft.Text(user_msg, color="white"),
                bgcolor=CHAT_USER_COLOR,
                padding=10,
                border_radius=10,
                margin=ft.margin.only(left=50, bottom=5)
            )
        )
        
        loading_msg = ft.Text("Veri tabanı taranıyor...", italic=True, color="grey", size=12)
        chat_history.controls.append(loading_msg)
        
        query = chat_input.value
        chat_input.value = ""
        page.update()

        def search_thread():
            perform_wiki_search(query)
            if loading_msg in chat_history.controls:
                chat_history.controls.remove(loading_msg)
            page.update()

        threading.Thread(target=search_thread, daemon=True).start()

    btn_send = ft.IconButton(icon="search", icon_color=PRIMARY_COLOR, on_click=send_message)

    # Dosya Yükleme
    def pick_files_result(e: ft.FilePickerResultEvent):
        if e.files:
            try:
                with open(e.files[0].path, "r", encoding="utf-8") as f:
                    new_data = json.load(f)
                for item in new_data:
                    if not any(q['question'] == item['question'] for q in questions):
                        item.setdefault("next_review", "")
                        item.setdefault("level", 0)
                        questions.append(item)
                save_data(DATA_FILE, questions)
                page.snack_bar = ft.SnackBar(ft.Text("Sorular Yüklendi!"), bgcolor="green"); page.snack_bar.open = True
                load_ui_question()
                page.update()
            except: pass

    file_picker = ft.FilePicker(on_result=pick_files_result)
    page.overlay.append(file_picker)
    btn_upload = ft.ElevatedButton("📂 JSON Yükle", icon="upload_file", style=ft.ButtonStyle(bgcolor=SECONDARY_COLOR, color="white"), on_click=lambda _: file_picker.pick_files(allow_multiple=False, allowed_extensions=["json"]))

    # --- FONKSİYONLAR ---
    def get_due_question():
        nonlocal current_question_idx
        now = datetime.now()
        due_list = []
        for i, q in enumerate(questions):
            date_str = q.get("next_review", "")
            if not date_str: due_list.append((i, q)); continue
            try:
                if datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S") <= now: due_list.append((i, q))
            except: due_list.append((i, q))
        
        if due_list: current_question_idx, q = due_list[0]; return q
        return None

    def load_ui_question():
        q = get_due_question()
        if q:
            question_text.value = q["question"]
            topic_text.value = f"Konu: {q.get('topic', 'Genel')}"
            answer_text.value = q["answer"]
            answer_text.visible = False
            img_container.src = q.get("image", "")
            img_container.visible = True if q.get("image") else False
            btn_show.visible = True; btn_correct.visible = False; btn_wrong.visible = False
        else:
            question_text.value = "🎉 Tebrikler!\nTüm tekrarlar bitti."; topic_text.value = ""; answer_text.visible = False; btn_show.visible = False; btn_correct.visible = False; btn_wrong.visible = False
        page.update()

    def process_answer(is_correct):
        nonlocal current_question_idx
        if current_question_idx == -1: return
        q = questions[current_question_idx]
        now = datetime.now()
        if is_correct:
            lvl = q.get("level", 0) + 1
            days_add = [0, 1, 3, 7, 14, 30][min(lvl, 5)]
            today = datetime.now().strftime("%Y-%m-%d")
            if stats.get("last_study_date") != today:
                stats["streak"] = stats.get("streak", 0) + 1; stats["last_study_date"] = today
                streak_text.value = f"🔥 Seri: {stats['streak']}"
        else: lvl = 0; days_add = 0
        q["level"] = lvl
        q["next_review"] = (now + timedelta(minutes=10) if days_add == 0 else now + timedelta(days=days_add)).strftime("%Y-%m-%d %H:%M:%S")
        save_data(DATA_FILE, questions); save_data(STATS_FILE, stats)
        load_ui_question()

    btn_show.on_click = lambda e: [setattr(answer_text, 'visible', True), setattr(btn_show, 'visible', False), setattr(btn_correct, 'visible', True), setattr(btn_wrong, 'visible', True), page.update()]
    btn_correct.on_click = lambda e: process_answer(True)
    btn_wrong.on_click = lambda e: process_answer(False)

    # --- SEKMELER (TABS) ---
    quiz_content = ft.Container(
        padding=20,
        content=ft.Column([
            ft.Container(height=10),
            streak_text,
            ft.Container(height=20),
            ft.Container(
                content=ft.Column([topic_text, img_container, ft.Container(height=10), question_text, ft.Divider(color="grey"), answer_text], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD_COLOR, padding=20, border_radius=20, border=ft.border.all(1, PRIMARY_COLOR), shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color=PRIMARY_COLOR, blur_style=ft.ShadowBlurStyle.OUTER), width=350, height=400
            ),
            ft.Container(height=20),
            btn_show,
            ft.Row([btn_wrong, btn_correct], alignment=ft.MainAxisAlignment.CENTER, spacing=20)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)
    )

    chat_content = ft.Container(
        padding=20,
        content=ft.Column([
            ft.Text("🤖 Wiki-Asistan", size=20, weight="bold", color=PRIMARY_COLOR),
            ft.Divider(),
            chat_history,
            ft.Row([chat_input, btn_send])
        ])
    )

    settings_content = ft.Container(
        padding=20,
        content=ft.Column([
            ft.Text("⚙️ Ayarlar", size=20, weight="bold"),
            ft.Divider(),
            ft.Text("Yeni Soru Ekle:", size=16),
            btn_upload,
            ft.Container(height=20),
            ft.ElevatedButton("🔔 Bildirim Testi Yap", on_click=lambda e: send_local_notification("Test", "Sistem çalışıyor!")),
            ft.Text(f"Toplam Soru: {len(questions)}", color="grey"),
        ])
    )

    my_tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="Quiz", icon="quiz", content=quiz_content),
            ft.Tab(text="Asistan", icon="menu_book", content=chat_content),
            ft.Tab(text="Ayarlar", icon="settings", content=settings_content),
        ],
        expand=1,
    )

    page.add(my_tabs)
    check_pending_reviews()
    load_ui_question()

ft.app(target=main)