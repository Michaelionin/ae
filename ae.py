import pygame
import requests
from io import BytesIO
from urllib.parse import urljoin, urlparse
import commonmark
import sys
import time
import requests.exceptions
import os

class AlternetExplorer:
    def __init__(self):
        # Инициализируем pygame БЕЗ аудио-микшера чтобы избежать конфликтов со звуком
        pygame.init()
        pygame.mixer.quit()  # КРИТИЧНО: отключаем mixer для устранения потрескивания с VLC
        # Начальные размеры окна
        self.screen_width = 1000
        self.screen_height = 800
        # Создаем изменяемое окно
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        pygame.display.set_caption("Alternet Explorer")
        
        # Константа для домашней страницы
        self.HOME_PAGE_URL = "http://ionics.atwebpages.com/alternet/ae_homepage.php"
        
        # Цвета в стиле первых браузеров (Netscape Navigator, Mosaic)
        self.WINDOW_BG = (200, 200, 200)  # Серый фон окна
        self.BUTTON_FACE = (192, 192, 192)  # Цвет кнопок
        self.BUTTON_HIGHLIGHT = (220, 220, 220)  # Цвет при наведении
        self.BUTTON_SHADOW = (128, 128, 128)  # Тень кнопок
        self.BUTTON_TEXT = (0, 0, 0)  # Цвет текста на кнопках
        self.TEXT_BG = (255, 255, 255)  # Белый фон для текста
        self.TEXT_COLOR = (0, 0, 0)  # Черный текст
        self.LINK_COLOR = (0, 0, 128)  # Темно-синие ссылки
        self.QUOTE_BG = (240, 240, 245)  # Светло-серый фон для цитат
        self.BORDER_COLOR = (128, 128, 128)  # Цвет границ
        self.SCROLLBAR_BG = (220, 220, 220)
        self.SCROLLBAR_HANDLE = (160, 160, 160)
        self.URL_BG = (255, 255, 255)  # Белый фон строки URL
        self.STATUS_BG = (192, 192, 192)  # Фон статус-бара
        self.ERROR_BG = (255, 220, 220)  # Фон для ошибок
        self.IMAGE_BORDER_COLOR = (200, 200, 200)  # Цвет рамки изображения
        
        # Параметры прокрутки
        self.scroll_offset = 0
        self.max_scroll = 0
        self.scroll_speed = 40
        self.scrollbar_width = 12
        self.dragging_scrollbar = False
        self.scrollbar_drag_start = 0
        self.scrollbar_initial_offset = 0
        
        # Поля для ввода URL
        self.url_input_active = False
        self.url_input = self.HOME_PAGE_URL
        self.url_input_cursor = len(self.url_input)
        self.url_input_visible = True
        self.blink_timer = 0
        self.blink_interval = 0.5  # секунды
        
        # Кнопки навигации
        self.update_layout(self.screen_width, self.screen_height)
        
        # Шрифты в стиле первых браузеров
        self.font_families = [
            'MS Sans Serif', 'Arial', 'Helvetica', 'sans-serif'
        ]
        
        # Создаем шрифты
        try:
            self.fonts = {
                'normal': pygame.font.SysFont('MS Sans Serif, Arial', 16),
                'h1': pygame.font.SysFont('MS Sans Serif, Arial', 24, bold=True),
                'h2': pygame.font.SysFont('MS Sans Serif, Arial', 20, bold=True),
                'h3': pygame.font.SysFont('MS Sans Serif, Arial', 18, bold=True),
                'code': pygame.font.SysFont('Courier New, monospace', 14),
                'url': pygame.font.SysFont('MS Sans Serif, Arial', 14),
                'status': pygame.font.SysFont('MS Sans Serif, Arial', 12),
                'button': pygame.font.SysFont('MS Sans Serif, Arial', 13),
                'error_title': pygame.font.SysFont('MS Sans Serif, Arial', 18, bold=True),
                'error_text': pygame.font.SysFont('MS Sans Serif, Arial', 16),
                'image_caption': pygame.font.SysFont('MS Sans Serif, Arial', 12, italic=True)
            }
        except:
            # Если не получается, используем шрифт по умолчанию
            self.fonts = {
                'normal': pygame.font.SysFont(None, 16),
                'h1': pygame.font.SysFont(None, 24, bold=True),
                'h2': pygame.font.SysFont(None, 20, bold=True),
                'h3': pygame.font.SysFont(None, 18, bold=True),
                'code': pygame.font.SysFont("Courier New", 14),
                'url': pygame.font.SysFont(None, 14),
                'status': pygame.font.SysFont(None, 12),
                'button': pygame.font.SysFont(None, 13),
                'error_title': pygame.font.SysFont(None, 18, bold=True),
                'error_text': pygame.font.SysFont(None, 16),
                'image_caption': pygame.font.SysFont(None, 12, italic=True)
            }
        
        # Устанавливаем подчеркивание для ссылок
        self.fonts['link'] = pygame.font.SysFont('MS Sans Serif, Arial', 16)
        self.fonts['link'].set_underline(True)
        
        # Состояние браузера
        self.current_url = self.HOME_PAGE_URL
        self.back_stack = []
        self.forward_stack = []  # Добавляем стек для вперед
        self.active_areas = []  # Для хранения кликабельных областей (rect, url)
        self.parser = commonmark.Parser()
        
        # Инициализируем ast как пустой документ
        self.markdown_text = ""
        self.ast = self.parser.parse("# Добро пожаловать в Alternet Explorer\n\nЗагрузка начальной страницы...")
        
        # Кэш изображений
        self.image_cache = {}
        
        # Таймер для ограничения FPS
        self.clock = pygame.time.Clock()
        
        # Состояние загрузки
        self.loading = True
        self.status_message = "Инициализация..."
        
        # Индикатор загрузки (вращающаяся буква А)
        self.loading_indicator_angle = 0
        self.loading_indicator_rect = None  # Будет установлено в update_layout
        
        # Tooltip система
        self.tooltip_hover_button = None  # Какая кнопка под мышью
        self.tooltip_hover_time = 0  # Время начала наведения
        self.tooltip_delay = 0.5  # Задержка перед показом tooltip (секунды)
        self.tooltip_visible = False
        
        # Инициализация
        self.render_page()  # Сначала отрисовываем начальный экран
        self.load_page(self.current_url)  # Затем загружаем страницу
    
    def update_layout(self, new_width, new_height):
        """Обновляет расположение элементов интерфейса при изменении размера окна"""
        self.screen_width = max(600, new_width)  # Минимальная ширина 600px
        self.screen_height = max(400, new_height)  # Минимальная высота 400px
        
        # Обновляем расположение кнопок с отступами
        button_y = 10
        button_height = 25
        button_spacing = 10
        
        # Кнопка "Назад"
        self.back_button_rect = pygame.Rect(10, button_y, 25, button_height)
        
        # Кнопка "Вперед"
        self.forward_button_rect = pygame.Rect(
            self.back_button_rect.right + button_spacing, 
            button_y, 
            25, 
            button_height
        )
        
        # Кнопка "Домой"
        self.home_button_rect = pygame.Rect(
            self.forward_button_rect.right + button_spacing, 
            button_y, 
            25, 
            button_height
        )
        
        # Строка URL начинается после кнопок с отступом
        url_start_x = self.home_button_rect.right + button_spacing
        url_width = self.screen_width - url_start_x - 60
        self.url_input_rect = pygame.Rect(url_start_x, button_y, url_width, button_height)
        
        # Кнопка "Перейти"
        self.go_button_rect = pygame.Rect(
            self.screen_width - 90,
            button_y,
            50,
            button_height
        )
        
        # Индикатор загрузки (буква А) - справа от кнопки "Перейти"
        self.loading_indicator_rect = pygame.Rect(
            self.screen_width - 35,
            button_y,
            30,
            button_height
        )
    
    def draw_3d_rectangle(self, rect, is_pressed=False):
        """Рисует 3D-прямоугольник в стиле первых браузеров"""
        # Верхняя и левая границы
        top_left_color = self.BUTTON_SHADOW if is_pressed else self.BUTTON_HIGHLIGHT
        bottom_right_color = self.BUTTON_HIGHLIGHT if is_pressed else self.BUTTON_SHADOW
        
        # Рисуем верхнюю границу
        pygame.draw.line(self.screen, top_left_color, 
                        (rect.left, rect.top), (rect.right, rect.top))
        pygame.draw.line(self.screen, top_left_color, 
                        (rect.left, rect.top), (rect.left, rect.bottom))
        
        # Рисуем нижнюю и правую границы
        pygame.draw.line(self.screen, bottom_right_color, 
                        (rect.right, rect.top), (rect.right, rect.bottom))
        pygame.draw.line(self.screen, bottom_right_color, 
                        (rect.left, rect.bottom), (rect.right, rect.bottom))
        
        # Заливаем внутренность
        inner_rect = pygame.Rect(rect.left + 1, rect.top + 1, 
                                rect.width - 2, rect.height - 2)
        pygame.draw.rect(self.screen, self.BUTTON_FACE, inner_rect)
    
    def draw_button(self, rect, text, is_pressed=False, enabled=True):
        """Рисует кнопку в стиле первых браузеров"""
        self.draw_3d_rectangle(rect, is_pressed)
        
        # Текст на кнопке
        if enabled:
            color = self.BUTTON_TEXT
        else:
            color = (128, 128, 128)  # Серый для неактивной кнопки
            
        text_surf = self.fonts['button'].render(text, True, color)
        text_rect = text_surf.get_rect(center=rect.center)
        self.screen.blit(text_surf, text_rect)
    
    def draw_url_input(self):
        """Рисует строку ввода URL"""
        # Фон строки
        pygame.draw.rect(self.screen, self.URL_BG, self.url_input_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.url_input_rect, 1)
        
        # Текст
        display_text = self.url_input
        if len(display_text) > 90:
            display_text = display_text[:45] + "..." + display_text[-45:]
        
        text_surf = self.fonts['url'].render(display_text, True, self.TEXT_COLOR)
        self.screen.blit(text_surf, (self.url_input_rect.x + 5, self.url_input_rect.y + 4))
        
        # Курсор
        if self.url_input_active and self.url_input_visible:
            cursor_x = self.url_input_rect.x + 5 + min(self.fonts['url'].size(display_text[:self.url_input_cursor])[0], self.url_input_rect.width - 10)
            pygame.draw.line(self.screen, self.TEXT_COLOR, 
                            (cursor_x, self.url_input_rect.y + 4), 
                            (cursor_x, self.url_input_rect.y + 21), 1)
    
    def draw_loading_indicator(self):
        """Рисует индикатор загрузки - вращающуюся букву А с 3D рамкой"""
        if not self.loading_indicator_rect:
            return
        
        # ИСПРАВЛЕНО: Рисуем 3D рамку вокруг индикатора как у кнопок
        self.draw_3d_rectangle(self.loading_indicator_rect, is_pressed=False)
        
        # Цвет индикатора: красный при загрузке, зеленый когда загружено
        indicator_color = (220, 20, 20) if self.loading else (20, 200, 20)
        
        # Создаем большой шрифт для буквы А
        indicator_font = pygame.font.SysFont('MS Sans Serif, Arial', 20, bold=True)
        
        # Рендерим букву А
        text_surface = indicator_font.render('А', True, indicator_color)
        
        # Если идет загрузка - вращаем БЫСТРЕЕ (12 градусов вместо 5)
        if self.loading:
            # ИСПРАВЛЕНО: Увеличиваем угол вращения с 5 до 12 для более быстрой анимации
            self.loading_indicator_angle = (self.loading_indicator_angle + 12) % 360
            text_surface = pygame.transform.rotate(text_surface, self.loading_indicator_angle)
        
        # Центрируем букву в прямоугольнике индикатора
        text_rect = text_surface.get_rect(center=self.loading_indicator_rect.center)
        self.screen.blit(text_surface, text_rect)
    
    def draw_tooltip(self, text, button_rect):
        """Рисует всплывающую подсказку в стиле Windows 95"""
        # Шрифт для tooltip
        tooltip_font = pygame.font.SysFont('MS Sans Serif, Arial', 11)
        
        # Рендерим текст
        text_surface = tooltip_font.render(text, True, (0, 0, 0))
        
        # Размеры tooltip с отступами
        padding = 4
        tooltip_width = text_surface.get_width() + padding * 2
        tooltip_height = text_surface.get_height() + padding * 2
        
        # Позиция tooltip - под кнопкой
        tooltip_x = button_rect.centerx - tooltip_width // 2
        tooltip_y = button_rect.bottom + 5
        
        # Корректируем если выходит за границы экрана
        if tooltip_x < 5:
            tooltip_x = 5
        if tooltip_x + tooltip_width > self.screen_width - 5:
            tooltip_x = self.screen_width - tooltip_width - 5
        
        tooltip_rect = pygame.Rect(tooltip_x, tooltip_y, tooltip_width, tooltip_height)
        
        # Фон tooltip - желтый (#FFFFE1) как в Windows 95
        pygame.draw.rect(self.screen, (255, 255, 225), tooltip_rect)
        # Черная рамка
        pygame.draw.rect(self.screen, (0, 0, 0), tooltip_rect, 1)
        
        # Рисуем текст
        self.screen.blit(text_surface, (tooltip_x + padding, tooltip_y + padding))
    
    def draw_status_bar(self):
        """Рисует статус-бар внизу окна"""
        status_rect = pygame.Rect(0, self.screen_height - 25, self.screen_width, 25)
        pygame.draw.rect(self.screen, self.STATUS_BG, status_rect)
        pygame.draw.line(self.screen, self.BORDER_COLOR, 
                        (0, self.screen_height - 26), (self.screen_width, self.screen_height - 26), 1)
        
        # Сообщение о состоянии
        status_text = self.status_message
        if self.loading:
            status_text = "Загрузка..."
        
        text_surf = self.fonts['status'].render(status_text, True, self.TEXT_COLOR)
        self.screen.blit(text_surf, (5, self.screen_height - 23))
        
        # URL под мышью
        mouse_pos = pygame.mouse.get_pos()
        # ИСПРАВЛЕНО: учитываем прокрутку при проверке областей в статус-баре
        adjusted_pos = (mouse_pos[0], mouse_pos[1] + self.scroll_offset)
        for rect, url in self.active_areas:
            if rect.collidepoint(adjusted_pos):
                url_text = url
                if len(url_text) > 70:
                    url_text = url_text[:35] + "..." + url_text[-35:]
                url_surf = self.fonts['status'].render(url_text, True, self.LINK_COLOR)
                self.screen.blit(url_surf, (self.screen_width - url_surf.get_width() - 10, self.screen_height - 23))
                return
    
    def load_page(self, url):
        """Загружает страницу по URL с явным указанием UTF-8 кодировки"""
        # Сохраняем текущий URL в истории, если это не переход "вперед"
        if url != self.current_url and (not self.forward_stack or url != self.forward_stack[-1]):
            self.back_stack.append(self.current_url)
            self.forward_stack = []  # Очищаем стек "вперед" при новом переходе
        
        try:
            self.loading = True
            self.status_message = f"Загрузка: {url}"
            # Обновляем интерфейс, чтобы показать статус
            self.render_page()
            
            print(f"Загрузка: {url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            # Устанавливаем кодировку UTF-8
            response.encoding = 'utf-8'
            
            self.current_url = url
            self.url_input = url  # Обновляем строку ввода
            self.markdown_text = response.text
            
            # Проверка и исправление кодировки
            try:
                self.markdown_text = self.markdown_text.encode('latin1').decode('utf-8', 'replace')
            except:
                pass
            
            self.ast = self.parser.parse(self.markdown_text)
            
            # ДИАГНОСТИКА: логируем структуру AST
            print("\n[AST] Структура документа:")
            self._debug_ast(self.ast, 0)
            
            self.scroll_offset = 0
            self.max_scroll = 0
            self.loading = False
            self.status_message = "Страница загружена"
            self.render_page()
        except requests.exceptions.ConnectionError:
            self.loading = False
            self.status_message = "Ошибка: Нет подключения к интернету"
            error_msg = "# Ошибка подключения\n\nНет подключения к интернету.\nПроверьте сетевое соединение и повторите попытку."
            self.markdown_text = error_msg
            self.ast = self.parser.parse(self.markdown_text)
            self.scroll_offset = 0
            self.max_scroll = 0
            self.render_page()
        except requests.exceptions.Timeout:
            self.loading = False
            self.status_message = "Ошибка: Таймаут подключения"
            error_msg = "# Ошибка подключения\n\nТаймаут подключения.\nПопробуйте повторить запрос позже."
            self.markdown_text = error_msg
            self.ast = self.parser.parse(self.markdown_text)
            self.scroll_offset = 0
            self.max_scroll = 0
            self.render_page()
        except Exception as e:
            self.loading = False
            self.status_message = f"Ошибка: {str(e)}"
            error_msg = f"# Ошибка\n\nНе удалось загрузить страницу:\n{str(e)}"
            self.markdown_text = error_msg
            self.ast = self.parser.parse(self.markdown_text)
            self.scroll_offset = 0
            self.max_scroll = 0
            self.render_page()
    
    def _debug_ast(self, node, level):
        """Отладочный метод для визуализации структуры AST"""
        indent = "  " * level
        if node.t == 'text':
            print(f"{indent}{node.t}: {repr(node.literal[:50])}...")
        elif node.t == 'image':
            print(f"{indent}IMAGE: {node.destination}")
        elif node.t == 'link':
            print(f"{indent}LINK: {node.destination}")
        else:
            print(f"{indent}{node.t}")
        
        child = node.first_child
        while child:
            self._debug_ast(child, level + 1)
            child = child.nxt
    
    def load_image(self, url, base_url):
        """ИСПРАВЛЕНО: Универсальная загрузка изображений с поддержкой редиректов http→https"""
        # Обработка относительных URL
        if url.startswith('//'):
            # Обработка протокол-относительных URL
            parsed = urlparse(base_url)
            full_url = f"{parsed.scheme}:{url}"
        elif url.startswith('http://') or url.startswith('https://'):
            full_url = url
        else:
            full_url = urljoin(base_url, url)
        
        # Проверяем кэш (только для успешно загруженных изображений)
        if full_url in self.image_cache:
            cached_img = self.image_cache[full_url]
            # Проверяем, что это не заглушка ошибки (по размеру)
            if cached_img.get_size() != (200, 150):
                return cached_img, full_url
        
        # Список URL для попытки загрузки (http и https варианты)
        urls_to_try = [full_url]
        
        # Если URL с http://, добавляем https:// вариант для автоматического fallback
        if full_url.startswith('http://'):
            https_url = 'https://' + full_url[7:]
            urls_to_try.append(https_url)
        
        last_error = None
        
        for attempt_url in urls_to_try:
            try:
                print(f"[IMAGE] Попытка загрузки: {attempt_url}")
                
                # Добавляем User-Agent для совместимости
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
                }
                
                # КРИТИЧНО: явно разрешаем редиректы
                response = requests.get(
                    attempt_url,
                    headers=headers,
                    timeout=10,
                    allow_redirects=True,  # Явно следуем редиректам
                    stream=False  # Загружаем полностью
                )
                
                response.raise_for_status()
                
                # Логируем финальный URL после всех редиректов
                final_url = response.url
                if final_url != attempt_url:
                    print(f"[IMAGE] Редирект: {attempt_url} → {final_url}")
                
                # ИСПРАВЛЕНО: Проверка MIME-типа стала мягкой
                content_type = response.headers.get('Content-Type', '').lower()
                print(f"[IMAGE] Content-Type: {content_type}")
                
                # Определяем по расширению файла (используем финальный URL)
                ext = os.path.splitext(final_url.split('?')[0])[1].lower()  # Убираем query параметры
                
                # Если расширение валидное - игнорируем MIME-тип
                is_valid_extension = ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico']
                is_valid_mime = 'image' in content_type
                
                if not is_valid_extension and not is_valid_mime:
                    raise ValueError(f"Не похоже на изображение: MIME={content_type}, ext={ext}")
                
                # Пробуем загрузить изображение
                print(f"[IMAGE] Размер данных: {len(response.content)} байт")
                img = pygame.image.load(BytesIO(response.content))
                print(f"[IMAGE] Успешно загружено: {img.get_size()}")
                
                # Сохраняем в кэш ТОЛЬКО успешно загруженные изображения
                self.image_cache[full_url] = img
                
                return img, final_url
                
            except requests.exceptions.SSLError as e:
                print(f"[IMAGE] SSL ошибка для {attempt_url}: {str(e)}")
                last_error = e
                continue  # Пробуем следующий URL
                
            except requests.exceptions.RequestException as e:
                print(f"[IMAGE] Сетевая ошибка для {attempt_url}: {str(e)}")
                last_error = e
                continue  # Пробуем следующий URL
                
            except Exception as e:
                print(f"[IMAGE] Ошибка обработки {attempt_url}: {str(e)}")
                last_error = e
                continue  # Пробуем следующий URL
        
        # Если все попытки провалились - создаем заглушку
        print(f"[IMAGE] ВСЕ ПОПЫТКИ ПРОВАЛИЛИСЬ для {url}")
        print(f"[IMAGE] Последняя ошибка: {str(last_error)}")
        
        # Создаем заглушку с информацией об ошибке
        img_width, img_height = 200, 150
        img = pygame.Surface((img_width, img_height))
        img.fill((240, 240, 240))
        
        # Рисуем рамку
        pygame.draw.rect(img, (200, 200, 200), (5, 5, img_width - 10, img_height - 10), 1)
        
        # Рисуем крест
        pygame.draw.line(img, (255, 0, 0), (20, 20), (img_width - 20, img_height - 20), 2)
        pygame.draw.line(img, (255, 0, 0), (img_width - 20, 20), (20, img_height - 20), 2)
        
        # Добавляем текст с ошибкой
        try:
            error_msg = str(last_error) if last_error else "Unknown error"
            error_lines = []
            words = error_msg.split()
            current_line = ""
            
            for word in words:
                if len(current_line) + len(word) + 1 > 25:
                    error_lines.append(current_line)
                    current_line = word
                else:
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
            
            if current_line:
                error_lines.append(current_line)
            
            error_lines = error_lines[:3]
            
            for i, line in enumerate(error_lines):
                error_font = self.fonts['image_caption']
                error_text = error_font.render(line, True, (200, 0, 0))
                text_rect = error_text.get_rect(center=(img_width // 2, 40 + i * 15))
                img.blit(error_text, text_rect)
            
            # URL изображения
            url_font = pygame.font.SysFont('MS Sans Serif, Arial', 10)
            display_url = os.path.basename(url)[:30]
            url_text = url_font.render(f"{display_url}", True, (100, 100, 100))
            url_rect = url_text.get_rect(center=(img_width // 2, img_height - 20))
            img.blit(url_text, url_rect)
        except Exception as text_error:
            print(f"[IMAGE] Ошибка при создании заглушки: {text_error}")
        
        # НЕ КЕШИРУЕМ заглушки - при следующем рендере попробуем снова
        return img, full_url
    
    def wrap_text(self, text, font, max_width):
        """Улучшенный алгоритм переноса текста с поддержкой UTF-8"""
        if not text:
            return []
        
        words = text.split()
        if not words:
            return []
        
        lines = []
        current_line = words[0]
        
        for word in words[1:]:
            # Проверяем, поместится ли слово в текущую строку
            test_line = current_line + ' ' + word
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def render_node(self, node, base_url, x, y, screen):
        """Рекурсивно отрисовывает узел AST с правильными отступами"""
        # Обновляем максимальную прокрутку
        self.max_scroll = max(self.max_scroll, y + 100)
        
        if node.t == 'document':
            # Обработка дочерних узлов документа
            child = node.first_child
            while child:
                y = self.render_node(child, base_url, x, y, screen)
                child = child.nxt
            return y
        
        elif node.t == 'heading':
            level = min(node.level, 3)  # Поддерживаем только h1-h3
            font_key = f'h{level}'
            font = self.fonts[font_key]
            
            # Собираем текст заголовка
            text = self.collect_text(node)
            lines = self.wrap_text(text, font, self.screen_width - 40)
            
            # Добавляем отступ перед заголовком
            y += 20 if level == 1 else 15 if level == 2 else 10
            
            # Отрисовка
            for line in lines:
                try:
                    rendered = font.render(line, True, self.TEXT_COLOR)
                    screen_y = y - self.scroll_offset
                    # Рисуем только если видимо
                    if screen_y + rendered.get_height() > 0 and screen_y < self.screen_height:
                        screen.blit(rendered, (x, screen_y))
                    y += rendered.get_height() + 3
                except:
                    pass
            
            # Добавляем отступ после заголовка
            y += 15 if level == 1 else 10 if level == 2 else 5
            
            return y
        
        elif node.t == 'paragraph':
            font = self.fonts['normal']
            y += 10  # Отступ перед параграфом
            y = self.render_inline(node, base_url, x, y, screen, font)
            y += 10  # Отступ после параграфа
            return y
        
        elif node.t == 'block_quote':
            # Цитата с отступом и фоном
            y += 15
            
            # Сначала определяем высоту цитаты
            quote_height = 0
            temp_y = y
            child = node.first_child
            while child:
                if child.t == 'paragraph':
                    temp_y = self.render_inline(child, base_url, x + 20, temp_y, screen, self.fonts['normal'])
                    quote_height = max(quote_height, temp_y - y)
                child = child.nxt
            
            # ИСПРАВЛЕНО: используем логические координаты для фона
            screen_y = y - self.scroll_offset
            # Рисуем фон цитаты только если видимо
            if screen_y + quote_height + 10 > 0 and screen_y - 5 < self.screen_height:
                pygame.draw.rect(screen, self.QUOTE_BG, 
                               (x - 10, screen_y - 5, self.screen_width - 40, quote_height + 10))
                # Рисуем левую границу
                pygame.draw.line(screen, self.LINK_COLOR, 
                               (x - 5, screen_y - 5), 
                               (x - 5, screen_y + quote_height + 5), 2)
            
            # Теперь рисуем содержимое цитаты
            child = node.first_child
            while child:
                if child.t == 'paragraph':
                    y = self.render_inline(child, base_url, x + 20, y, screen, self.fonts['normal'])
                child = child.nxt
            
            y += 15
            return y
        
        elif node.t == 'list':
            # Списки
            is_ordered = node.list_data['type'] == 'ordered'
            item_number = 1
            
            y += 10
            
            child = node.first_child
            while child:
                if child.t == 'item':
                    # Маркер списка
                    marker = f"{item_number}." if is_ordered else "•"
                    try:
                        marker_surf = self.fonts['normal'].render(marker, True, self.TEXT_COLOR)
                        screen_y = y - self.scroll_offset
                        if screen_y + marker_surf.get_height() > 0 and screen_y < self.screen_height:
                            screen.blit(marker_surf, (x, screen_y))
                    except:
                        pass
                    
                    # Содержимое пункта
                    y = self.render_node(child, base_url, x + 30, y, screen)
                    
                    if is_ordered:
                        item_number += 1
                child = child.nxt
            
            y += 10
            return y
        
        elif node.t == 'item':
            # Пункт списка
            child = node.first_child
            while child:
                y = self.render_node(child, base_url, x, y, screen)
                child = child.nxt
            return y + 5
        
        elif node.t == 'code_block':
            # Блок кода
            y += 15
            
            font = self.fonts['code']
            text = node.literal.strip()
            lines = text.split('\n')
            
            # Вычисляем высоту блока
            block_height = len(lines) * (font.get_height() + 2) + 10
            
            # ИСПРАВЛЕНО: используем логические координаты для фона
            screen_y = y - self.scroll_offset
            # Рисуем фон только если видимо
            if screen_y + block_height > 0 and screen_y - 5 < self.screen_height:
                pygame.draw.rect(screen, (245, 245, 245), 
                               (x - 10, screen_y - 5, self.screen_width - 40, block_height))
                pygame.draw.rect(screen, (200, 200, 200), 
                               (x - 10, screen_y - 5, self.screen_width - 40, block_height), 1)
            
            for line in lines:
                try:
                    rendered = font.render(line, True, (0, 100, 0))
                    screen_y = y - self.scroll_offset
                    if screen_y + rendered.get_height() > 0 and screen_y < self.screen_height:
                        screen.blit(rendered, (x, screen_y))
                    y += rendered.get_height() + 2
                except:
                    pass
            
            y += 15
            return y
        
        elif node.t == 'thematic_break':
            # Горизонтальная линия
            screen_y = y - self.scroll_offset
            if screen_y > 0 and screen_y < self.screen_height:
                pygame.draw.line(screen, (128, 128, 128), 
                               (x, screen_y), 
                               (x + self.screen_width - 40, screen_y), 1)
                pygame.draw.line(screen, (255, 255, 255), 
                               (x, screen_y + 1), 
                               (x + self.screen_width - 40, screen_y + 1), 1)
            return y + 20
        
        elif node.t == 'image':
            # ИСПРАВЛЕНО: ИЗОБРАЖЕНИЕ С ПРАВИЛЬНЫМ ПОЗИЦИОНИРОВАНИЕМ
            y += 15
            
            # Загружаем изображение
            img, full_url = self.load_image(node.destination, base_url)
            
            if img:
                # Максимальная ширина изображения
                max_width = self.screen_width - 60
                
                # Определяем текущие размеры изображения
                img_width, img_height = img.get_size()
                
                # Масштабируем изображение, если оно слишком широкое
                if img_width > max_width:
                    scale_factor = max_width / img_width
                    new_width = int(img_width * scale_factor)
                    new_height = int(img_height * scale_factor)
                    img = pygame.transform.scale(img, (new_width, new_height))
                    img_width, img_height = new_width, new_height
                
                # ИСПРАВЛЕНО: проверяем видимость ПЕРЕД отрисовкой
                screen_y = y - self.scroll_offset
                is_visible = (screen_y + img_height > 0 and screen_y < self.screen_height)
                
                if is_visible:
                    # Рисуем рамку вокруг изображения
                    pygame.draw.rect(screen, self.IMAGE_BORDER_COLOR, 
                                   (x, screen_y, img_width, img_height), 1)
                    
                    # Рисуем изображение
                    screen.blit(img, (x, screen_y))
                
                # НЕ ДОБАВЛЯЕМ изображения в active_areas - они не должны быть кликабельными для навигации
                # img_rect = pygame.Rect(x, y, img_width, img_height)
                # self.active_areas.append((img_rect, full_url))
                
                # Обновляем позицию Y
                y += img_height + 10
            
            # Добавляем подпись к изображению
            if node.title or node.destination:
                font = self.fonts['image_caption']
                alt_text = node.title if node.title else os.path.basename(node.destination)
                try:
                    caption_lines = self.wrap_text(alt_text, font, self.screen_width - 60)
                    
                    for line in caption_lines:
                        rendered = font.render(line, True, (100, 100, 100))
                        screen_y = y - self.scroll_offset
                        if screen_y + rendered.get_height() > 0 and screen_y < self.screen_height:
                            screen.blit(rendered, (x, screen_y))
                        y += rendered.get_height() + 3
                except:
                    pass
            
            y += 10
            return y
        
        # Обработка других типов узлов
        child = node.first_child
        while child:
            y = self.render_node(child, base_url, x, y, screen)
            child = child.nxt
        
        return y
    
    def render_inline(self, node, base_url, x, y, screen, base_font):
        """ИСПРАВЛЕНО: Отрисовывает инлайновые элементы с правильными переносами"""
        current_x = x
        max_width = self.screen_width - 40
        line_height = base_font.get_height()
        
        child = node.first_child
        while child:
            if child.t == 'text':
                text = child.literal
                words = text.split()
                
                for word in words:
                    try:
                        # Добавляем пробел перед словом, если это не начало строки
                        if current_x > x:
                            word_with_space = ' ' + word
                        else:
                            word_with_space = word
                        
                        word_width = base_font.size(word_with_space)[0]
                        
                        # Проверяем, помещается ли слово
                        if current_x + word_width > x + max_width and current_x > x:
                            # Переносим на новую строку
                            y += line_height
                            current_x = x
                            word_with_space = word
                            word_width = base_font.size(word_with_space)[0]
                        
                        # Рисуем слово
                        rendered = base_font.render(word_with_space, True, self.TEXT_COLOR)
                        screen_y = y - self.scroll_offset
                        
                        if screen_y + rendered.get_height() > 0 and screen_y < self.screen_height:
                            screen.blit(rendered, (current_x, screen_y))
                        
                        current_x += word_width
                    except Exception as e:
                        print(f"Ошибка отрисовки текста: {e}")
            
            elif child.t == 'softbreak':
                y += line_height
                current_x = x
            
            elif child.t == 'linebreak':
                y += line_height
                current_x = x
            
            elif child.t == 'link':
                # ИСПРАВЛЕНО: Ссылка с правильной обработкой переносов
                url = child.destination
                link_text = self.collect_text(child)
                words = link_text.split()
                
                for word in words:
                    try:
                        if current_x > x:
                            word_with_space = ' ' + word
                        else:
                            word_with_space = word
                        
                        word_width = self.fonts['link'].size(word_with_space)[0]
                        
                        # Проверяем перенос
                        if current_x + word_width > x + max_width and current_x > x:
                            y += line_height
                            current_x = x
                            word_with_space = word
                            word_width = self.fonts['link'].size(word_with_space)[0]
                        
                        rendered = self.fonts['link'].render(word_with_space, True, self.LINK_COLOR)
                        screen_y = y - self.scroll_offset
                        
                        # ИСПРАВЛЕНО: Сохраняем область в ЛОГИЧЕСКИХ координатах
                        rect = pygame.Rect(current_x, y, word_width, line_height)
                        self.active_areas.append((rect, url))
                        
                        if screen_y + rendered.get_height() > 0 and screen_y < self.screen_height:
                            screen.blit(rendered, (current_x, screen_y))
                        
                        current_x += word_width
                    except Exception as e:
                        print(f"Ошибка отрисовки ссылки: {e}")
            
            elif child.t == 'strong':
                # Жирный текст
                bold_font = pygame.font.SysFont('MS Sans Serif, Arial', base_font.get_height(), bold=True)
                text = self.collect_text(child)
                words = text.split()
                
                for word in words:
                    try:
                        if current_x > x:
                            word_with_space = ' ' + word
                        else:
                            word_with_space = word
                        
                        word_width = bold_font.size(word_with_space)[0]
                        
                        if current_x + word_width > x + max_width and current_x > x:
                            y += line_height
                            current_x = x
                            word_with_space = word
                            word_width = bold_font.size(word_with_space)[0]
                        
                        rendered = bold_font.render(word_with_space, True, self.TEXT_COLOR)
                        screen_y = y - self.scroll_offset
                        
                        if screen_y + rendered.get_height() > 0 and screen_y < self.screen_height:
                            screen.blit(rendered, (current_x, screen_y))
                        
                        current_x += word_width
                    except:
                        pass
            
            elif child.t == 'emph':
                # Курсив
                italic_font = pygame.font.SysFont('MS Sans Serif, Arial', base_font.get_height(), italic=True)
                text = self.collect_text(child)
                words = text.split()
                
                for word in words:
                    try:
                        if current_x > x:
                            word_with_space = ' ' + word
                        else:
                            word_with_space = word
                        
                        word_width = italic_font.size(word_with_space)[0]
                        
                        if current_x + word_width > x + max_width and current_x > x:
                            y += line_height
                            current_x = x
                            word_with_space = word
                            word_width = italic_font.size(word_with_space)[0]
                        
                        rendered = italic_font.render(word_with_space, True, self.TEXT_COLOR)
                        screen_y = y - self.scroll_offset
                        
                        if screen_y + rendered.get_height() > 0 and screen_y < self.screen_height:
                            screen.blit(rendered, (current_x, screen_y))
                        
                        current_x += word_width
                    except:
                        pass
            
            elif child.t == 'image':
                # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Обработка инлайн-изображений
                print(f"[INLINE IMAGE] Обнаружено изображение: {child.destination}")
                
                # Если изображение не в начале строки, переходим на новую строку
                if current_x > x:
                    y += line_height
                    current_x = x
                
                # Загружаем изображение
                img, full_url = self.load_image(child.destination, base_url)
                
                if img:
                    # Максимальная ширина изображения
                    max_img_width = max_width
                    
                    # Определяем размеры
                    img_width, img_height = img.get_size()
                    
                    # Масштабируем если нужно
                    if img_width > max_img_width:
                        scale_factor = max_img_width / img_width
                        new_width = int(img_width * scale_factor)
                        new_height = int(img_height * scale_factor)
                        img = pygame.transform.scale(img, (new_width, new_height))
                        img_width, img_height = new_width, new_height
                    
                    # Проверяем видимость
                    screen_y = y - self.scroll_offset
                    is_visible = (screen_y + img_height > 0 and screen_y < self.screen_height)
                    
                    if is_visible:
                        # Рисуем рамку
                        pygame.draw.rect(screen, self.IMAGE_BORDER_COLOR,
                                       (x, screen_y, img_width, img_height), 1)
                        # Рисуем изображение
                        screen.blit(img, (x, screen_y))
                        print(f"[INLINE IMAGE] Отрисовано: {img_width}x{img_height} at y={y}")
                    
                    # НЕ ДОБАВЛЯЕМ изображения в active_areas - они не должны быть кликабельными для навигации
                    # img_rect = pygame.Rect(x, y, img_width, img_height)
                    # self.active_areas.append((img_rect, full_url))
                    
                    # Обновляем позицию
                    y += img_height + 10
                    current_x = x  # Сброс на начало строки
                    
                    # Подпись к изображению
                    if child.title or child.destination:
                        caption_font = self.fonts['image_caption']
                        alt_text = child.title if child.title else os.path.basename(child.destination)
                        try:
                            caption_lines = self.wrap_text(alt_text, caption_font, max_width)
                            for line in caption_lines:
                                rendered = caption_font.render(line, True, (100, 100, 100))
                                screen_y = y - self.scroll_offset
                                if screen_y + rendered.get_height() > 0 and screen_y < self.screen_height:
                                    screen.blit(rendered, (x, screen_y))
                                y += rendered.get_height() + 3
                        except:
                            pass
                        y += 10
            
            child = child.nxt
        
        # Если остались элементы на строке, переходим на новую
        if current_x > x:
            y += line_height
        
        return y
    
    def collect_text(self, node):
        """Собирает текст из узла и его дочерних элементов"""
        if node.t == 'text':
            return node.literal
        
        text = ''
        child = node.first_child
        while child:
            text += self.collect_text(child)
            child = child.nxt
        
        return text
    
    def draw_scrollbar(self):
        """Рисует полосу прокрутки в стиле Windows 95"""
        if self.max_scroll <= self.screen_height - 100:
            return
        
        # Вычисляем размер ползунка
        visible_height = self.screen_height - 100
        scrollbar_height = max(20, int((visible_height / self.max_scroll) * visible_height))
        scrollbar_pos = int((self.scroll_offset / self.max_scroll) * (visible_height - scrollbar_height))
        
        # Рисуем фон полосы прокрутки
        scrollbar_rect = pygame.Rect(
            self.screen_width - self.scrollbar_width, 
            50, 
            self.scrollbar_width, 
            visible_height
        )
        pygame.draw.rect(self.screen, self.SCROLLBAR_BG, scrollbar_rect)
        
        # Рисуем ползунок
        handle_rect = pygame.Rect(
            self.screen_width - self.scrollbar_width, 
            50 + scrollbar_pos, 
            self.scrollbar_width, 
            scrollbar_height
        )
        pygame.draw.rect(self.screen, self.SCROLLBAR_HANDLE, handle_rect)
        
        # 3D эффект для ползунка
        pygame.draw.line(self.screen, self.BUTTON_HIGHLIGHT, 
                        (handle_rect.right, handle_rect.top), 
                        (handle_rect.right, handle_rect.bottom))
        pygame.draw.line(self.screen, self.BUTTON_HIGHLIGHT, 
                        (handle_rect.left, handle_rect.top), 
                        (handle_rect.right, handle_rect.top))
        pygame.draw.line(self.screen, self.BUTTON_SHADOW, 
                        (handle_rect.left, handle_rect.bottom), 
                        (handle_rect.right, handle_rect.bottom))
        pygame.draw.line(self.screen, self.BUTTON_SHADOW, 
                        (handle_rect.left, handle_rect.top), 
                        (handle_rect.left, handle_rect.bottom))
    
    def handle_scroll(self, event):
        """ИСПРАВЛЕНО: Обрабатывает события прокрутки с правильной проверкой кликов"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # Колесо вверх
                self.scroll_offset = max(0, self.scroll_offset - self.scroll_speed)
            elif event.button == 5:  # Колесо вниз
                self.scroll_offset = min(self.max_scroll - (self.screen_height - 100), self.scroll_offset + self.scroll_speed)
            elif event.button == 1:  # Левая кнопка
                # Проверка клика на полосе прокрутки
                if event.pos[0] > self.screen_width - self.scrollbar_width:
                    visible_height = self.screen_height - 100
                    if self.max_scroll > visible_height:
                        scrollbar_height = max(20, int((visible_height / self.max_scroll) * visible_height))
                        scrollbar_pos = (event.pos[1] - 50) / (visible_height - scrollbar_height)
                        self.scroll_offset = int((self.max_scroll - visible_height) * scrollbar_pos)
                        self.scroll_offset = max(0, min(self.max_scroll - visible_height, self.scroll_offset))
                # Проверка клика на активных областях
                else:
                    # ИСПРАВЛЕНО: преобразуем экранные координаты в логические
                    pos = pygame.mouse.get_pos()
                    adjusted_pos = (pos[0], pos[1] + self.scroll_offset)
                    
                    for rect, url in self.active_areas:
                        if rect.collidepoint(adjusted_pos):
                            self.forward_stack.append(self.current_url)
                            self.load_page(url)
                            break
            
            elif event.button == 2:  # Средняя кнопка
                self.scroll_offset = 0
        
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_scrollbar and event.buttons[0]:
                # Перемещаем ползунок
                dy = event.pos[1] - self.scrollbar_drag_start
                visible_height = self.screen_height - 100
                if self.max_scroll > visible_height:
                    scrollbar_height = max(20, int((visible_height / self.max_scroll) * visible_height))
                    new_offset = self.scrollbar_initial_offset + dy * (self.max_scroll / visible_height)
                    self.scroll_offset = max(0, min(self.max_scroll - visible_height, new_offset))
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging_scrollbar = False
    
    def handle_url_input(self, event):
        """Обрабатывает ввод в строку URL"""
        if not self.url_input_active:
            return
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.url_input_active = False
                self.load_page(self.url_input)
            elif event.key == pygame.K_ESCAPE:
                self.url_input_active = False
                self.url_input = self.current_url
            elif event.key == pygame.K_BACKSPACE:
                if self.url_input_cursor > 0:
                    self.url_input = self.url_input[:self.url_input_cursor-1] + self.url_input[self.url_input_cursor:]
                    self.url_input_cursor = max(0, self.url_input_cursor - 1)
            elif event.key == pygame.K_DELETE:
                if self.url_input_cursor < len(self.url_input):
                    self.url_input = self.url_input[:self.url_input_cursor] + self.url_input[self.url_input_cursor+1:]
            elif event.key == pygame.K_LEFT:
                self.url_input_cursor = max(0, self.url_input_cursor - 1)
            elif event.key == pygame.K_RIGHT:
                self.url_input_cursor = min(len(self.url_input), self.url_input_cursor + 1)
            elif event.key == pygame.K_HOME:
                self.url_input_cursor = 0
            elif event.key == pygame.K_END:
                self.url_input_cursor = len(self.url_input)
            elif 32 <= event.key <= 126:
                char = event.unicode
                if char:
                    self.url_input = self.url_input[:self.url_input_cursor] + char + self.url_input[self.url_input_cursor:]
                    self.url_input_cursor += 1
    
    def render_page(self):
        """Отрисовывает всю страницу с прокруткой"""
        # Фон окна
        self.screen.fill(self.WINDOW_BG)
        
        # Верхняя панель с улучшенным 3D эффектом
        toolbar_rect = pygame.Rect(0, 0, self.screen_width, 50)
        pygame.draw.rect(self.screen, (192, 192, 192), toolbar_rect)
        
        # 3D границы тулбара (как в Windows 95) - ИСПРАВЛЕНО: убрана белая полоска
        pygame.draw.line(self.screen, (223, 223, 223), (0, 0), (self.screen_width, 0), 1)  # Светло-серая вместо белой
        pygame.draw.line(self.screen, (128, 128, 128), (0, 49), (self.screen_width, 49), 1)  # Нижняя тень
        pygame.draw.line(self.screen, (64, 64, 64), (0, 50), (self.screen_width, 50), 1)  # Темная граница
        
        # Разделители между кнопками (вертикальные линии в стиле Windows 95)
        separator_x1 = self.home_button_rect.right + 5
        pygame.draw.line(self.screen, (128, 128, 128), (separator_x1, 8), (separator_x1, 42), 1)
        pygame.draw.line(self.screen, (255, 255, 255), (separator_x1 + 1, 8), (separator_x1 + 1, 42), 1)
        
        # Кнопки навигации с улучшенными символами
        self.draw_button(self.back_button_rect, "<", enabled=len(self.back_stack) > 0)
        self.draw_button(self.forward_button_rect, ">", enabled=len(self.forward_stack) > 0)
        self.draw_button(self.home_button_rect, "H", enabled=True)  # ИСПРАВЛЕНО: 'H' вместо unicode символа
        
        # Строка ввода URL
        self.draw_url_input()
        
        # Кнопка "Перейти"
        self.draw_button(self.go_button_rect, "Go")
        
        # Индикатор загрузки
        self.draw_loading_indicator()
        
        # Основное содержимое с правильным clipping
        content_rect = pygame.Rect(0, 50, self.screen_width - self.scrollbar_width, self.screen_height - 75)
        pygame.draw.rect(self.screen, self.TEXT_BG, content_rect)
        
        # КРИТИЧНО: устанавливаем clipping rect для контента
        self.screen.set_clip(content_rect)
        
        # Очищаем активные области
        self.active_areas = []
        
        # Отрисовка содержимого
        y_offset = 60
        if hasattr(self, 'ast') and self.ast is not None:
            self.render_node(self.ast, self.current_url, 20, y_offset, self.screen)
        
        # КРИТИЧНО: сбрасываем clipping
        self.screen.set_clip(None)
        
        # Граница области контента (поверх контента, чтобы не обрезалась)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, content_rect, 2)
        # Внутренняя тень для 3D эффекта
        pygame.draw.line(self.screen, (64, 64, 64), (1, 51), (content_rect.right - 1, 51), 1)
        pygame.draw.line(self.screen, (64, 64, 64), (1, 51), (1, content_rect.bottom - 1), 1)
        
        # Полоса прокрутки
        self.draw_scrollbar()
        
        # Статус-бар
        self.draw_status_bar()
        
        # Tooltip (рисуется последним, поверх всего)
        if self.tooltip_visible and self.tooltip_hover_button:
            button_tooltips = {
                'back': 'Назад',
                'forward': 'Вперед',
                'home': 'Домашняя страница',
                'go': 'Перейти'
            }
            
            tooltip_text = button_tooltips.get(self.tooltip_hover_button, '')
            if tooltip_text:
                button_rects = {
                    'back': self.back_button_rect,
                    'forward': self.forward_button_rect,
                    'home': self.home_button_rect,
                    'go': self.go_button_rect
                }
                button_rect = button_rects.get(self.tooltip_hover_button)
                if button_rect:
                    self.draw_tooltip(tooltip_text, button_rect)
        
        pygame.display.flip()
    
    def run(self):
        """Основной цикл браузера"""
        running = True
        last_render_time = 0
        render_interval = 1.0 / 30  # 30 FPS
        blink_timer = 0
        
        while running:
            current_time = time.time()
            dt = current_time - last_render_time
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif event.type == pygame.VIDEORESIZE:
                    self.update_layout(event.w, event.h)
                    self.render_page()
                
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL):
                    self.handle_scroll(event)
                    
                    # Обработка движения мыши для tooltip
                    if event.type == pygame.MOUSEMOTION:
                        mouse_pos = pygame.mouse.get_pos()
                        
                        # Определяем над какой кнопкой мышь
                        current_hover = None
                        if self.back_button_rect.collidepoint(mouse_pos):
                            current_hover = 'back'
                        elif self.forward_button_rect.collidepoint(mouse_pos):
                            current_hover = 'forward'
                        elif self.home_button_rect.collidepoint(mouse_pos):
                            current_hover = 'home'
                        elif self.go_button_rect.collidepoint(mouse_pos):
                            current_hover = 'go'
                        
                        # Если начали наводить на новую кнопку
                        if current_hover != self.tooltip_hover_button:
                            self.tooltip_hover_button = current_hover
                            self.tooltip_hover_time = current_time
                            self.tooltip_visible = False
                        
                        # Если навели достаточно долго - показываем tooltip
                        if self.tooltip_hover_button and (current_time - self.tooltip_hover_time) > self.tooltip_delay:
                            self.tooltip_visible = True
                            self.render_page()
                    
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        # Кнопка "Назад"
                        if self.back_button_rect.collidepoint(event.pos) and len(self.back_stack) > 0:
                            if self.current_url != self.back_stack[-1]:
                                self.forward_stack.append(self.current_url)
                            self.current_url = self.back_stack.pop()
                            self.load_page(self.current_url)
                        
                        # Кнопка "Вперед"
                        elif self.forward_button_rect.collidepoint(event.pos) and len(self.forward_stack) > 0:
                            self.back_stack.append(self.current_url)
                            self.current_url = self.forward_stack.pop()
                            self.load_page(self.current_url)
                        
                        # Кнопка "Домой"
                        elif self.home_button_rect.collidepoint(event.pos):
                            self.url_input_active = False
                            self.load_page(self.HOME_PAGE_URL)
                        
                        # Кнопка "Перейти"
                        elif self.go_button_rect.collidepoint(event.pos):
                            self.url_input_active = False
                            self.load_page(self.url_input)
                        
                        # Строка URL
                        elif self.url_input_rect.collidepoint(event.pos):
                            self.url_input_active = True
                            mouse_x = event.pos[0] - self.url_input_rect.x - 5
                            for i in range(len(self.url_input) + 1):
                                if i < len(self.url_input):
                                    text_width = self.fonts['url'].size(self.url_input[:i])[0]
                                    if mouse_x < text_width:
                                        self.url_input_cursor = i
                                        break
                                else:
                                    self.url_input_cursor = len(self.url_input)
                        
                        # Начало перетаскивания ползунка
                        elif event.pos[0] > self.screen_width - self.scrollbar_width:
                            visible_height = self.screen_height - 100
                            if self.max_scroll > visible_height:
                                scrollbar_height = max(20, int((visible_height / self.max_scroll) * visible_height))
                                scrollbar_pos = (event.pos[1] - 50) / (visible_height - scrollbar_height)
                                self.scrollbar_initial_offset = self.scroll_offset
                                self.scrollbar_drag_start = event.pos[1]
                                self.dragging_scrollbar = True
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.url_input_active = False
                    elif self.url_input_active:
                        self.handle_url_input(event)
            
            # Мигание курсора
            blink_timer += dt
            if blink_timer >= self.blink_interval:
                self.url_input_visible = not self.url_input_visible
                blink_timer = 0
                self.render_page()
            
            # Анимация индикатора загрузки
            if self.loading:
                self.render_page()
            
            if dt > render_interval:
                last_render_time = current_time
            
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    print("=" * 50)
    print("Alternet Explorer - браузер для сети Альтернет")
    print("Запуск начальной страницы:", "http://ionics.atwebpages.com/alternet/ae_homepage.php")
    print("=" * 50)
    
    browser = AlternetExplorer()
    browser.run()
