import pygame
import requests
from io import BytesIO
from urllib.parse import urljoin, urlparse
import commonmark
import sys
import time

class AlternetExplorer:
    def __init__(self):
        pygame.init()
        self.screen_width = 1000
        self.screen_height = 800
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Alternet Explorer")
        
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
        self.url_input = "http://ionics.neocities.org/alternet/list.md"
        self.url_input_cursor = len(self.url_input)
        self.url_input_visible = True
        self.blink_timer = 0
        self.blink_interval = 0.5  # секунды
        
        # Кнопки навигации
        self.back_button_rect = pygame.Rect(10, 10, 25, 25)
        self.forward_button_rect = pygame.Rect(40, 10, 25, 25)
        self.go_button_rect = pygame.Rect(940, 10, 50, 25)
        
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
                'button': pygame.font.SysFont('MS Sans Serif, Arial', 13)
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
                'button': pygame.font.SysFont(None, 13)
            }
        
        # Устанавливаем подчеркивание для ссылок
        self.fonts['link'] = pygame.font.SysFont('MS Sans Serif, Arial', 16)
        self.fonts['link'].set_underline(True)
        
        # Состояние браузера
        self.current_url = "http://ionics.neocities.org/alternet/list.md"
        self.back_stack = []
        self.forward_stack = []  # Добавляем стек для вперед
        self.active_areas = []  # Для хранения кликабельных областей (rect, url)
        self.parser = commonmark.Parser()
        
        # ИНДИВИДУАЛЬНОЕ ИСПРАВЛЕНИЕ: инициализируем ast как пустой документ
        self.markdown_text = ""
        self.ast = self.parser.parse("# Добро пожаловать в Alternet Explorer\n\nЗагрузка начальной страницы...")
        
        # Кэш изображений
        self.image_cache = {}
        
        # Таймер для ограничения FPS
        self.clock = pygame.time.Clock()
        
        # Состояние загрузки
        self.loading = True
        self.status_message = "Инициализация..."
        
        # Инициализация
        self.render_page()  # Сначала отрисовываем начальный экран
        self.load_page(self.current_url)  # Затем загружаем страницу
    
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
        url_rect = pygame.Rect(80, 10, 850, 25)
        pygame.draw.rect(self.screen, self.URL_BG, url_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, url_rect, 1)
        
        # Текст
        display_text = self.url_input
        if len(display_text) > 90:
            display_text = display_text[:45] + "..." + display_text[-45:]
        
        text_surf = self.fonts['url'].render(display_text, True, self.TEXT_COLOR)
        self.screen.blit(text_surf, (url_rect.x + 5, url_rect.y + 4))
        
        # Курсор
        if self.url_input_active and self.url_input_visible:
            cursor_x = url_rect.x + 5 + min(self.fonts['url'].size(display_text[:self.url_input_cursor])[0], url_rect.width - 10)
            pygame.draw.line(self.screen, self.TEXT_COLOR, 
                            (cursor_x, url_rect.y + 4), 
                            (cursor_x, url_rect.y + 21), 1)
    
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
        for rect, url in self.active_areas:
            if rect.collidepoint(mouse_pos):
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
            self.scroll_offset = 0
            self.max_scroll = 0
            self.loading = False
            self.status_message = "Страница загружена"
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
    
    def load_image(self, url, base_url):
        """Загружает изображение с кэшированием и обработкой ошибок"""
        # Обработка относительных URL
        if url.startswith('//'):
            # Обработка протокол-относительных URL
            parsed = urlparse(base_url)
            full_url = f"{parsed.scheme}:{url}"
        elif url.startswith('http://') or url.startswith('https://'):
            full_url = url
        else:
            full_url = urljoin(base_url, url)
        
        if full_url in self.image_cache:
            return self.image_cache[full_url], full_url
        
        try:
            response = requests.get(full_url, timeout=8)
            response.raise_for_status()
            
            # Проверка MIME-типа
            content_type = response.headers.get('Content-Type', '')
            if 'image' not in content_type and not full_url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                raise ValueError(f"Неподдерживаемый MIME-тип: {content_type}")
                
            img = pygame.image.load(BytesIO(response.content))
            self.image_cache[full_url] = img
            return img, full_url
        except Exception as e:
            print(f"Ошибка загрузки изображения {full_url}: {str(e)}")
            # Создаем заглушку для изображения
            img = pygame.Surface((100, 100))
            img.fill((240, 240, 240))
            pygame.draw.rect(img, (200, 200, 200), (5, 5, 90, 90), 1)
            pygame.draw.line(img, (255, 0, 0), (0, 0), (100, 100), 2)
            pygame.draw.line(img, (255, 0, 0), (0, 100), (100, 0), 2)
            
            # Добавляем текст с ошибкой
            try:
                error_font = pygame.font.SysFont('MS Sans Serif, Arial', 10)
                error_text = error_font.render("Ошибка изображения", True, (255, 0, 0))
                text_rect = error_text.get_rect(center=(50, 50))
                img.blit(error_text, text_rect)
            except:
                pass
                
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
            lines = self.wrap_text(text, font, 960)
            
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
            # Добавляем отступ перед параграфом
            y += 10
            y = self.render_inline(node, base_url, x, y, screen, font)
            # Добавляем отступ после параграфа
            y += 10
            return y
        
        elif node.t == 'block_quote':
            # Цитата с отступом и фоном
            y += 10
            
            # Сначала определяем высоту цитаты
            quote_height = 0
            temp_y = y
            child = node.first_child
            while child:
                if child.t == 'paragraph':
                    temp_y = self.render_inline(child, base_url, x + 20, temp_y, screen, self.fonts['normal'])
                    quote_height = max(quote_height, temp_y - y)
                child = child.nxt
            
            # Рисуем фон цитаты
            pygame.draw.rect(screen, self.QUOTE_BG, (x-10, y - self.scroll_offset - 5, 980, quote_height + 10))
            
            # Рисуем левую границу (как в оригинальном Netscape)
            pygame.draw.line(screen, self.LINK_COLOR, (x-5, y - self.scroll_offset - 5), 
                            (x-5, y - self.scroll_offset + quote_height + 5), 2)
            
            # Теперь рисуем содержимое цитаты
            child = node.first_child
            while child:
                if child.t == 'paragraph':
                    y = self.render_inline(child, base_url, x + 20, y, screen, self.fonts['normal'])
                child = child.nxt
            
            y += 10
            return y
        
        elif node.t == 'list':
            # Списки
            is_ordered = node.list_data['type'] == 'ordered'
            item_number = 1
            
            y += 10  # Отступ перед списком
            
            child = node.first_child
            while child:
                if child.t == 'item':
                    # Маркер списка
                    marker = f"{item_number}." if is_ordered else "•"
                    try:
                        marker_surf = self.fonts['normal'].render(marker, True, self.TEXT_COLOR)
                        screen.blit(marker_surf, (x, y - self.scroll_offset))
                    except:
                        pass
                    
                    # Содержимое пункта
                    y = self.render_node(child, base_url, x + 30, y, screen)
                    
                    if is_ordered:
                        item_number += 1
                child = child.nxt
            
            y += 10  # Отступ после списком
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
            y += 10
            # Рисуем фон
            pygame.draw.rect(screen, (245, 245, 245), (x-10, y - self.scroll_offset - 5, 980, 80))
            # Рисуем границу
            pygame.draw.rect(screen, (200, 200, 200), (x-10, y - self.scroll_offset - 5, 980, 80), 1)
            
            font = self.fonts['code']
            text = node.literal.strip()
            lines = text.split('\n')
            
            for line in lines:
                try:
                    rendered = font.render(line, True, (0, 100, 0))
                    screen_y = y - self.scroll_offset
                    if screen_y + rendered.get_height() > 0 and screen_y < self.screen_height:
                        screen.blit(rendered, (x, screen_y))
                    y += rendered.get_height() + 2
                except:
                    pass
            
            y += 10
            return y
        
        elif node.t == 'thematic_break':
            # Горизонтальная линия (как в Netscape)
            pygame.draw.line(screen, (128, 128, 128), (x, y - self.scroll_offset), (x + 960, y - self.scroll_offset), 1)
            pygame.draw.line(screen, (255, 255, 255), (x, y - self.scroll_offset + 1), (x + 960, y - self.scroll_offset + 1), 1)
            return y + 20
        
        elif node.t == 'image':
            # Изображение
            y += 10  # Отступ перед изображением
            img, full_url = self.load_image(node.destination, base_url)
            
            if img:
                max_width = 960
                if img.get_width() > max_width:
                    scale_factor = max_width / img.get_width()
                    new_size = (int(img.get_width() * scale_factor), 
                               int(img.get_height() * scale_factor))
                    img = pygame.transform.scale(img, new_size)
                
                # Рисуем изображение
                screen_y = y - self.scroll_offset
                if screen_y + img.get_height() > 0 and screen_y < self.screen_height:
                    screen.blit(img, (x, screen_y))
                
                y += img.get_height() + 5
            
            # Альтернативный текст
            if node.title or node.destination:
                font = self.fonts['normal']
                alt_text = node.title if node.title else node.destination
                try:
                    rendered = font.render(f"[Изображение: {alt_text}]", True, (100, 100, 100))
                    screen_y = y - self.scroll_offset
                    if screen_y + rendered.get_height() > 0 and screen_y < self.screen_height:
                        screen.blit(rendered, (x, screen_y))
                    y += rendered.get_height() + 5
                except:
                    pass
            
            return y
        
        # Обработка других типов узлов
        child = node.first_child
        while child:
            y = self.render_node(child, base_url, x, y, screen)
            child = child.nxt
        
        return y
    
    def render_inline(self, node, base_url, x, y, screen, base_font):
        """Отрисовывает инлайновые элементы с правильными переносами"""
        current_x = x
        max_width = 960
        line_height = base_font.get_height()
        
        child = node.first_child
        while child:
            if child.t == 'text':
                text = child.literal
                lines = self.wrap_text(text, base_font, max_width - (current_x - x))
                
                for line in lines:
                    try:
                        rendered = base_font.render(line, True, self.TEXT_COLOR)
                        screen_y = y - self.scroll_offset
                        
                        # Рисуем только если видимо
                        if screen_y + rendered.get_height() > 0 and screen_y < self.screen_height:
                            screen.blit(rendered, (current_x, screen_y))
                        
                        current_x += rendered.get_width()
                        
                        if current_x > x + max_width:
                            y += line_height
                            current_x = x
                    except Exception as e:
                        print(f"Ошибка отрисовки текста: {e}")
            
            elif child.t == 'softbreak':
                y += line_height
                current_x = x
            
            elif child.t == 'linebreak':
                y += line_height
                current_x = x
            
            elif child.t == 'link':
                # Ссылка
                url = child.destination
                link_text = self.collect_text(child)
                
                # Проверяем, нужно ли разбить на строки
                lines = self.wrap_text(link_text, self.fonts['link'], max_width - (current_x - x))
                
                for i, line in enumerate(lines):
                    try:
                        rendered = self.fonts['link'].render(line, True, self.LINK_COLOR)
                        screen_y = y - self.scroll_offset
                        
                        # Сохраняем область для клика (с учётом прокрутки)
                        rect = pygame.Rect(current_x, screen_y, rendered.get_width(), rendered.get_height())
                        self.active_areas.append((rect, url))
                        
                        # Рисуем только если видимо
                        if screen_y + rendered.get_height() > 0 and screen_y < self.screen_height:
                            screen.blit(rendered, (current_x, screen_y))
                        
                        # Переход на новую строку, если текст не влез
                        if i < len(lines) - 1 or current_x + rendered.get_width() > x + max_width:
                            y += rendered.get_height()
                            current_x = x
                        else:
                            current_x += rendered.get_width()
                    except Exception as e:
                        print(f"Ошибка отрисовки ссылки: {e}")
            
            elif child.t == 'strong':
                # Жирный текст
                bold_font = pygame.font.SysFont('MS Sans Serif, Arial', base_font.get_height(), bold=True)
                text = self.collect_text(child)
                lines = self.wrap_text(text, bold_font, max_width - (current_x - x))
                
                for line in lines:
                    try:
                        rendered = bold_font.render(line, True, self.TEXT_COLOR)
                        screen_y = y - self.scroll_offset
                        
                        # Рисуем только если видимо
                        if screen_y + rendered.get_height() > 0 and screen_y < self.screen_height:
                            screen.blit(rendered, (current_x, screen_y))
                        
                        if current_x + rendered.get_width() > x + max_width:
                            y += rendered.get_height()
                            current_x = x
                        else:
                            current_x += rendered.get_width()
                    except:
                        pass
            
            elif child.t == 'emph':
                # Курсив
                italic_font = pygame.font.SysFont('MS Sans Serif, Arial', base_font.get_height(), italic=True)
                text = self.collect_text(child)
                lines = self.wrap_text(text, italic_font, max_width - (current_x - x))
                
                for line in lines:
                    try:
                        rendered = italic_font.render(line, True, self.TEXT_COLOR)
                        screen_y = y - self.scroll_offset
                        
                        # Рисуем только если видимо
                        if screen_y + rendered.get_height() > 0 and screen_y < self.screen_height:
                            screen.blit(rendered, (current_x, screen_y))
                        
                        if current_x + rendered.get_width() > x + max_width:
                            y += rendered.get_height()
                            current_x = x
                        else:
                            current_x += rendered.get_width()
                    except:
                        pass
            
            child = child.nxt
        
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
        if self.max_scroll <= self.screen_height - 100:  # Учитываем верхнюю панель
            return  # Нет необходимости в прокрутке
        
        # Вычисляем размер ползунка
        visible_height = self.screen_height - 100  # Учитываем верхнюю панель
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
        """Обрабатывает события прокрутки"""
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
                    pos = pygame.mouse.get_pos()
                    screen_y = pos[1] + self.scroll_offset
                    # Проверяем клики по активным областям
                    for rect, url in self.active_areas:
                        if rect.collidepoint((pos[0], screen_y)):
                            self.forward_stack.append(self.current_url)
                            self.load_page(url)
                            break
            
            elif event.button == 2:  # Средняя кнопка (клик на колесо)
                # Сброс прокрутки в начало
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
            elif 32 <= event.key <= 126:  # ASCII символы
                char = event.unicode
                if char:
                    self.url_input = self.url_input[:self.url_input_cursor] + char + self.url_input[self.url_input_cursor:]
                    self.url_input_cursor += 1
    
    def render_page(self):
        """Отрисовывает всю страницу с прокруткой"""
        # Фон окна
        self.screen.fill(self.WINDOW_BG)
        
        # Верхняя панель (меню и инструменты)
        pygame.draw.rect(self.screen, (192, 192, 192), (0, 0, self.screen_width, 50))
        pygame.draw.line(self.screen, self.BORDER_COLOR, (0, 50), (self.screen_width, 50), 1)
        
        # Кнопки навигации
        self.draw_button(self.back_button_rect, "<", enabled=len(self.back_stack) > 0)
        self.draw_button(self.forward_button_rect, ">", enabled=len(self.forward_stack) > 0)
        
        # Строка ввода URL
        self.draw_url_input()
        
        # Кнопка "Перейти"
        self.draw_button(self.go_button_rect, "Вперед")
        
        # Основное содержимое с прокруткой
        content_rect = pygame.Rect(0, 50, self.screen_width, self.screen_height - 75)
        pygame.draw.rect(self.screen, self.TEXT_BG, content_rect)
        
        # Рисуем границу вокруг области содержимого
        pygame.draw.rect(self.screen, self.BORDER_COLOR, content_rect, 1)
        
        # Очищаем активные области
        self.active_areas = []
        
        # Основное содержимое
        y_offset = 60
        # Проверяем, что ast существует перед отрисовкой
        if hasattr(self, 'ast') and self.ast is not None:
            self.render_node(self.ast, self.current_url, 20, y_offset, self.screen)
        
        # Рисуем полосу прокрутки
        self.draw_scrollbar()
        
        # Статус-бар
        self.draw_status_bar()
        
        pygame.display.flip()
    
    def run(self):
        """Основной цикл браузера с ограничением FPS"""
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
                
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL):
                    self.handle_scroll(event)
                    
                    # Обработка кликов на кнопках
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
                        
                        # Кнопка "Перейти"
                        elif self.go_button_rect.collidepoint(event.pos):
                            self.url_input_active = False
                            self.load_page(self.url_input)
                        
                        # Строка URL
                        elif pygame.Rect(80, 10, 850, 25).collidepoint(event.pos):
                            self.url_input_active = True
                            # Устанавливаем курсор
                            url_rect = pygame.Rect(80, 10, 850, 25)
                            mouse_x = event.pos[0] - url_rect.x - 5
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
            
            # Ограничиваем FPS и перерисовываем только при необходимости
            if dt > render_interval:
                last_render_time = current_time
            
            self.clock.tick(60)  # Ограничение на 60 FPS
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    print("=" * 50)
    print("Alternet Explorer - браузер для сети Альтернет")
    print("Запуск начальной страницы:", "http://ionics.neocities.org/alternet/list.md")
    print("=" * 50)
    
    browser = AlternetExplorer()
    browser.run()